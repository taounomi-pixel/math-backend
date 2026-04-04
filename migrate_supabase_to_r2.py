import os
import httpx
import boto3
import asyncio
from sqlmodel import create_engine, Session, select
from database import s3_client, R2_BUCKET_NAME, R2_PUBLIC_DOMAIN, DATABASE_URL
from models import Video

async def migrate():
    if not s3_client:
        print("❌ R2 client not initialized. Check your .env.")
        return

    engine = create_engine(DATABASE_URL)
    print(f"DEBUG: Connecting to database: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL}")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        with Session(engine) as session:
            all_videos = session.exec(select(Video)).all()
            print(f"DEBUG: Total videos in DB: {len(all_videos)}")
            for v in all_videos:
                print(f"  - [{v.id}] {v.title}: {v.video_url}")

            # Find videos still on Supabase
            statement = select(Video).where(
                (Video.video_url.contains('supabase.co')) | 
                (Video.manim_source_url.contains('supabase.co'))
            )
            videos_to_migrate = session.exec(statement).all()
            
            if not videos_to_migrate:
                print("✅ No videos found that need migration.")
                return

            print(f"📦 Found {len(videos_to_migrate)} records to migrate.")
            
            for video in videos_to_migrate:
                print(f"\n🚀 Migrating: {video.title} (ID: {video.id})")
                
                # Migrate Video
                if video.video_url and 'supabase.co' in video.video_url:
                    old_url = video.video_url
                    filename = old_url.split('/')[-1]
                    print(f"  - Downloading video: {filename}...")
                    
                    try:
                        resp = await client.get(old_url)
                        resp.raise_for_status()
                        file_data = resp.content
                        
                        print(f"  - Uploading to R2: {filename}...")
                        s3_client.put_object(
                            Bucket=R2_BUCKET_NAME,
                            Key=filename,
                            Body=file_data,
                            ContentType='video/mp4'
                        )
                        
                        new_url = f"{R2_PUBLIC_DOMAIN}/{filename}"
                        video.video_url = new_url
                        print(f"  ✅ Video migrated to: {new_url}")
                    except Exception as e:
                        print(f"  ❌ Failed to migrate video: {e}")

                # Migrate Source Code
                if video.manim_source_url and 'supabase.co' in video.manim_source_url:
                    old_src_url = video.manim_source_url
                    src_filename = old_src_url.split('/')[-1]
                    print(f"  - Downloading source: {src_filename}...")
                    
                    try:
                        resp = await client.get(old_src_url)
                        resp.raise_for_status()
                        src_data = resp.content
                        
                        print(f"  - Uploading to R2: {src_filename}...")
                        s3_client.put_object(
                            Bucket=R2_BUCKET_NAME,
                            Key=src_filename,
                            Body=src_data,
                            ContentType='text/plain; charset=utf-8'
                        )
                        
                        new_src_url = f"{R2_PUBLIC_DOMAIN}/{src_filename}"
                        video.manim_source_url = new_src_url
                        print(f"  ✅ Source migrated to: {new_src_url}")
                    except Exception as e:
                        print(f"  ❌ Failed to migrate source: {e}")

                session.add(video)
                session.commit()
                print(f"✨ Record updated for {video.title}")

    print("\n🏁 All migrations complete.")

if __name__ == "__main__":
    asyncio.run(migrate())
