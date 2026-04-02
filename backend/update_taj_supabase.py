import os
from database import supabase
import json

def update_via_api():
    print("Attempting to update user 'taj' via Supabase REST API...")
    
    # 1. Update taj
    res = supabase.table("users").update({
        "identities_json": ["google", "github"]
    }).eq("username", "taj").execute()
    
    if res.data:
        print(f"Successfully updated 'taj': {res.data}")
    else:
        print(f"Failed to update 'taj'. Response: {res}")

    # 2. Bulk update others
    # Note: PostgREST doesn't support "IS NULL" update in a single query easily 
    # without a specific syntax, but let's try to fix taj first to get the user working.
    
if __name__ == "__main__":
    update_via_api()
