import os
from sqlmodel import Session, select, create_engine
from backend.models import User
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if not DATABASE_URL:
    print("DATABASE_URL not found!")
    exit(1)

engine = create_engine(DATABASE_URL)

print(f"Inspecting with SQLModel engine: {DATABASE_URL.split('@')[-1]}")

with Session(engine) as session:
    try:
        # Try to select the first user
        statement = select(User).limit(1)
        print(f"Generated SQL: {statement}")
        result = session.exec(statement).first()
        if result:
            # Safely check for attributes
            username = getattr(result, 'username', 'N/A')
            email = getattr(result, 'email', 'N/A')
            uid = getattr(result, 'supabase_uid', 'N/A')
            print(f"Found user: {username}, Email: {email}, UID: {uid}")
        else:
            print("No users found in table.")
    except Exception as e:
        print(f"SQLModel Error: {e}")

# Also inspect the table columns via SQLAlchemy inspector
from sqlalchemy import inspect
inspector = inspect(engine)
try:
    columns = inspector.get_columns("users")
    print(f"Columns in 'users' table according to SQLAlchemy: {[c['name'] for c in columns]}")
except Exception as e:
    print(f"Inspector Error: {e}")
