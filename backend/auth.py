from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt

import os

# Security Settings
SECRET_KEY = os.getenv("SECRET_KEY", "SUPER_SECRET_MATHVIS_KEY_CHANGE_IN_PRODUCTION")
if SECRET_KEY == "SUPER_SECRET_MATHVIS_KEY_CHANGE_IN_PRODUCTION":
    print("⚠️ WARNING: Using default insecure SECRET_KEY. Set SECRET_KEY in .env immediately for production!")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 7 days validity

import bcrypt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed one."""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

def get_password_hash(password: str) -> str:
    """Generate a bcrypt hash of the password."""
    # Salt is automatically handled by hashpw
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
