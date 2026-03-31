import psycopg2
import os

db_url = "postgresql://postgres.hoqnejmcrqznkcxzcagm:3X,qQNemrx.P!6,@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres"

video_url = "https://hoqnejmcrqznkcxzcagm.supabase.co/storage/v1/object/public/Videos/a86c8054-17bf-4185-8140-8bf72b4c8895_AmazingMathEquations.mp4"
bad_url_marker = "EulerEpicycles"

try:
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    # Replace URLs ending with EulerEpicycles.mp4
    cur.execute("UPDATE videos SET video_url = %s WHERE video_url LIKE %s", (video_url, f"%{bad_url_marker}%"))
    print(f"Updated {cur.rowcount} rows in PostgreSQL.")
    conn.commit()
    cur.close()
    conn.close()
except Exception as e:
    print(f"Postgres error: {e}")
