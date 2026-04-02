from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt, JWTError

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Security Settings
SECRET_KEY = os.getenv("SECRET_KEY", "SUPER_SECRET_MATHVIS_KEY_CHANGE_IN_PRODUCTION")
if SECRET_KEY == "SUPER_SECRET_MATHVIS_KEY_CHANGE_IN_PRODUCTION":
    print("⚠️ WARNING: Using default insecure SECRET_KEY. Set SECRET_KEY in .env immediately for production!")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 7 days validity

# Supabase Auth Settings - Fully handled by SDK
# No longer using manual JWT decode for Supabase tokens.

import bcrypt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed one."""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

def get_password_hash(password: str) -> str:
    """Generate a bcrypt hash of the password."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_supabase_token(token: str) -> Optional[dict]:
    """
    Verify a Supabase-issued JWT by calling the Supabase Auth API.
    This automatically handles ES256, HS256, and all other signature algorithms correctly.
    Returns dict with 'sub' (supabase uid), 'email', 'provider' or None if invalid.
    """
    from database import supabase
    
    if not supabase:
        print("❌ ERROR: Supabase client not initialized in database.py!")
        return None
    
    # Strip 'Bearer ' if present
    if token.startswith("Bearer "):
        token = token[7:]
    
    try:
        # SDK get_user(token) validates the token with Supabase and returns the user object
        user_response = supabase.auth.get_user(token)
        user = user_response.user
        
        if not user:
            print("⚠️ Supabase: Token valid but no user found in response.")
            return None
            
        # Return equivalent structure to the previous decoded payload for compatibility
        return {
            "sub": user.id,
            "email": user.email,
            "provider": user.app_metadata.get("provider", "email")
        }
    except Exception as e:
        # Avoid noisy logs if it's just a non-Supabase JWT being passed during handshake
        # But still log for real Supabase authentication issues.
        err_str = str(e)
        if "sub claim" in err_str or "Invalid JWT" in err_str:
            # This is expected when a custom System JWT is passed to this function
            # during the dual-token handshake process.
            pass 
        else:
            print(f"DEBUG: Supabase token verification failed: {err_str}")
        return None
