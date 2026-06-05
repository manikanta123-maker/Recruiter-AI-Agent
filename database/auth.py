import os
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from datetime import datetime, timedelta
from typing import List

# Security configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "recruiter_ai_super_secret_session_key_2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120

security = HTTPBearer()

# Static mock user registry for local testing when Firebase/Auth0 are not configured
MOCK_USERS = {
    "recruiter@recruiter.ai": {
        "email": "recruiter@recruiter.ai",
        "password": "recruiter123", # simple plaintext for development/testing
        "role": "Recruiter"
    },
    "manager@recruiter.ai": {
        "email": "manager@recruiter.ai",
        "password": "manager123",
        "role": "HiringManager"
    },
    "admin@recruiter.ai": {
        "email": "admin@recruiter.ai",
        "password": "admin123",
        "role": "Admin"
    }
}

def create_access_token(data: dict) -> str:
    """Create a signed JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """FastAPI dependency to extract and verify the bearer token."""
    token = credentials.credentials
    
    # Try Firebase Auth decoding if configured (optional advanced path)
    firebase_project_id = os.getenv("FIREBASE_PROJECT_ID")
    if firebase_project_id:
        try:
            # In a real environment with firebase-admin:
            # from firebase_admin import auth as firebase_auth
            # decoded_token = firebase_auth.verify_id_token(token)
            # return {"email": decoded_token.get("email"), "role": decoded_token.get("role", "Recruiter")}
            pass
        except Exception as e:
            print(f"Firebase token verification failed, falling back to local: {e}")
            
    # Fallback/Default: Decrypt our own signed local JWT
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        role: str = payload.get("role")
        if email is None or role is None:
            raise credentials_exception
        return {"email": email, "role": role}
    except JWTError:
        raise credentials_exception

class RoleChecker:
    """Enforces specific role requirements on API routes."""
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: dict = Depends(get_current_user)):
        user_role = current_user.get("role")
        if user_role not in self.allowed_roles and user_role != "Admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation forbidden for role: {user_role}. Required: {self.allowed_roles}"
            )
        return current_user
