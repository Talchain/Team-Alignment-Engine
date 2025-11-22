"""Authentication dependencies for FastAPI routes."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from typing import List, Optional
from uuid import UUID
import logging

from src.auth.jwt import verify_token
from src.auth.models import User, TokenData

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    Get current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer credentials

    Returns:
        Authenticated user

    Raises:
        HTTPException: If token is invalid or expired
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials
        payload = verify_token(token)

        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        role: str = payload.get("role")

        if user_id is None or email is None or role is None:
            logger.warning("Invalid token payload", extra={"payload": payload})
            raise credentials_exception

        # In a real implementation, you would fetch the user from database
        # For now, we construct from token claims
        user = User(
            user_id=UUID(user_id),
            email=email,
            role=role,
            is_active=True,
        )

        return user

    except JWTError as e:
        logger.warning(
            "JWT verification failed",
            extra={"error": str(e)},
            exc_info=True
        )
        raise credentials_exception
    except ValueError as e:
        logger.warning(
            "Invalid user ID format",
            extra={"error": str(e)},
            exc_info=True
        )
        raise credentials_exception


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user.

    Args:
        current_user: Current authenticated user

    Returns:
        Active user

    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


def require_role(allowed_roles: List[str]):
    """
    Dependency factory for role-based access control.

    Args:
        allowed_roles: List of allowed roles

    Returns:
        Dependency function

    Example:
        @app.get("/admin", dependencies=[Depends(require_role(["admin"]))])
        async def admin_endpoint():
            ...
    """
    async def role_checker(current_user: User = Depends(get_current_active_user)):
        if current_user.role not in allowed_roles:
            logger.warning(
                "Insufficient permissions",
                extra={
                    "user_id": str(current_user.user_id),
                    "user_role": current_user.role,
                    "required_roles": allowed_roles,
                }
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {allowed_roles}"
            )
        return current_user

    return role_checker


# Optional: Allow bypassing auth for specific scenarios
async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    )
) -> Optional[User]:
    """
    Get current user if authenticated, None otherwise.

    Useful for endpoints that work with or without authentication.

    Args:
        credentials: Optional HTTP Bearer credentials

    Returns:
        User if authenticated, None otherwise
    """
    if credentials is None:
        return None

    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None
