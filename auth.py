# auth.py
import os, time, jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database import get_db
from models import User
from passlib.hash import pbkdf2_sha256

security = HTTPBearer()
SECRET_KEY = os.getenv("JWT_SECRET", "local-secret-key-change-me")

def get_password_hash(password: str) -> str:
    return pbkdf2_sha256.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    return pbkdf2_sha256.verify(password, hashed)

def create_access_token(data: dict, expires_in: int = 60*60*8) -> str:
    to_encode = data.copy()
    to_encode.update({"exp": int(time.time()) + expires_in})
    return jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except Exception:
        raise HTTPException(status_code=401, detail="Token invalide")
    user_id = int(payload.get("sub", "0"))
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur introuvable")
    return user
