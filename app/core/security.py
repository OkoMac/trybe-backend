"""Security utilities - JWT tokens and password hashing"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
import uuid

from app.core.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


def get_password_hash(password: str) -> str:
    """Hash a password"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token

    Args:
        data: Data to encode in token (should include 'sub' for user_id)
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access",
        "jti": str(uuid.uuid4())  # JWT ID for token tracking
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """
    Create JWT refresh token

    Args:
        data: Data to encode in token (should include 'sub' for user_id)

    Returns:
        Encoded JWT refresh token string
    """
    to_encode = data.copy()

    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh",
        "jti": str(uuid.uuid4())
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """
    Decode and verify JWT token

    Args:
        token: JWT token string

    Returns:
        Decoded token payload or None if invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def verify_token(token: str, token_type: str = "access") -> Optional[dict]:
    """
    Verify token is valid and of correct type

    Args:
        token: JWT token string
        token_type: Expected token type ('access' or 'refresh')

    Returns:
        Decoded payload if valid, None otherwise
    """
    payload = decode_token(token)

    if payload is None:
        return None

    # Verify token type
    if payload.get("type") != token_type:
        return None

    # Verify expiration
    exp = payload.get("exp")
    if exp is None or datetime.fromtimestamp(exp) < datetime.utcnow():
        return None

    return payload
