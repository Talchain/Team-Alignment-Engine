"""Authentication models."""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


class Token(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Token expiration in seconds")


class TokenData(BaseModel):
    """Decoded token data."""

    user_id: UUID
    email: EmailStr
    role: str
    exp: datetime
    iat: datetime


class User(BaseModel):
    """User model for authentication."""

    user_id: UUID
    email: EmailStr
    role: str = Field(
        description="User role: admin, team_lead, stakeholder, viewer"
    )
    is_active: bool = True
    team_id: Optional[UUID] = None
    organization_id: Optional[UUID] = None

    class Config:
        """Pydantic config."""
        from_attributes = True
