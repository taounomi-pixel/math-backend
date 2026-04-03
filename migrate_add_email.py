import sqlite3
import os

db_path = "mathvis.db"

if not os.path.exists(db_path):
    print(f"Database {db_path} not found. Skipping migration.")
    exit(0)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if email column already exists
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if "email" not in columns:
        print("Adding 'email' column to 'users' table...")
        cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")
        # Set index for email
        cursor.execute("CREATE INDEX idx_users_email ON users(email)")
        conn.commit()
        print("Migration successful: Added 'email' column to 'users' table.")
    else:
        print("'email' column already exists in 'users' table. Skipping.")
    
    conn.close()
except Exception as e:
    print(f"Migration failed: {e}")
    exit(1)
