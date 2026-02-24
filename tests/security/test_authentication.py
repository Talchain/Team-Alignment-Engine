"""Security tests for authentication and authorization."""

import pytest
from fastapi import HTTPException
from uuid import uuid4
from datetime import datetime, timedelta
from jose import jwt

from src.auth.jwt import create_access_token, verify_token
from src.auth.models import User
from src.config import settings


class TestJWTAuthentication:
    """Test JWT token creation and verification."""

    def test_create_access_token(self):
        """Test creating a valid JWT token."""
        user_id = uuid4()
        email = "test@example.com"
        role = "admin"

        token = create_access_token(user_id=user_id, email=email, role=role)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_valid_token(self):
        """Test verifying a valid token."""
        user_id = uuid4()
        email = "test@example.com"
        role = "admin"

        token = create_access_token(user_id=user_id, email=email, role=role)
        payload = verify_token(token)

        assert payload["sub"] == str(user_id)
        assert payload["email"] == email
        assert payload["role"] == role
        assert "exp" in payload
        assert "iat" in payload

    def test_verify_expired_token(self):
        """Test that expired tokens are rejected."""
        user_id = uuid4()
        email = "test@example.com"
        role = "admin"

        # Create token that expired 1 hour ago
        token = create_access_token(
            user_id=user_id,
            email=email,
            role=role,
            expires_delta=timedelta(hours=-1)
        )

        with pytest.raises(Exception):  # JWT library raises JWTError
            verify_token(token)

    def test_verify_invalid_signature(self):
        """Test that tokens with invalid signatures are rejected."""
        # Create token with different secret
        payload = {
            "sub": str(uuid4()),
            "email": "test@example.com",
            "role": "admin",
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow(),
        }
        invalid_token = jwt.encode(payload, "wrong_secret", algorithm="HS256")

        with pytest.raises(Exception):
            verify_token(invalid_token)

    def test_token_expiration_time(self):
        """Test that tokens have correct expiration time."""
        user_id = uuid4()
        token = create_access_token(
            user_id=user_id,
            email="test@example.com",
            role="admin"
        )
        payload = verify_token(token)

        exp_timestamp = payload["exp"]
        iat_timestamp = payload["iat"]

        # Difference should be approximately jwt_expiration_minutes
        diff_minutes = (exp_timestamp - iat_timestamp) / 60

        assert abs(diff_minutes - settings.jwt_expiration_minutes) < 1


class TestAuthorizationRoles:
    """Test role-based access control."""

    def test_admin_role_token(self):
        """Test creating token with admin role."""
        token = create_access_token(
            user_id=uuid4(),
            email="admin@example.com",
            role="admin"
        )
        payload = verify_token(token)
        assert payload["role"] == "admin"

    def test_team_lead_role_token(self):
        """Test creating token with team_lead role."""
        token = create_access_token(
            user_id=uuid4(),
            email="lead@example.com",
            role="team_lead"
        )
        payload = verify_token(token)
        assert payload["role"] == "team_lead"

    def test_stakeholder_role_token(self):
        """Test creating token with stakeholder role."""
        token = create_access_token(
            user_id=uuid4(),
            email="stakeholder@example.com",
            role="stakeholder"
        )
        payload = verify_token(token)
        assert payload["role"] == "stakeholder"


class TestUserModel:
    """Test User model validation."""

    def test_valid_user(self):
        """Test creating a valid user."""
        user = User(
            user_id=uuid4(),
            email="test@example.com",
            role="admin",
            is_active=True
        )

        assert user.is_active is True
        assert user.role == "admin"

    def test_user_with_team(self):
        """Test user with team assignment."""
        team_id = uuid4()
        user = User(
            user_id=uuid4(),
            email="test@example.com",
            role="team_lead",
            is_active=True,
            team_id=team_id
        )

        assert user.team_id == team_id

    def test_inactive_user(self):
        """Test creating an inactive user."""
        user = User(
            user_id=uuid4(),
            email="test@example.com",
            role="stakeholder",
            is_active=False
        )

        assert user.is_active is False
