from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt, JWTError

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Security Settings
SECRET_KEY = os.getenv("SECRET_KEY", "SUPER_SECRET_MATHVIS_KEY_CHANGE_IN_PRODUCTION")
if SECRET_KEY == "SUPER_SECRET_MATHVIS_KEY_CHANGE_IN_PRODUCTION":
    print("⚠️ WARNING: Using default insecure SECRET_KEY. Set SECRET_KEY in .env immediately for production!")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 7 days validity

# Supabase Auth Settings
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")

import bcrypt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed one."""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

def get_password_hash(password: str) -> str:
    """Generate a bcrypt hash of the password."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_supabase_token(token: str) -> Optional[dict]:
    """
    Verify a Supabase-issued JWT and extract user info.
    Returns dict with 'sub' (supabase uid), 'email', 'provider' or None if invalid.
    """
    if not SUPABASE_JWT_SECRET:
        print("❌ ERROR: SUPABASE_JWT_SECRET not configured in environment! Verification will fail.")
        return None
    
    # Strip 'Bearer ' if present to improve robustness
    if token.startswith("Bearer "):
        token = token[7:]
    
    try:
        # Standard Supabase JWT settings: HS256 and 'authenticated' audience
        payload = jwt.decode(
            token, 
            SUPABASE_JWT_SECRET, 
            algorithms=["HS256"],
            audience="authenticated"
        )
        
        supabase_uid = payload.get("sub")
        email = payload.get("email")
        
        # Extract provider from app_metadata
        app_metadata = payload.get("app_metadata", {})
        provider = app_metadata.get("provider", "email")
        
        if not supabase_uid:
            print("⚠️ Supabase JWT missing 'sub' claim")
            return None
            
        return {
            "sub": supabase_uid,
            "email": email,
            "provider": provider
        }
    except jwt.ExpiredSignatureError:
        print("❌ Supabase JWT verification error: Token expired")
        return None
    except jwt.JWTClaimsError as e:
        print(f"❌ Supabase JWT verification error: Claims/Audience error - {e}")
        return None
    except JWTError as e:
        print(f"❌ Supabase JWT verification error: {type(e).__name__}: {e}")
        return None
