from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
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
from models import User, UserBase, Video, Like
from auth import verify_password, get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, SECRET_KEY, ALGORITHM
from fastapi.middleware.cors import CORSMiddleware

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Automatically triggers SQLite table creation if files don't exist
    create_db_and_tables()
    yield

app = FastAPI(title="MathVis API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

@app.post("/api/register", response_model=UserBase)
def register_user(user_in: UserCreate, session: Session = Depends(get_session)):
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
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
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
        "username": user.username
    }

async def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)):
    from jose import jwt, JWTError
    auth_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise auth_exception
    except JWTError:
        raise auth_exception
        
    user = session.exec(select(User).where(User.username == username)).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# -----------------
# Upload Routes
# -----------------

@app.post("/api/videos")
async def upload_video(
    title: str = Form(...),
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
                file_options={"content-type": "text/plain"} # Use text/plain for better compatibility
            )
            manim_source_url = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(source_unique_filename)
        except Exception as e:
            # Re-raise as 500 so we can see the error in frontend
            raise HTTPException(status_code=500, detail=f"Failed to upload Manim source to Supabase: {str(e)}")
    
    new_video = Video(
        title=title,
        video_url=video_url,
        manim_source_url=manim_source_url,
        uploader_id=current_user.id
    )
    
    session.add(new_video)
    session.commit()
    session.refresh(new_video)
    
    return {"message": "Video uploaded successfully", "video": new_video}

@app.get("/api/videos")
def get_videos(session: Session = Depends(get_session)):
    """
    Get all uploaded videos.
    """
    videos = session.exec(select(Video).order_by(Video.upload_time.desc())).all()
    results = []
    
    # For MVP we iterate through video records and eagerly return like count and username
    for v in videos:
        results.append({
            "id": v.id,
            "title": v.title,
            "video_url": v.video_url,
            "manim_source_url": v.manim_source_url,
            "view_count": v.view_count,
            "upload_time": v.upload_time,
            "uploader_username": v.uploader.username,
            "uploader_id": v.uploader_id,
            "like_count": len(v.likes)
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
        raise HTTPException(status_code=404, detail="Video not found")
        
    if video.uploader_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this video")
        
    # Attempt to delete from Supabase if configured
    if supabase:
        files_to_remove = []
        
        # Add video file to removal list
        if video.video_url:
            video_filename = video.video_url.split('/')[-1]
            files_to_remove.append(video_filename)
            
        # Add manim source file to removal list
        if video.manim_source_url:
            source_filename = video.manim_source_url.split('/')[-1]
            files_to_remove.append(source_filename)
            
        if files_to_remove:
            try:
                supabase.storage.from_(SUPABASE_BUCKET).remove(files_to_remove)
            except Exception as e:
                # We continue even if storage delete fails, but log it
                print(f"Failed to delete from Supabase: {e}")
            
    # Delete from DB
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
