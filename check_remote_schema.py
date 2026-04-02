from sqlmodel import Session, text
from database import engine

def check_schema():
    with engine.connect() as conn:
        print("Checking public.users table columns...")
        res = conn.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND table_schema = 'public';
        """))
        for row in res:
            print(f"Column: {row[0]}, Type: {row[1]}")

if __name__ == "__main__":
    check_schema()
