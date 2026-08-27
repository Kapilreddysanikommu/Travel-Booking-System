"""
Shared authentication helpers: password hashing and JWT creation/verification.

Every service imports from here instead of re-implementing hashing or token
logic, so all 4 services trust tokens signed with the same secret and agree
on the same expiry rules.
"""

import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-only-insecure-secret")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))  # 24 hours

# CryptContext manages hashing scheme details (bcrypt) so callers never
# touch bcrypt directly - if we ever migrate hashing schemes, this is the
# only place that changes.
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTPBearer parses the "Authorization: Bearer <token>" header for us and
# raises a 403 automatically if the header is missing entirely.
_bearer_scheme = HTTPBearer()


def hash_password(plain_password: str) -> str:
    """Turn a plaintext password into a one-way bcrypt hash for storage."""
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a login attempt against the stored hash. True if it matches."""
    return _pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: str) -> str:
    """
    Build a signed JWT containing the user_id and an expiry claim.

    "sub" (subject) is the JWT-standard claim name for who the token is
    about - using it instead of a custom field name keeps this compatible
    with other JWT tooling.
    """
    expire_at = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {"sub": user_id, "exp": expire_at}
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> str:
    """
    Verify a JWT's signature and expiry, return the user_id inside it.

    Raises HTTPException(401) if the token is invalid, tampered with, or
    expired - jose's jwt.decode checks the signature and "exp" claim for us.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return payload["sub"]


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> str:
    """
    FastAPI dependency: require a valid JWT and return the user_id inside it.

    Any route can require auth by adding `user_id: str = Depends(get_current_user)`
    as a parameter - FastAPI runs this function first, and the route only
    executes if it returns successfully.
    """
    return decode_access_token(credentials.credentials)
