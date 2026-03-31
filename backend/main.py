from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, Request
from typing import List, Optional
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select
from datetime import timedelta
import boto3
import uuid
import os
import shutil

# Local imports
from database import create_db_and_tables, engine
from models import User, UserBase, Video, Like, Comment
from auth import verify_password, get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, SECRET_KEY, ALGORITHM, verify_supabase_token
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import filetype

from contextlib import asynccontextmanager

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

from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Setup Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET_NAME", "videos")

supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

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

class OAuthCompleteRegistration(BaseModel):
    supabase_token: str
    username: str
    password: str

class OAuthLoginRequest(BaseModel):
    supabase_token: str

class OAuthBindRequest(BaseModel):
    supabase_token: str

@app.post("/api/register", response_model=UserBase)
@limiter.limit("5/minute")
def register_user(request: Request, user_in: UserCreate, session: Session = Depends(get_session)):
    existing_user = session.exec(select(User).where(User.username == user_in.username)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = get_password_hash(user_in.password)
    new_user = User(username=user_in.username, password_hash=hashed_password)
    
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
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
        
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "id": user.id}, 
        expires_delta=access_token_expires
    )
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user_id": user.id,
        "username": user.username,
        "is_admin": user.is_admin
    }

async def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)):
    from jose import jwt, JWTError
    auth_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Try old custom JWT first
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username:
            user = session.exec(select(User).where(User.username == username)).first()
            if user:
                return user
    except JWTError:
        pass
    
    # Try Supabase JWT
    supabase_info = verify_supabase_token(token)
    if supabase_info:
        user = session.exec(select(User).where(User.supabase_uid == supabase_info["sub"])).first()
        if user:
            return user
    
    raise auth_exception

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
    # 1. Verify the Supabase token
    supabase_info = verify_supabase_token(data.supabase_token)
    if not supabase_info:
        raise HTTPException(status_code=401, detail="Invalid or expired OAuth token")
    
    # 2. Check if this Supabase UID is already registered
    existing = session.exec(select(User).where(User.supabase_uid == supabase_info["sub"])).first()
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
        supabase_uid=supabase_info["sub"],
        email=supabase_info.get("email"),
        auth_provider=supabase_info.get("provider", "unknown")
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
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": new_user.id,
        "username": new_user.username,
        "is_admin": new_user.is_admin,
        "auth_provider": new_user.auth_provider,
        "email": new_user.email
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
    supabase_info = verify_supabase_token(data.supabase_token)
    if not supabase_info:
        raise HTTPException(status_code=401, detail="Invalid or expired OAuth token")
    
    # Find linked local user
    user = session.exec(select(User).where(User.supabase_uid == supabase_info["sub"])).first()
    if not user:
        # No linked account found - frontend should show registration form
        return {
            "status": "needs_registration",
            "email": supabase_info.get("email"),
            "provider": supabase_info.get("provider")
        }
    
    # Issue local JWT
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
        "auth_provider": user.auth_provider,
        "email": user.email
    }

@app.post("/api/auth/bind")
def bind_oauth_account(
    data: OAuthBindRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Bind an OAuth account to an existing user (logged in with username/password).
    """
    supabase_info = verify_supabase_token(data.supabase_token)
    if not supabase_info:
        raise HTTPException(status_code=401, detail="Invalid or expired OAuth token")
    
    # Check if this Supabase UID is already linked to another user
    existing = session.exec(select(User).where(User.supabase_uid == supabase_info["sub"])).first()
    if existing and existing.id != current_user.id:
        raise HTTPException(status_code=400, detail="This OAuth account is already linked to another user")
    
    # Bind
    current_user.supabase_uid = supabase_info["sub"]
    current_user.email = supabase_info.get("email") or current_user.email
    current_user.auth_provider = supabase_info.get("provider", current_user.auth_provider)
    
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    
    return {
        "message": "OAuth account bound successfully",
        "auth_provider": current_user.auth_provider,
        "email": current_user.email
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
