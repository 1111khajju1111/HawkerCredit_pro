from datetime import datetime, timedelta
from typing import Optional, Any, Union, List
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False)

# Bcrypt is used directly (rather than through passlib's CryptContext
# wrapper) - per-password random salt generated automatically, adaptive
# work factor. This replaces the previous PBKDF2 implementation that used
# a single hardcoded salt shared across every user in the system (which
# defeats the purpose of salting entirely - identical passwords would
# have produced identical hashes for every vendor/lender/admin).
_BCRYPT_MAX_BYTES = 72  # bcrypt's hard input-length limit


def get_password_hash(password: str) -> str:
    pw_bytes = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pw_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        pw_bytes = plain_password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
        return bcrypt.checkpw(pw_bytes, hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(subject: Union[str, Any], role: str, expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "role": role.upper()
    }
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        return {}


def get_current_user(token: Optional[str] = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    Resolves the authenticated user from a bearer JWT. There is
    intentionally NO unauthenticated fallback identity here: a missing or
    invalid token always results in 401, full stop. (A previous version of
    this function silently returned the first VENDOR row in the database
    when no token was supplied, which meant every "protected" endpoint
    downstream of it was effectively public and vendor data was not
    actually isolated.)
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    from app.models.schema import User
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def require_roles(allowed_roles: List[str]):
    def role_checker(current_user=Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User role '{current_user.role}' is not authorized to access this resource"
            )
        return current_user
    return role_checker


def verify_vendor_access(vendor_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Enforces strict vendor data isolation.
    A vendor can ONLY access their own data. Lenders and Admins can access any vendor.
    """
    if current_user.role in ["LENDER", "ADMIN"]:
        return True

    from app.models.schema import Vendor
    vendor = db.query(Vendor).filter(Vendor.vendor_id == vendor_id).first()
    if not vendor or vendor.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vendor data isolation violation: You are not authorized to access another vendor's profile"
        )
    return True
