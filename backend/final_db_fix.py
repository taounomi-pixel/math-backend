import psycopg2
import json

# Connection string
DATABASE_URL = "postgresql://postgres:hoqnejmcrqznkcxzcagm@db.hoqnejmcrqznkcxzcagm.supabase.co:5432/postgres"

def fix_taj_and_others():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # 1. Specifically fix taj for testing
        print("Updating taj...")
        cur.execute("""
            UPDATE public.users 
            SET identities_json = '["google", "github"]' 
            WHERE username = 'taj';
        """)
        
        # 2. Bulk fix for any user with auth_provider but NO identities_json
        print("Bulk updating other users...")
        cur.execute("""
            UPDATE public.users 
            SET identities_json = json_build_array(auth_provider)
            WHERE identities_json IS NULL AND auth_provider IS NOT NULL;
        """)
        
        conn.commit()
        print("Update successful!")
        
        # 3. Verify taj again
        cur.execute("SELECT username, identities_json FROM public.users WHERE username = 'taj';")
        row = cur.fetchone()
        print(f"Verified Record -> User: {row[0]}, Identities: {row[1]}")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fix_taj_and_others()
