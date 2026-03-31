import sqlite3
import os

def migrate():
    # Path to the database
    db_path = "mathvis.db"
    
    if not os.path.exists(db_path):
        print(f"Database {db_path} not found. Cannot migrate.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Add tags column
        print("Adding 'tags' column to videos table...")
        cursor.execute("ALTER TABLE videos ADD COLUMN tags VARCHAR")
        conn.commit()
        print("Successfully added 'tags' column.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("Column 'tags' already exists.")
        else:
            print(f"Error checking/adding column: {e}")

    conn.close()

if __name__ == "__main__":
    migrate()
