"""Authentication endpoints - Register, Login, Refresh Token"""

from datetime import datetime
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    verify_token
)
from app.models.user import User
from app.schemas.user import (
    UserCreate,
    UserResponse,
    TokenResponse,
    UserLogin
)
from app.api.deps import get_current_user

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Register a new user

    - **email**: Valid email address (will be validated)
    - **password**: Minimum 12 characters with complexity requirements
    - **full_name**: User's full name
    - **username**: Unique username (3-50 characters, alphanumeric, -, _)
    - **user_type**: professional, employer, or company
    """
    # Check if email already exists
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Check if username already exists
    result = await db.execute(
        select(User).where(User.username == user_data.username)
    )
    existing_username = result.scalar_one_or_none()

    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    # Create new user
    hashed_password = get_password_hash(user_data.password)

    new_user = User(
        email=user_data.email,
        password_hash=hashed_password,
        full_name=user_data.full_name,
        username=user_data.username,
        phone=user_data.phone,
        bio=user_data.bio,
        location=user_data.location,
        user_type=user_data.user_type
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Generate tokens
    access_token = create_access_token(data={"sub": str(new_user.id)})
    refresh_token = create_refresh_token(data={"sub": str(new_user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=UserResponse.model_validate(new_user)
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    OAuth2 compatible token login

    - **username**: Email address
    - **password**: User password
    """
    # Find user by email (username field contains email)
    result = await db.execute(
        select(User).where(User.email == form_data.username)
    )
    user = result.scalar_one_or_none()

    # Verify user exists and password is correct
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account"
        )

    # Update last login
    user.last_login = datetime.utcnow()
    await db.commit()

    # Generate tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.post("/login/json", response_model=TokenResponse)
async def login_json(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    JSON login endpoint (alternative to OAuth2 form)

    - **email**: User email address
    - **password**: User password
    """
    # Find user by email
    result = await db.execute(
        select(User).where(User.email == credentials.email)
    )
    user = result.scalar_one_or_none()

    # Verify user exists and password is correct
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account"
        )

    # Update last login
    user.last_login = datetime.utcnow()
    await db.commit()

    # Generate tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Refresh access token using refresh token

    - **refresh_token**: Valid refresh token
    """
    # Verify refresh token
    payload = verify_token(refresh_token, token_type="refresh")

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    # Get user_id from token
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    # Fetch user
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account"
        )

    # Generate new tokens
    new_access_token = create_access_token(data={"sub": str(user.id)})
    new_refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get current user information

    Requires valid access token in Authorization header
    """
    return UserResponse.model_validate(current_user)


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Logout current user

    Note: With JWT tokens, logout is typically handled client-side by removing the token.
    This endpoint is provided for consistency and can be enhanced with token blacklisting.
    """
    return {
        "message": "Successfully logged out",
        "detail": "Please remove your access and refresh tokens from client storage"
    }
