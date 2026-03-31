import os
from dotenv import load_dotenv
from sqlmodel import create_engine, Session, select
from models import Video

# Load the .env from the backend directory
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("DATABASE_URL not found in environment!")
    exit(1)

engine = create_engine(DATABASE_URL)

with Session(engine) as session:
    # Find the video with title "欧拉变换"
    statement = select(Video).where(Video.title == "欧拉变换")
    video = session.exec(statement).first()
    
    if video:
        old_url = video.video_url
        new_url = "https://hoqnejmcrqznkcxzcagm.supabase.co/storage/v1/object/public/Videos/18c8d9ba-4067-4491-8536-80c12121cd66_EulerEpicycles.mp4"
        
        if old_url != new_url:
            video.video_url = new_url
            session.add(video)
            session.commit()
            print(f"SUCCESS: Updated '{video.title}' URL from {old_url} to {new_url}")
        else:
            print(f"INFO: URL for '{video.title}' is already correct: {new_url}")
    else:
        print("ERROR: Video '欧拉变换' not found in database!")
