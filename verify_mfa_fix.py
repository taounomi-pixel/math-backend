import os
import json
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, Session, create_engine as sqlmodel_create_engine
from datetime import datetime, timedelta, timezone
from jose import jwt

# 1. Setup Mock Environment
os.environ["DATABASE_URL"] = "sqlite:///./test_mfa_verify.db"
os.environ["SUPABASE_URL"] = "https://example.supabase.co"
os.environ["SUPABASE_ANON_KEY"] = "mock-key"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "mock-service-key"
os.environ["SUPABASE_JWT_SECRET"] = "super-secret-key-that-is-at-least-32-chars-long-!!!123"

# Import app after setting env vars
from main import app, get_session, User, engine as real_engine

# 2. Setup Test Database
test_engine = sqlmodel_create_engine("sqlite:///./test_mfa_verify.db", connect_args={"check_same_thread": False})
SQLModel.metadata.create_all(test_engine)

def override_get_session():
    with Session(test_engine) as session:
        yield session

app.dependency_overrides[get_session] = override_get_session

client = TestClient(app)

def test_mfa_handshake():
    print("\n--- Testing MFA Handshake logic ---")
    
    # 1. Create a test user with a bound supabase_uid
    with Session(test_engine) as session:
        test_user = User(
            username="test_mfa_user",
            password_hash="hashed_pw", # Not actually checked in this specific test flow if we mock verify_password
            supabase_uid="test-supabase-uid-999",
            is_active=True
        )
        session.add(test_user)
        session.commit()
    
    # 2. Test /api/login (Password would normally be checked, but let's test the response structure)
    # We need to mock the password check if we want to test /api/login fully, 
    # but the goal is to see if it returns 200 for MFA users.
    # For simplicity, let's assume the password check passes or we test the handler directly.
    
    print("Testing /api/login response for bound user...")
    # Mocking the password check is hard without refactoring main.py
    # So let's test the /api/auth/verify-login directly which was the 401 source.
    
    # 3. Create a valid mock Supabase token
    payload = {
        "sub": "test-supabase-uid-999",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1)
    }
    mock_token = jwt.encode(payload, os.environ["SUPABASE_JWT_SECRET"], algorithm="HS256")
    
    # 4. Test /api/auth/verify-login
    print("Testing /api/auth/verify-login with valid token and username...")
    response = client.post("/api/auth/verify-login", json={
        "username": "test_mfa_user",
        "supabase_token": mock_token
    })
    
    print(f"Response status: {response.status_code}")
    print(f"Response body: {response.json()}")
    
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "access_token" in response.json()
    print("✅ SUCCESS: verify-login works with username/token pair.")

    # 5. Test /api/auth/verify-login WITHOUT username (The new robust fallback)
    print("\nTesting /api/auth/verify-login WITHOUT username (fallback to UID)...")
    response = client.post("/api/auth/verify-login", json={
        "supabase_token": mock_token
    })
    
    print(f"Response status: {response.status_code}")
    print(f"Response body: {response.json()}")
    
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    print("✅ SUCCESS: verify-login works using only Supabase UID from token.")

    # 6. Test /api/auth/verify-login with MISMATCHED username
    print("\nTesting /api/auth/verify-login with identity mismatch...")
    # Create another user
    with Session(test_engine) as session:
        other_user = User(username="wrong_user", supabase_uid="other-uid", is_active=True)
        session.add(other_user)
        session.commit()
        
    response = client.post("/api/auth/verify-login", json={
        "username": "wrong_user",
        "supabase_token": mock_token # Token matches test-supabase-uid-999, not other-uid
    })
    
    print(f"Response status: {response.status_code}")
    print(f"Response body: {response.json()}")
    assert response.status_code == 401
    assert "Identity verification failed" in response.json()["detail"]
    print("✅ SUCCESS: correctly identifies and rejects identity mismatch.")

if __name__ == "__main__":
    try:
        test_mfa_handshake()
    finally:
        # Cleanup
        if os.path.exists("./test_mfa_verify.db"):
            os.remove("./test_mfa_verify.db")
