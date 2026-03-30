import os
from sqlmodel import create_engine, SQLModel
from dotenv import load_dotenv

load_dotenv()

# Get DATABASE_URL from environment, fallback to local sqlite for development
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./mathvis.db")

# Render and Supabase often use 'postgres://', but SQLModel/SQLAlchemy requires 'postgresql://'
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Optimization for Supabase Pooler and Connection Stability
connect_args = {}
if DATABASE_URL.startswith("postgresql"):
    # Ensure SSL is used for Supabase cloud connections
    connect_args = {"sslmode": "require"}
else:
    # connect_args={"check_same_thread": False} is required for SQLite inside FastAPI
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, echo=True, connect_args=connect_args)

def create_db_and_tables():
    # This automatically syncs the Models to create empty SQL tables (PostgreSQL/SQLite)
    SQLModel.metadata.create_all(engine)
