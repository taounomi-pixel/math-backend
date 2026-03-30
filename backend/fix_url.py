import sqlite3
import os

url = 'https://hoqnejmcrqznkcxzcagm.supabase.co/storage/v1/object/public/Videos/a86c8054-17bf-4185-8140-8bf72b4c8895_AmazingMathEquations.mp4'

try:
    with sqlite3.connect('mathvis.db') as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE videos SET video_url = ?", (url,))
        conn.commit()
        print("Updated video URL successfully.")
except Exception as e:
    print(f"Error: {e}")
