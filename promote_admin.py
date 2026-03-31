import sqlite3
import os

db_path = r'd:\Desktop\数学可视化平台\backend\mathvis.db'

if not os.path.exists(db_path):
    print(f"ERROR: Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("--- Starting Admin Promotion ---")

# 1. Add column if not exists
try:
    cursor.execute("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0")
    print("[INFO] Added 'is_admin' column to 'users' table.")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e).lower():
        print("[INFO] 'is_admin' column already exists.")
    else:
        print(f"[ERROR] Failed to add column: {e}")

# 2. Promote TAO to admin
cursor.execute("UPDATE users SET is_admin = 1 WHERE username = 'TAO'")
if cursor.rowcount > 0:
    print("[SUCCESS] Successfully promoted 'TAO' to admin.")
else:
    print("[WARNING] User 'TAO' not found in database. Checking all users...")
    cursor.execute("SELECT username FROM users")
    users = cursor.fetchall()
    print(f"[INFO] Current users in DB: {[u[0] for u in users]}")

conn.commit()
conn.close()
print("--- Done ---")
