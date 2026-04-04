import os
from sqlmodel import create_engine, Session, select
from database import DATABASE_URL
from models import Video

print(f"DEBUG: Connecting to: {DATABASE_URL}")
engine = create_engine(DATABASE_URL)

with Session(engine) as session:
    videos = session.exec(select(Video)).all()
    print(f"DEBUG: Found {len(videos)} videos in database:")
    for v in videos:
        print(f"  - [{v.id}] {v.title}: {v.video_url}")
