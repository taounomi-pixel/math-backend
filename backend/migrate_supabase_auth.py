"""
Migration script: Add Supabase Auth columns to users table.
Adds: supabase_uid, email, auth_provider columns.
Makes password_hash nullable for OAuth-only users.
"""
import os
from sqlalchemy import text
from database import engine

def migrate():
    """Run migration using raw SQL for PostgreSQL compatibility."""
    with engine.connect() as conn:
        # Check if columns already exist before adding
        result = conn.execute(text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'users'
        """))
        existing_columns = [row[0] for row in result]
        
        if 'supabase_uid' not in existing_columns:
            conn.execute(text("""
                ALTER TABLE users ADD COLUMN supabase_uid TEXT UNIQUE
            """))
            print("✅ Added supabase_uid column")
        else:
            print("ℹ️  supabase_uid column already exists")
            
        if 'email' not in existing_columns:
            conn.execute(text("""
                ALTER TABLE users ADD COLUMN email TEXT
            """))
            print("✅ Added email column")
        else:
            print("ℹ️  email column already exists")
            
        if 'auth_provider' not in existing_columns:
            conn.execute(text("""
                ALTER TABLE users ADD COLUMN auth_provider TEXT
            """))
            print("✅ Added auth_provider column")
        else:
            print("ℹ️  auth_provider column already exists")
        
        # Make password_hash nullable (for OAuth-only users)
        try:
            conn.execute(text("""
                ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL
            """))
            print("✅ Made password_hash nullable")
        except Exception as e:
            print(f"ℹ️  password_hash already nullable or error: {e}")
        
        # Create index on supabase_uid for fast lookups
        try:
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_users_supabase_uid ON users (supabase_uid)
            """))
            print("✅ Created index on supabase_uid")
        except Exception as e:
            print(f"ℹ️  Index creation note: {e}")
        
        conn.commit()
        print("🎉 Supabase Auth migration complete!")

if __name__ == "__main__":
    migrate()
