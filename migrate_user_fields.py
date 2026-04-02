import os
from sqlalchemy import text
from database import engine

def migrate():
    """Simple migration to add last_login_at and updated_at to the users table if they don't exist."""
    print("Running migration for user fields...")
    with engine.connect() as conn:
        # Check if columns exist (agnostic to SQLite/PostgreSQL)
        # We can try to add them and catch the error if they already exist, 
        # but a cleaner way is to check the table info.
        
        try:
            # Check SQLite
            if engine.url.drivername == "sqlite":
                columns = [row[1] for row in conn.execute(text("PRAGMA table_info(users)")).fetchall()]
            else:
                # Check PostgreSQL
                query = text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'users'
                """)
                columns = [row[0] for row in conn.execute(query).fetchall()]
            
            if 'last_login_at' not in columns:
                print("Adding 'last_login_at' column...")
                conn.execute(text("ALTER TABLE users ADD COLUMN last_login_at TIMESTAMP WITH TIME ZONE"))
                conn.commit()
            
            if 'updated_at' not in columns:
                print("Adding 'updated_at' column...")
                conn.execute(text("ALTER TABLE users ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE"))
                # Set initial values for updated_at
                conn.execute(text("UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL"))
                conn.commit()
            
            print("Migration completed successfully.")
        except Exception as e:
            print(f"Migration error (this might be normal if columns already exist): {e}")

if __name__ == "__main__":
    migrate()
