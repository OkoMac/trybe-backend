"""User schemas - Pydantic models for API validation"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
import uuid


class UserBase(BaseModel):
    """Base user schema"""
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    phone: Optional[str] = Field(None, max_length=20)
    bio: Optional[str] = None
    location: Optional[dict] = None
    user_type: str = Field(default="professional")


class UserCreate(UserBase):
    """Schema for creating a new user"""
    password: str = Field(..., min_length=12, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password complexity"""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            raise ValueError("Password must contain at least one special character")
        return v


class UserUpdate(BaseModel):
    """Schema for updating a user"""
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    location: Optional[dict] = None


class UserResponse(UserBase):
    """Schema for user response"""
    id: uuid.UUID
    avatar_url: Optional[str] = None
    verification_status: str
    is_active: bool
    is_verified: bool
    user_metadata: Optional[dict] = None
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

    model_config = {"from_attributes": True}


class UserLogin(BaseModel):
    """Schema for user login"""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Schema for token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse
