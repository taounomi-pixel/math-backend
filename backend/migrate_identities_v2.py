import os
import psycopg2
import json
from dotenv import load_dotenv

# Load .env
env_path = 'backend/.env'
load_dotenv(env_path)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found")
    exit(1)

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

try:
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()

    # 1. Add identities_json column if not exists
    print("Adding identities_json column...")
    cur.execute("ALTER TABLE public.users ADD COLUMN IF NOT EXISTS identities_json TEXT DEFAULT '[]'")

    # 2. Migrate existing auth_provider to identities_json
    print("Migrating existing auth_provider data...")
    cur.execute("SELECT id, auth_provider, identities_json FROM public.users")
    users = cur.fetchall()
    
    for user_id, auth_provider, identities_json in users:
        # If identities_json is '[]' or null, and we have an auth_provider, populate it
        current_list = json.loads(identities_json or '[]')
        if not current_list and auth_provider:
            new_list = [auth_provider]
            cur.execute(
                "UPDATE public.users SET identities_json = %s WHERE id = %s",
                (json.dumps(new_list), user_id)
            )
            print(f"Migrated user {user_id}: {auth_provider} -> {new_list}")

    print("Migration successful.")
    conn.close()
except Exception as e:
    print(f"Error: {e}")
