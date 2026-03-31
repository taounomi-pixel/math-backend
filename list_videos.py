import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(url, key)

bucket = os.environ.get("SUPABASE_BUCKET_NAME")
res = supabase.storage.from_(bucket).list()
for f in res:
    print(f['name'])
