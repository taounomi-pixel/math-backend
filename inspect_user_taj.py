import os
import psycopg2
from dotenv import load_dotenv

# Load .env
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found")
    exit(1)

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

print(f"Inspecting user 'taj' in: {DATABASE_URL.split('@')[-1]}")

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    # Query taj's details
    cur.execute("""
        SELECT id, username, email, supabase_uid, auth_provider, identities_json, is_admin 
        FROM public.users 
        WHERE username = 'taj' OR email = 'taounomi@gmail.com'
    """)
    rows = cur.fetchall()
    
    if not rows:
        print("User 'taj' or 'taounomi@gmail.com' not found.")
    else:
        colnames = [desc[0] for desc in cur.description]
        for row in rows:
            print("-" * 40)
            user_dict = dict(zip(colnames, row))
            for key, val in user_dict.items():
                print(f"{key}: {val}")

    conn.close()
except Exception as e:
    print(f"Error: {e}")
