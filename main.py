# MathVis Backend - Auth Fix Multi-Identity Sync v1.0.4
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, Request
from typing import List, Optional
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select
from datetime import timedelta, datetime, timezone
import boto3
import uuid
import os
import shutil
import random
import resend
# Local imports
from database import create_db_and_tables, engine, supabase, supabase_admin, SUPABASE_BUCKET
from models import User, UserBase, UserRead, Video, Like, Comment, VerificationCode
from auth import verify_password, get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, SECRET_KEY, ALGORITHM, verify_supabase_token
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import filetype

from contextlib import asynccontextmanager
import json

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Automatically triggers SQLite table creation if files don't exist
    create_db_and_tables()
    
    # Auto-run un-applied DB migrations for free-tier deployments (no-shell)
    try:
        import migrate_categories
        migrate_categories.migrate()
    except Exception as e:
        print(f"DEBUG: Category migration log: {e}")
        
    try:
        import migrate_tags
        migrate_tags.migrate()
    except Exception as e:
        print(f"DEBUG: Tags migration log: {e}")

    try:
        import migrate_supabase_auth
        migrate_supabase_auth.migrate()
    except Exception as e:
        print(f"DEBUG: Supabase auth migration log: {e}")
    
    yield

app = FastAPI(title="MathVis API", lifespan=lifespan)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    # Debug logging for CORS issues
    origin = request.headers.get("origin")
    method = request.method
    print(f"DEBUG: Incoming request from origin: {origin}, method: {method}, path: {request.url.path}")
    
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    # Content-Security-Policy can sometimes interfere with CORS if not set carefully, 
    # but usually it's for resource loading within the page.
    # response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none';"
    return response

# Setup SlowAPI Rate Limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "https://math-vis.xin",
        "https://www.math-vis.xin",
        "https://math-frontend.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/login")

# Supabase is now initialized in database.py

def get_session():
    with Session(engine) as session:
        yield session

# -----------------
# Auth Routes
# -----------------
from pydantic import BaseModel

class UserCreate(BaseModel):
    username: str
    password: str
    email: str
    code: str

class OAuthCompleteRegistration(BaseModel):
    username: str
    password: str

class OAuthLoginRequest(BaseModel):
    supabase_token: Optional[str] = None

class OAuthVerifyRequest(BaseModel):
    username: Optional[str] = None
    supabase_token: Optional[str] = None

class OAuthBindRequest(BaseModel):
    supabase_token: str

class SendCodeRequest(BaseModel):
    email: str
    intent: str = "login"  # login, register, bind

class VerifyCodeRequest(BaseModel):
    email: str
    code: str

class OAuthBindToUsernameRequest(BaseModel):
    username: str
    password: str
    supabase_token: str

def get_user_identities(user: User) -> List[str]:
    """Helper to consistently get list of provider names."""
    # Since we removed identities_json, we just return a placeholder 
    # to signify the account is bound to Supabase.
    if user.supabase_uid:
        return ["bound"]
    return []

@app.post("/api/register", response_model=UserRead)
@limiter.limit("5/minute")
def register_user(request: Request, user_in: UserCreate, session: Session = Depends(get_session)):
    """
    Public registration endpoint. Now requires Email OTP.
    """
    email = user_in.email.strip().lower()
    code = user_in.code.strip()

    # 1. Verify OTP Code
    record = session.exec(
        select(VerificationCode).where(
            VerificationCode.email == email,
            VerificationCode.code == code
        )
    ).first()

    if not record:
        raise HTTPException(status_code=400, detail="验证码错误")
    
    if record.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        session.delete(record)
        session.commit()
        raise HTTPException(status_code=400, detail="验证码已过期")

    # 2. Check duplicate username
    existing_user = session.exec(select(User).where(User.username == user_in.username)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="用户名已被占用")
    
    # 3. Check duplicate email (Safety check)
    existing_email = session.exec(select(User).where(User.email == email)).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="该邮箱已注册，请直接登录")

    # 4. Create User
    hashed_password = get_password_hash(user_in.password)
    new_user = User(
        username=user_in.username, 
        password_hash=hashed_password,
        email=email
    )
    
    session.add(new_user)
    # Delete the used code
    session.delete(record)
    session.commit()
    session.refresh(new_user)
    
    # Attach virtual identities for response_model
    new_user.identities = get_user_identities(new_user)
    return new_user
    new_user.identities = []
    return new_user

@app.post("/api/login")
@limiter.limit("5/minute")
def login_for_access_token(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user has a bound account (Supabase UID)
    if user.supabase_uid:
        # Fetch actual bound providers from Supabase Admin
        bound_providers = []
        if supabase_admin:
            try:
                sb_user = supabase_admin.auth.admin.get_user_by_id(str(user.supabase_uid))
                if sb_user and hasattr(sb_user, "user"):
                    # Preferred: Extract from app_metadata (managed by Supabase)
                    bound_providers = sb_user.user.app_metadata.get('providers', [])
                    
                    # Fallback: Check identities directly if app_metadata is empty
                    if not bound_providers and hasattr(sb_user.user, "identities"):
                        bound_providers = [identity.provider for identity in sb_user.user.identities]
                elif sb_user and hasattr(sb_user, "identities"):
                    bound_providers = [identity.provider for identity in sb_user.identities]
            except Exception as e:
                print(f"DEBUG: Failed to fetch identities from Supabase Admin: {e}")
                bound_providers = ["oauth"] # Generic fallback
        
        # Return status=needs_verification with 200 OK to trigger frontend verification mode
        return {
            "status": "needs_verification",
            "error_code": "oauth_verification_required",
            "message": "Security Policy: MFA required. Please verify your identity via linked account.",
            "auth_providers": bound_providers,
            "email": user.email # Masked or actual email
        }
    
    # Standard password-only login (unbound account)
    session.add(user)
    session.commit()
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "id": user.id}, 
        expires_delta=access_token_expires
    )
    return {
        "status": "ok",
        "suggest_binding": True,
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "is_admin": user.is_admin,
            "email": user.email,
            "supabase_uid": user.supabase_uid,
            "bound_providers": [], # Password login for unbound users
            "identities": get_user_identities(user),
        }
    }


@app.post("/api/auth/verify-login")
def verify_login_with_oauth(
    data: OAuthVerifyRequest,
    request: Request,
    session: Session = Depends(get_session)
):
    """
    Second step of login for bound accounts.
    Verifies the Supabase token and matches it with the username.
    """
    # Extract token from Body (MUST be explicit)
    sb_token = data.supabase_token
    if not sb_token:
        raise HTTPException(status_code=401, detail="supabase_token in request body required")

    # Step 1: Find user
    user = None
    if data.username:
        user = session.exec(select(User).where(User.username == data.username)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
    
    # Step 2: Verify Supabase token
    supabase_info = verify_supabase_token(sb_token)
    if not supabase_info:
        raise HTTPException(status_code=401, detail="Invalid Supabase token")
    
    # Step 3: Find user by token if username was missing
    if not user:
        user = session.exec(select(User).where(User.supabase_uid == str(supabase_info["sub"]))).first()
        if not user:
            raise HTTPException(status_code=404, detail="No local account linked to this OAuth identity")

    # Step 4: Validate match
    if not user.supabase_uid:
        print(f"DEBUG: verify-login: User '{user.username}' has no supabase_uid bound. Cannot verify.")
        raise HTTPException(status_code=400, detail="User does not have a bound account")
    
    # CRITICAL: Force str() on both sides to prevent UUID object vs string mismatch
    db_uid = str(user.supabase_uid)
    token_uid = str(supabase_info["sub"])
    print(f"DEBUG: verify-login: Comparing DB UID='{db_uid}' (type={type(user.supabase_uid).__name__}) vs Token SUB='{token_uid}' (type={type(supabase_info['sub']).__name__})")
    
    if token_uid != db_uid:
        print(f"DEBUG: Identity match FAILED for user '{user.username}'. DB UID: {db_uid}, Token SUB: {token_uid}")
        raise HTTPException(status_code=401, detail="Identity verification failed. Please use your correctly linked account.")
        
    # Issue absolute JWT
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "id": user.id}, 
        expires_delta=access_token_expires
    )

    # Hydrate bound_providers so frontend can skip the extra /me call
    bound_providers = fetch_bound_providers(user.supabase_uid)
    print(f"DEBUG: verify-login: user='{user.username}', bound_providers={bound_providers}")

    return {
        "status": "ok",
        "access_token": access_token, 
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "is_admin": user.is_admin,
            "email": user.email,
            "supabase_uid": user.supabase_uid,
            "bound_providers": bound_providers,
            "identities": get_user_identities(user),
        },
        # Flat alias
        "bound_providers": bound_providers,
    }

async def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)):
    from jose import jwt, JWTError
    auth_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Strictly handle custom System JWT only.
    # This ensures that we never pass a custom token to the Supabase SDK.
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username:
            user = session.exec(select(User).where(User.username == username)).first()
            if user:
                return user
    except JWTError:
        pass
            
    raise auth_exception

# -----------------
# User Info
# -----------------

def fetch_bound_providers(supabase_uid: str) -> list:
    """
    Query Supabase Admin API to get list of bound OAuth providers for a user.
    Uses a 4-tier fallback strategy to handle Supabase API response variations.
    """
    if not supabase_admin or not supabase_uid:
        print(f"DEBUG: fetch_bound_providers: skipped (admin={'yes' if supabase_admin else 'NO'}, uid={supabase_uid!r})")
        return []
    try:
        sb_resp = supabase_admin.auth.admin.get_user_by_id(str(supabase_uid))
        
        # Normalise: the SDK may return sb_resp.user or the object itself may have the fields
        sb_user = getattr(sb_resp, 'user', sb_resp)
        
        if not sb_user:
            print(f"DEBUG: fetch_bound_providers: no user object returned for uid={supabase_uid}")
            return []
        
        app_meta = getattr(sb_user, 'app_metadata', {}) or {}
        identities = getattr(sb_user, 'identities', []) or []
        
        print(f"DEBUG: fetch_bound_providers uid={supabase_uid}: app_metadata={app_meta}, identities_count={len(identities)}")

        # TIER 1: app_metadata.providers (plural list) — standard Supabase field
        providers = app_meta.get('providers', [])
        if providers:
            # Filter out 'email' as it is not a real OAuth provider
            result = [p for p in providers if p and p != 'email']
            if result:
                print(f"DEBUG: fetch_bound_providers: TIER1 result={result}")
                return result

        # TIER 2: app_metadata.provider (singular) — also set by Supabase
        single = app_meta.get('provider', '')
        if single and single != 'email':
            print(f"DEBUG: fetch_bound_providers: TIER2 result=[{single}]")
            return [single]

        # TIER 3: identities list — iterate and extract provider names
        if identities:
            result = list(set(
                str(getattr(identity, 'provider', '')) for identity in identities
            ))
            result = [p for p in result if p and p != 'email']
            if result:
                print(f"DEBUG: fetch_bound_providers: TIER3 result={result}")
                return result

        # TIER 4: No known provider found
        print(f"DEBUG: fetch_bound_providers: TIER4 - No known providers found")
        return []

    except Exception as e:
        print(f"DEBUG: fetch_bound_providers error for uid={supabase_uid}: {e}")
    return []

@app.get("/api/users/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """
    Return the current user's profile with real-time bound_providers
    hydrated from Supabase Admin API.
    """
    bound_providers = fetch_bound_providers(current_user.supabase_uid)
    print(f"DEBUG: /api/users/me: user='{current_user.username}', supabase_uid={current_user.supabase_uid!r}, bound_providers={bound_providers}")

    return {
        "id": current_user.id,
        "username": current_user.username,
        "is_admin": current_user.is_admin,
        "email": current_user.email,
        "supabase_uid": current_user.supabase_uid, 
        "bound_providers": bound_providers,
    }

# -----------------
# OAuth Routes
# -----------------

@app.post("/api/auth/complete-registration")
@limiter.limit("5/minute")
def complete_oauth_registration(
    request: Request,
    data: OAuthCompleteRegistration,
    session: Session = Depends(get_session)
):
    """
    After OAuth verification, user sets username + password to complete registration.
    Creates a local user linked to their Supabase auth account.
    """
    # We should always check Header for this second step
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        sb_token = auth_header.split(" ")[1]
    else:
        raise HTTPException(status_code=401, detail="Supabase OAuth token required in Authorization header")

    # 1. Verify the Supabase token
    supabase_info = verify_supabase_token(sb_token)
    if not supabase_info:
        raise HTTPException(status_code=401, detail="Invalid or expired OAuth token")
    
    # 2. Check if this Supabase UID is already registered
    existing = session.exec(select(User).where(User.supabase_uid == str(supabase_info["sub"]))).first()
    if existing:
        raise HTTPException(status_code=400, detail="This OAuth account is already linked to a user")
    
    # 3. Check if username is taken
    existing_user = session.exec(select(User).where(User.username == data.username)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    # 4. Create the local user
    hashed_password = get_password_hash(data.password)
    new_user = User(
        username=data.username,
        password_hash=hashed_password,
        supabase_uid=str(supabase_info["sub"])
    )
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    
    # 5. Issue a local JWT token
    access_token = create_access_token(
        data={"sub": new_user.username, "id": new_user.id},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return {
        "status": "ok",
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": new_user.id,
            "username": new_user.username,
            "is_admin": new_user.is_admin,
            "email": new_user.email,
            "supabase_uid": new_user.supabase_uid,
            "bound_providers": fetch_bound_providers(new_user.supabase_uid),
            "identities": get_user_identities(new_user),
        }
    }

@app.post("/api/auth/oauth-login")
@limiter.limit("10/minute")
def oauth_login(
    request: Request,
    data: OAuthLoginRequest,
    session: Session = Depends(get_session)
):
    """
    Login via Supabase OAuth token. Finds the linked local user.
    """
    # Try Body first, then Header
    sb_token = data.supabase_token
    if not sb_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            sb_token = auth_header.split(" ")[1]

    if not sb_token:
        raise HTTPException(status_code=401, detail="Bearer token or supabase_token required")

    supabase_info = verify_supabase_token(sb_token)
    if not supabase_info:
        raise HTTPException(status_code=401, detail="Invalid or expired OAuth token")
    
    # Find linked local user
    user = session.exec(select(User).where(User.supabase_uid == str(supabase_info["sub"]))).first()

    if not user:
        # No linked account found - frontend should show registration form
        return {
            "status": "needs_registration",
            "provider": supabase_info.get("provider")
        }
    
    # Issue local JWT
    access_token = create_access_token(
        data={"sub": user.username, "id": user.id},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    # Hydrate bound_providers so frontend can skip the extra /me call
    bound_providers = fetch_bound_providers(user.supabase_uid)
    print(f"DEBUG: oauth-login: user='{user.username}', bound_providers={bound_providers}")

    return {
        "status": "ok",
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "is_admin": user.is_admin,
            "email": user.email,
            "supabase_uid": user.supabase_uid,
            "bound_providers": bound_providers,
        },
        # Keep flat aliases for backward-compat with any callers that read top-level keys
        "user_id": user.id,
        "username": user.username,
        "is_admin": user.is_admin,
        "bound_providers": bound_providers,
        "identities": get_user_identities(user)
    }

# -----------------
# Email OTP Routes
# -----------------

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
resend.api_key = RESEND_API_KEY

def send_email_otp(to_email: str, code: str) -> None:
    try:
        params = {
            "from": "MathVis <noreply@math-vis.xin>",
            "to": [to_email],
            "subject": "【MathVis】你的登录验证码",
            "html": f"<h2>欢迎来到 MathVis</h2><p>你的验证码是：<strong>{code}</strong></p><p>该验证码 5 分钟内有效。</p>"
        }
        email_response = resend.Emails.send(params)
        print(f"Resend email sent successfully: {email_response}")
    except Exception as e:
        print(f"ERROR: Resend API Error: {str(e)}")
        raise RuntimeError("邮件推送服务异常，请稍后重试")


@app.post("/api/auth/send-code")
@limiter.limit("5/minute")
def send_verification_code(
    request: Request,
    data: SendCodeRequest,
    session: Session = Depends(get_session)
):
    """
    Generate a 6-digit OTP, store it, and email it to the user.
    """
    if not RESEND_API_KEY:
        raise HTTPException(status_code=500, detail="Resend API Key not configured on server")

    email = data.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email address")

    # Intent check ONLY for registration
    if data.intent == "register":
        # Check if email is already registered in our local 'users' table
        existing_email = session.exec(select(User).where(User.email == email)).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="该邮箱已注册，请使用账号密码登录")

    # Delete any stale codes for this email before creating a new one
    old_codes = session.exec(select(VerificationCode).where(VerificationCode.email == email)).all()
    for old in old_codes:
        session.delete(old)
    session.commit()

    code = str(random.randint(100000, 999999))
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

    record = VerificationCode(email=email, code=code, expires_at=expires_at)
    session.add(record)
    session.commit()

    try:
        send_email_otp(email, code)
    except Exception as e:
        print(f"ERROR: send_verification_code: SMTP failed for {email}: {e}")
        # 根据商用标准，无论是 RuntimeError 还是不可预知的其他 Exception，统一返回友好 500
        raise HTTPException(status_code=500, detail="发件服务器网络异常，请稍后重试或检查配置")


    print(f"DEBUG: send-code: OTP sent to {email}, intent={data.intent}, expires_at={expires_at}")
    return {"status": "ok", "message": "Verification code sent"}


@app.post("/api/auth/verify-code")
@limiter.limit("10/minute")
def verify_email_code(
    request: Request,
    data: VerifyCodeRequest,
    session: Session = Depends(get_session)
):
    """
    Validate a 6-digit email OTP and return a system JWT.
    Auto-registers the user if no account exists for this email.
    """
    email = data.email.strip().lower()
    code = data.code.strip()

    # 1. Look up the code record
    record = session.exec(
        select(VerificationCode)
        .where(VerificationCode.email == email)
        .where(VerificationCode.code == code)
    ).first()

    if not record:
        raise HTTPException(status_code=401, detail="验证码错误，请重新获取")

    # 2. Check expiry (compare offset-aware datetimes)
    now = datetime.now(timezone.utc)
    expires = record.expires_at
    if expires.tzinfo is None:
        # Make naive datetimes timezone-aware (UTC)
        from datetime import timezone as _tz
        expires = expires.replace(tzinfo=_tz.utc)
    if now > expires:
        session.delete(record)
        session.commit()
        raise HTTPException(status_code=401, detail="验证码已过期，请重新获取")

    # 3. Consume the code immediately (one-time use)
    session.delete(record)
    session.commit()

    # 4. Find user strictly by email field (do NOT query by username)
    user = session.exec(select(User).where(User.email == email)).first()
    
    # 绝对禁止静默由于没找到用户而用邮箱注册了一个没有被认证的新用户 ("shadow account")
    if not user:
        print(f"DEBUG: verify-code: rejected OTP login for unbound email '{email}'")
        raise HTTPException(status_code=401, detail="该邮箱尚未绑定任何账号")
        
    print(f"DEBUG: verify-code: existing user '{user.username}' logged in via OTP")

    # 5. Issue system JWT
    access_token = create_access_token(
        data={"sub": user.username, "id": user.id},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    # 6. Hydrate bound_providers (may be empty for OTP-only users)
    bound_providers = fetch_bound_providers(user.supabase_uid) if user.supabase_uid else []

    return {
        "status": "ok",
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "is_admin": user.is_admin,
            "email": email,
            "bound_providers": bound_providers,
        },
        "bound_providers": bound_providers,
    }


@app.post("/api/auth/bind")
def bind_oauth_account(
    request: Request,
    data: OAuthBindRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Bind an OAuth account to an existing user (logged in with username/password).
    """
    # CRITICAL FIX: The current user is identified by the System JWT in the header (Depends(get_current_user))
    # The account TO BE BOUND is identified by the supabase_token in the request body.
    # We must NEVER use the Authorization header for Supabase verification during the bind process.
    sb_token = data.supabase_token
    if not sb_token:
        raise HTTPException(status_code=400, detail="supabase_token in body required for binding")

    # Verify that the SUBAPASE token is valid
    supabase_info = verify_supabase_token(sb_token)
    if not supabase_info:
        raise HTTPException(status_code=401, detail="OAuth Binding Failed: the provided Supabase token is invalid or expired.")
    
    # Check if this Supabase UID is already linked to another user
    token_uid = str(supabase_info["sub"])
    existing = session.exec(select(User).where(User.supabase_uid == token_uid)).first()
    if existing and existing.id != current_user.id:
        raise HTTPException(status_code=400, detail="This OAuth account is already linked to another user")
    
    # Check if any other user has this provider in their identities_json (optional but safer)
    # For now, supabase_uid check is sufficient as it's the primary key from Supabase.
    
    # Bind with dict mapping
    new_provider = supabase_info.get("provider", "unknown")
    try:
        p_data = json.loads(current_user.identities_json or "{}")
        if isinstance(p_data, list):
            p_data = {p: current_user.supabase_uid for p in p_data}
    except:
        p_data = {}
    
    # CRITICAL: Always store as string to prevent type mismatch on later comparisons
    current_user.supabase_uid = token_uid
    print(f"DEBUG: bind: Bound user '{current_user.username}' (id={current_user.id}) to supabase_uid='{token_uid}', provider='{new_provider}'")
    
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    
    return {
        "status": "ok",
        "message": "OAuth account bound successfully",
        "user_id": current_user.id,
        "username": current_user.username,
        "is_admin": current_user.is_admin,
        "auth_provider": supabase_info.get("provider"),
        "email": supabase_info.get("email"),
        "identities": get_user_identities(current_user)
    }

@app.post("/api/auth/bind-email")
@limiter.limit("5/minute")
def bind_email_address(
    request: Request,
    data: VerifyCodeRequest, # email, code
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Bind an email address to the current user via OTP verification.
    """
    email = data.email.strip().lower()
    code = data.code.strip()

    # 1. Verify OTP
    record = session.exec(
        select(VerificationCode)
        .where(VerificationCode.email == email)
        .where(VerificationCode.code == code)
    ).first()

    if not record:
        raise HTTPException(status_code=400, detail="验证码错误")

    if record.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        session.delete(record)
        session.commit()
        raise HTTPException(status_code=400, detail="验证码已过期")

    # 2. Check email uniqueness
    existing = session.exec(select(User).where(User.email == email)).first()
    if existing and existing.id != current_user.id:
        raise HTTPException(status_code=400, detail="该邮箱已被其他账号绑定")

    # 3. Bind email
    current_user.email = email
    session.add(current_user)
    session.delete(record)
    session.commit()
    session.refresh(current_user)

    return {
        "status": "ok",
        "message": "Email bound successfully",
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "bound_providers": fetch_bound_providers(current_user.supabase_uid)
        }
    }

@app.post("/api/auth/unbind")
def unbind_oauth_account(
    data: dict,  # {"provider": "github"}
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Remove an OAuth binding from the current user.
    """
    if current_user.supabase_uid:
        current_user.supabase_uid = None
        session.add(current_user)
        session.commit()
        session.refresh(current_user)
    
    return {
        "status": "ok",
        "message": f"Successfully unbound OAuth",
        "user_id": current_user.id,
        "username": current_user.username,
        "is_admin": current_user.is_admin,
        "identities": get_user_identities(current_user)
    }

@app.post("/api/auth/force-unbind")
def force_unbind_account(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    CRITICAL: Completely remove ALL OAuth bindings and DELETE the Supabase user.
    This is used when a user wants to "reset" their account to password-only 
    or unbind the very last identity.
    """
    if not current_user.supabase_uid:
        raise HTTPException(status_code=400, detail="No bound Supabase account found")

    # 1. Delete from Supabase Auth using Admin Client
    if supabase_admin:
        try:
            # delete_user is an admin operation
            supabase_admin.auth.admin.delete_user(current_user.supabase_uid)
            print(f"DEBUG: Successfully deleted Supabase user {current_user.supabase_uid}")
        except Exception as e:
            print(f"ERROR: Failed to delete Supabase user: {e}")
            # If the user is already gone from Supabase, we continue with local cleanup
    
    # 2. Local Cleanup
    user = current_user # Alias for clarity if needed
    user.supabase_uid = None
    
    session.add(user)
    session.commit()
    session.refresh(current_user)
    
    return {
        "status": "ok",
        "message": "Account successfully unbound and Supabase identity deleted. Session termination required.",
        "user_id": current_user.id
    }

@app.post("/api/auth/bind-to-username")
@limiter.limit("5/minute")
def bind_oauth_to_username(
    request: Request,
    data: OAuthBindToUsernameRequest,
    session: Session = Depends(get_session)
):
    """
    Bind an OAuth account to an existing username/password account (for first-time binding).
    Verifies password to ensure ownership before binding.
    """
    # 1. Verify user credentials
    user = session.exec(select(User).where(User.username == data.username)).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    # 2. Extract Supabase token
    # Use Body for consistency, but Header is acceptable here too
    sb_token = data.supabase_token
    if not sb_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            sb_token = auth_header.split(" ")[1]
            
    if not sb_token:
        raise HTTPException(status_code=401, detail="Supabase OAuth token required")

    # 3. Verify the Supabase token
    supabase_info = verify_supabase_token(sb_token)
    if not supabase_info:
        raise HTTPException(status_code=401, detail="Invalid or expired OAuth token")
    
    # 4. Check if this Supabase UID is already linked to another user
    existing = session.exec(select(User).where(User.supabase_uid == str(supabase_info["sub"]))).first()
    if existing and existing.id != user.id:
        raise HTTPException(status_code=400, detail="This OAuth account is already linked to another user")
    
    # 5. Bind
    user.supabase_uid = str(supabase_info["sub"])
    
    session.add(user)
    session.commit()
    session.refresh(user)
    
    access_token = create_access_token(
        data={"sub": user.username, "id": user.id},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return {
        "status": "ok",
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "username": user.username,
        "is_admin": user.is_admin,
        "identities": get_user_identities(user)
    }

# -----------------
# Upload Routes
# -----------------

@app.post("/api/videos")
async def upload_video(
    title: str = Form(...),
    category_l1: Optional[str] = Form(None),
    category_l2: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    file: UploadFile = File(...),
    source_file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Upload a local MP4 file to the server and create a database record.
    """
    print(f"DEBUG: Received upload request. Title: {title}")
    print(f"DEBUG: Video file: {file.filename if file else 'None'}")
    print(f"DEBUG: Source file: {source_file.filename if source_file else 'None'}")
    if not file.filename.endswith('.mp4'):
        raise HTTPException(status_code=400, detail="Only .mp4 files are supported.")
        
    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    
    # Force Cloud Storage requirement
    if not supabase:
        raise HTTPException(
            status_code=500, 
            detail="Supabase Storage is not configured. Cloud upload is required."
        )
        
    try:
        # Read the file data
        file_data = await file.read()
            
        # 1. Size constraint (30MB limit)
        if len(file_data) > 30 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="File too large. Maximum size allowed is 30MB.")
        
        # 2. Magic byte verification
        kind = filetype.guess(file_data[:2048])
        if kind is None or not kind.mime.startswith('video/'):
            raise HTTPException(status_code=400, detail="Invalid file type. Only genuine videos are permitted.")

        # Use supabase logic
        supabase.storage.from_(SUPABASE_BUCKET).upload(
            path=unique_filename,
            file=file_data,
            file_options={"content-type": file.content_type}
        )
            
        # Get public URL
        video_url = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(unique_filename)
        
        # Verify the URL is valid, fallback check (optional)
        if not video_url:
             raise Exception("Supabase returned an empty public URL.")
             
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload video to Supabase: {str(e)}")
    
    # Optional Source Code Upload
    manim_source_url = None
    if source_file:
        if not source_file.filename.endswith('.py'):
            raise HTTPException(status_code=400, detail="Only .py files are supported for Manim source.")
            
        source_unique_filename = f"{uuid.uuid4()}_{source_file.filename}"
        try:
            source_data = await source_file.read()
            # Try uploading with the inferred content type if specific one fails
            supabase.storage.from_(SUPABASE_BUCKET).upload(
                path=source_unique_filename,
                file=source_data,
                file_options={"content-type": "text/plain; charset=utf-8"} # Add utf-8 charset for Python code
            )
            manim_source_url = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(source_unique_filename)
        except Exception as e:
            # Re-raise as 500 so we can see the error in frontend
            raise HTTPException(status_code=500, detail=f"Failed to upload Manim source to Supabase: {str(e)}")
    
    new_video = Video(
        title=title,
        category_l1=category_l1,
        category_l2=category_l2,
        tags=tags,
        video_url=video_url,
        manim_source_url=manim_source_url,
        uploader_id=current_user.id
    )
    
    session.add(new_video)
    session.commit()
    session.refresh(new_video)
    
    return {"message": "Video uploaded successfully", "video": new_video}

@app.get("/api/videos")
def get_videos(request: Request, session: Session = Depends(get_session)):
    """
    Get all uploaded videos. If authenticated, also returns whether the current user liked each video.
    """
    # Optional authentication
    current_user_id = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            from jose import jwt
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            current_user_id = payload.get("id")
        except:
            pass # Invalid token, treat as guest

    videos = session.exec(select(Video).order_by(Video.upload_time.desc())).all()
    results = []
    
    for v in videos:
        # Check if current user has liked this video
        is_liked = False
        if current_user_id:
            is_liked = any(l.user_id == current_user_id for l in v.likes)

        results.append({
            "id": v.id,
            "title": v.title,
            "category_l1": v.category_l1,
            "category_l2": v.category_l2,
            "tags": v.tags.split(',') if v.tags else [],
            "video_url": v.video_url,
            "manim_source_url": v.manim_source_url,
            "view_count": v.view_count,
            "upload_time": v.upload_time,
            "uploader_username": v.uploader.username,
            "uploader_id": v.uploader_id,
            "like_count": len(v.likes),
            "_liked": is_liked
        })
        
    return results

@app.post("/api/videos/{video_id}/like")
def toggle_like_video(
    video_id: int, 
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Toggle the like status of a video for the current user.
    """
    video = session.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
        
    existing_like = session.exec(
        select(Like).where(Like.user_id == current_user.id, Like.video_id == video_id)
    ).first()
    
    if existing_like:
        # Unlike
        session.delete(existing_like)
        session.commit()
        new_count = len(session.exec(select(Like).where(Like.video_id == video_id)).all())
        return {"action": "unliked", "like_count": new_count}
    else:
        # Like
        new_like = Like(user_id=current_user.id, video_id=video_id)
        session.add(new_like)
        session.commit()
        new_count = len(session.exec(select(Like).where(Like.video_id == video_id)).all())
        return {"action": "liked", "like_count": new_count}

@app.delete("/api/videos/{video_id}")
def delete_video(
    video_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Delete a video only if the caller is the uploader.
    """
    video = session.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail=f"ID {video_id} NOT found in DB")
        
    print(f"DEBUG: Deleting {video_id} - ReqID: {current_user.id}, OwnerID: {video.uploader_id}, Admin: {current_user.is_admin}")
    if video.uploader_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail=f"Not authorized. u={current_user.id} vs o={video.uploader_id} a={current_user.is_admin}")
        
    # Attempt to delete from Supabase if configured
    if supabase:
        from urllib.parse import urlparse
        files_to_remove = []
        
        # Add video file to removal list
        if video.video_url:
            video_filename = urlparse(video.video_url).path.split('/')[-1]
            files_to_remove.append(video_filename)
            
        # Add manim source file to removal list
        if video.manim_source_url:
            source_filename = urlparse(video.manim_source_url).path.split('/')[-1]
            files_to_remove.append(source_filename)
            
        if files_to_remove:
            try:
                supabase.storage.from_(SUPABASE_BUCKET).remove(files_to_remove)
                print(f"DEBUG: Removed from Supabase Storage: {files_to_remove}")
            except Exception as e:
                # We continue even if storage delete fails, but log it
                print(f"Failed to delete from Supabase: {e}")
            
    # Delete associated likes and comments first (handles pre-existing tables without CASCADE)
    existing_likes = session.exec(select(Like).where(Like.video_id == video_id)).all()
    for like in existing_likes:
        session.delete(like)
    
    existing_comments = session.exec(select(Comment).where(Comment.video_id == video_id)).all()
    for comment in existing_comments:
        session.delete(comment)
    
    # Delete the video record itself
    session.delete(video)
    session.commit()
    
    return {"message": "Video deleted successfully"}

@app.get("/")
def read_root():
    return {"message": "Welcome to the MathVis API. Visit /docs for Swagger interactive documentation."}

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
