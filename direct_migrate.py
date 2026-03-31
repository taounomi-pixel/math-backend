import os
import psycopg2
from dotenv import load_dotenv

# Load original .env
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found in .env")
    exit(1)

# Fix postgresql:// prefix
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

print(f"Connecting to: {DATABASE_URL.split('@')[-1]}") # Hide password in logs

try:
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cursor = conn.cursor()
    
    print("[INFO] Connected successfully.")
    
    # Check current columns in public.users table
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'users' AND table_schema = 'public'
    """)
    existing_columns = [row[0] for row in cursor.fetchall()]
    print(f"[INFO] Existing columns in 'public.users': {existing_columns}")
    
    # 1. Add 'email' column if not exists
    if 'email' not in existing_columns:
        print("[INFO] Adding 'email' column to public.users...")
        cursor.execute("ALTER TABLE public.users ADD COLUMN email TEXT")
        print("[SUCCESS] 'email' column added.")
    
    # 2. Add 'supabase_uid' column if not exists
    if 'supabase_uid' not in existing_columns:
        print("[INFO] Adding 'supabase_uid' column to public.users...")
        cursor.execute("ALTER TABLE public.users ADD COLUMN supabase_uid TEXT UNIQUE")
        print("[SUCCESS] 'supabase_uid' column added.")
        
    # 3. Add 'auth_provider' column if not exists
    if 'auth_provider' not in existing_columns:
        print("[INFO] Adding 'auth_provider' column to public.users...")
        cursor.execute("ALTER TABLE public.users ADD COLUMN auth_provider TEXT")
        print("[SUCCESS] 'auth_provider' column added.")

    # 4. Make 'password_hash' nullable if it's not already
    print("[INFO] Making 'password_hash' nullable...")
    try:
        cursor.execute("ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL")
        print("[SUCCESS] 'password_hash' is now nullable.")
    except Exception as e:
        print(f"[INFO] 'password_hash' update note: {e}")

    # 5. Add index on supabase_uid
    print("[INFO] Creating index on 'supabase_uid'...")
    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_users_supabase_uid ON users (supabase_uid)")
        print("[SUCCESS] Index created.")
    except Exception as e:
        print(f"[INFO] Index creation note: {e}")
        
    conn.close()
    print("[INFO] All migrations applied successfully.")
    
except Exception as e:
    print(f"[ERROR] Migration failed: {e}")
    exit(1)
