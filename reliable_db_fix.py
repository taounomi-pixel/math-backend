from sqlmodel import Session, select, text
from database import engine
from models import User
import json

def reliable_fix():
    with Session(engine) as session:
        print("Starting reliable database update...")
        
        # 1. Update taj specifically
        user_taj = session.exec(select(User).where(User.username == "taj")).first()
        if user_taj:
            print(f"Updating user 'taj' (ID: {user_taj.id})...")
            user_taj.identities_json = json.dumps(["google", "github"])
            session.add(user_taj)
            print("Successfully updated 'taj' identities_json to ['google', 'github']")
        else:
            print("User 'taj' not found!")

        # 2. Bulk update users who have auth_provider but missing identities_json
        # Using raw SQL for cleaner bulk updates of JSON fields if needed, 
        # but let's stick to object-based for safety first.
        all_users = session.exec(select(User).where(User.identities_json == None).where(User.auth_provider != None)).all()
        print(f"Found {len(all_users)} users needing identity initialization.")
        for u in all_users:
            u.identities_json = json.dumps([u.auth_provider])
            session.add(u)
            
        session.commit()
        print("Database commit successful.")

        # 3. Final Verification
        session.refresh(user_taj)
        print(f"VERIFICATION: taj is now {user_taj.identities_json}")

if __name__ == "__main__":
    reliable_fix()
