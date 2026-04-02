import os
from sqlmodel import create_engine, SQLModel
from dotenv import load_dotenv
from supabase import create_client, Client

# MUST load environment variables before using them
load_dotenv()

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./mathvis.db")

# Render and Supabase often use 'postgres://', but SQLModel/SQLAlchemy requires 'postgresql://'
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Optimization for Supabase Pooler and Connection Stability
connect_args = {}
if DATABASE_URL.startswith("postgresql"):
    connect_args = {"sslmode": "require"}
else:
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, echo=True, connect_args=connect_args)

# Supabase setup - MANDATORY for Auth
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET_NAME", "videos")

if not SUPABASE_URL:
    print("❌ CRITICAL ERROR: SUPABASE_URL not found in environment!")
if not SUPABASE_ANON_KEY:
    print("❌ CRITICAL ERROR: SUPABASE_ANON_KEY not found in environment!")

supabase: Client = None
if SUPABASE_URL and SUPABASE_ANON_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        print("✅ Supabase Client initialized.")
    except Exception as e:
        print(f"❌ FAILED to initialize Supabase Client: {e}")

supabase_admin: Client = None
if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY:
    try:
        supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        print("✅ Supabase Admin Client initialized.")
    except Exception as e:
        print(f"❌ FAILED to initialize Supabase Admin Client: {e}")
elif SUPABASE_URL:
    print("⚠️ WARNING: SUPABASE_SERVICE_ROLE_KEY missing. Admin operations disabled.")

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
