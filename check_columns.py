import os
import psycopg2
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
    cur = conn.cursor()
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'users'")
    columns = cur.fetchall()
    print([col[0] for col in columns])
    conn.close()
except Exception as e:
    print(f"Error: {e}")
