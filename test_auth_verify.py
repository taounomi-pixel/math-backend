import os
import sys
from jose import jwt
from datetime import datetime, timedelta, timezone

# Add parent directory to path to import auth
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from auth import verify_supabase_token, SUPABASE_JWT_SECRET
except ImportError:
    print("Error: Could not import auth.py. Make sure this script is run from the backend directory.")
    sys.exit(1)

def test_jwt_verification():
    print(f"Testing JWT Verification with SECRET length: {len(SUPABASE_JWT_SECRET)}")
    
    if not SUPABASE_JWT_SECRET:
        print("❌ Error: SUPABASE_JWT_SECRET is empty.")
        return

    # 1. Create a dummy Supabase-like token
    payload = {
        "sub": "test-supabase-uid-123",
        "email": "test@example.com",
        "app_metadata": {
            "provider": "github"
        },
        "exp": datetime.now(timezone.utc) + timedelta(hours=1)
    }
    
    token = jwt.encode(payload, SUPABASE_JWT_SECRET, algorithm="HS256")
    print(f"Generated test token: {token[:20]}...")

    # 2. Verify using the backend's function
    result = verify_supabase_token(token)
    
    if result and result["sub"] == "test-supabase-uid-123":
        print("✅ SUCCESS: Backend successfully decoded the token using the configured secret!")
        print(f"Result: {result}")
    else:
        print("❌ FAILURE: Backend failed to decode the token correctly.")
        print(f"Result: {result}")

if __name__ == "__main__":
    test_jwt_verification()
