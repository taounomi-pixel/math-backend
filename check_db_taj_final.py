import os
from sqlmodel import Session, create_engine, select
from models import User
import json

# Connection string
DATABASE_URL = "postgresql://postgres:hoqnejmcrqznkcxzcagm@db.hoqnejmcrqznkcxzcagm.supabase.co:5432/postgres"

def check_taj():
    engine = create_engine(DATABASE_URL)
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == "taj")).first()
        if user:
            print(f"User: {user.username}")
            print(f"Email: {user.email}")
            print(f"Auth Provider: {user.auth_provider}")
            print(f"Identities JSON (raw): {user.identities_json}")
            try:
                p_list = json.loads(user.identities_json or "[]")
                print(f"Parsed List: {p_list}")
            except Exception as e:
                print(f"Failed to parse JSON: {e}")
        else:
            print("User 'taj' not found")

if __name__ == "__main__":
    check_taj()
