"""
Authentication utilities for user sessions and JWT tokens.
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from . import crud, models
from .database import get_db

# Secret key for JWT - in production, use environment variable
SECRET_KEY = "your-secret-key-change-this-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 43200  # 30 days

security = HTTPBearer(auto_error=False)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[models.User]:
    """
    Get current user from JWT token in Authorization header or cookie.
    Returns None if not authenticated (doesn't raise exception).
    """
    token = None
    
    # Try to get token from Authorization header
    if credentials:
        token = credentials.credentials
    # Try to get token from cookie
    elif "access_token" in request.cookies:
        token = request.cookies.get("access_token")
    
    if not token:
        return None
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
    except JWTError:
        return None
    
    user = crud.get_user_by_username(db, username=username)
    if not user or not user.is_active:
        return None
    
    return user


def get_current_user(
    user: Optional[models.User] = Depends(get_current_user_optional)
) -> models.User:
    """
    Get current user, raise exception if not authenticated.
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return user


def get_current_subscribed_user(
    user: models.User = Depends(get_current_user)
) -> models.User:
    """
    Get current user and verify they are subscribed.
    """
    if not user.is_subscribed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Subscription required to access this feature",
        )
    return user


def get_current_admin_user(
    user: models.User = Depends(get_current_user)
) -> models.User:
    """
    Get current user and verify they are admin.
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return user


def get_current_admin_user(
    user: models.User = Depends(get_current_user)
) -> models.User:
    """
    Get current user and verify they are admin.
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return user


def set_auth_cookie(response: Response, token: str):
    """Set authentication token in HTTP-only cookie."""
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
    )


def clear_auth_cookie(response: Response):
    """Clear authentication cookie."""
    response.delete_cookie(key="access_token")
