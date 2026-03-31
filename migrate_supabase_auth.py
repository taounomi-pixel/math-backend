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
        # Check if columns already exist in the 'public' schema before adding
        result = conn.execute(text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'users' AND table_schema = 'public'
        """))
        existing_columns = [row[0] for row in result]
        print(f"DEBUG: Existing columns in public.users: {existing_columns}")
        
        if 'supabase_uid' not in existing_columns:
            conn.execute(text("""
                ALTER TABLE public.users ADD COLUMN supabase_uid TEXT UNIQUE
            """))
            print("✅ Added supabase_uid column to public.users")
        else:
            print("ℹ️  supabase_uid column already exists in public.users")
            
        if 'email' not in existing_columns:
            conn.execute(text("""
                ALTER TABLE public.users ADD COLUMN email TEXT
            """))
            print("✅ Added email column to public.users")
        else:
            print("ℹ️  email column already exists in public.users")
            
        if 'auth_provider' not in existing_columns:
            conn.execute(text("""
                ALTER TABLE public.users ADD COLUMN auth_provider TEXT
            """))
            print("✅ Added auth_provider column to public.users")
        else:
            print("ℹ️  auth_provider column already exists in public.users")
        
        # Make password_hash nullable (for OAuth-only users)
        try:
            conn.execute(text("""
                ALTER TABLE public.users ALTER COLUMN password_hash DROP NOT NULL
            """))
            print("✅ Made password_hash nullable in public.users")
        except Exception as e:
            print(f"ℹ️  password_hash already nullable or error in public.users: {e}")
        
        # Create index on supabase_uid for fast lookups
        try:
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_users_supabase_uid ON public.users (supabase_uid)
            """))
            print("✅ Created index on supabase_uid in public.users")
        except Exception as e:
            print(f"ℹ️  Index creation note for public.users: {e}")
        
        conn.commit()
        print("🎉 Supabase Auth migration complete!")

if __name__ == "__main__":
    migrate()
