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

print(f"Connecting to: {DATABASE_URL.split('@')[-1]}")

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    # 1. Check current database name
    cur.execute("SELECT current_database()")
    print(f"Current Database: {cur.fetchone()[0]}")

    # 2. Check search path
    cur.execute("SHOW search_path")
    print(f"Search path: {cur.fetchone()[0]}")

    # 3. List all 'users' tables across all schemas
    cur.execute("""
        SELECT table_schema, table_name 
        FROM information_schema.tables 
        WHERE table_name = 'users'
    """)
    tables = cur.fetchall()
    print(f"Users tables found: {tables}")

    # 4. List columns for each found 'users' table
    for schema, table in tables:
        cur.execute(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = '{table}' AND table_schema = '{schema}'
        """)
        columns = [row[0] for row in cur.fetchall()]
        print(f"Columns in {schema}.{table}: {columns}")

    conn.close()
except Exception as e:
    print(f"Error: {e}")
