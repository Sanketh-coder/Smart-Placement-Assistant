"""Password hashing (PBKDF2-SHA256, salted) and JWT authentication helpers."""
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

import models
from database import get_db

JWT_SECRET = os.getenv("JWT_SECRET", "dev-only-secret-change-me")
JWT_ALG = "HS256"
JWT_EXPIRE_MIN = int(os.getenv("JWT_EXPIRE_MINUTES", "120"))
_ITER = 200_000
bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITER)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split("$")
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), _ITER)
    except ValueError:
        return False
    return hmac.compare_digest(digest.hex(), digest_hex)


def create_token(student: models.Student) -> str:
    payload = {
        "sub": str(student.student_id),
        "role": student.role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MIN),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)
) -> models.Student:
    err = HTTPException(status.HTTP_401_UNAUTHORIZED, "Please log in to continue.", headers={"WWW-Authenticate": "Bearer"})
    if creds is None:
        raise err
    try:
        data = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALG])
        user = db.get(models.Student, int(data["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        raise err
    if user is None:
        raise err
    return user


def require_admin(user: models.Student = Depends(get_current_user)) -> models.Student:
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Administrator access required.")
    return user
