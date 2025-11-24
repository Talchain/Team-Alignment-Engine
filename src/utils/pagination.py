"""Pagination utilities for API endpoints.

Provides consistent pagination patterns across all API routes.
"""

from typing import TypeVar, Generic, List
from pydantic import BaseModel, Field
from fastapi import Query


T = TypeVar("T")


class PaginationParams(BaseModel):
    """Standard pagination parameters for API endpoints."""

    limit: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of items to return (1-1000)"
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Number of items to skip before returning results"
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated response wrapper.

    Example:
        {
            "items": [...],
            "total": 150,
            "limit": 100,
            "offset": 0,
            "has_more": true
        }
    """

    items: List[T] = Field(description="List of items in this page")
    total: int = Field(description="Total number of items available")
    limit: int = Field(description="Maximum items per page")
    offset: int = Field(description="Number of items skipped")
    has_more: bool = Field(description="Whether more items are available")


def create_pagination_params(
    limit: int = Query(100, ge=1, le=1000, description="Max items per page"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
) -> PaginationParams:
    """
    Dependency for pagination parameters.

    Usage in FastAPI routes:
        @router.get("/items")
        async def get_items(
            pagination: PaginationParams = Depends(create_pagination_params)
        ):
            ...
    """
    return PaginationParams(limit=limit, offset=offset)


def paginate(
    items: List[T],
    total: int,
    params: PaginationParams,
) -> PaginatedResponse[T]:
    """
    Create paginated response from list of items.

    Args:
        items: List of items for current page
        total: Total count of all items (before pagination)
        params: Pagination parameters

    Returns:
        Paginated response with metadata

    Example:
        items = await repo.get_items(limit=params.limit, offset=params.offset)
        total = await repo.count_items()
        return paginate(items, total, params)
    """
    has_more = (params.offset + len(items)) < total

    return PaginatedResponse(
        items=items,
        total=total,
        limit=params.limit,
        offset=params.offset,
        has_more=has_more,
    )
