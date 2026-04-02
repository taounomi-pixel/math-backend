import psycopg2
import os
from dotenv import load_dotenv

# Load original .env
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found in .env")
    exit(1)

print("--- Connecting to Production Database ---")
try:
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cursor = conn.cursor()
    
    print("[INFO] Connected successfully.")
    
    # 1. Add column if not exists
    # PostgreSQL doesn't have IF NOT EXISTS in ALTER TABLE directly for columns in older versions,
    # so we check if it exists first.
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='users' AND column_name='is_admin' AND table_schema='public'
    """)
    if not cursor.fetchone():
        print("[INFO] Adding 'is_admin' column to public.users table...")
        cursor.execute("ALTER TABLE public.users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE")
        print("[SUCCESS] Column added.")
    else:
        print("[INFO] 'is_admin' column already exists in public.users.")
        
    # 2. Promote TAO to admin
    print("[INFO] Promoting 'TAO' to admin in public.users...")
    cursor.execute("UPDATE public.users SET is_admin = TRUE WHERE username = 'TAO'")
    if cursor.rowcount > 0:
        print("[SUCCESS] Successfully promoted 'TAO' to admin in production.")
    else:
        print("[WARNING] User 'TAO' not found in production DB.")
        cursor.execute("SELECT username FROM users")
        found = [u[0] for u in cursor.fetchall()]
        print(f"[INFO] Current users in production: {found}")
        
    conn.close()
    print("--- Done ---")
except Exception as e:
    print(f"[ERROR] Migration failed: {e}")
    exit(1)
