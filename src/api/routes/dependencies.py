"""Decision dependency endpoints for Phase D3."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.portfolio import (
    DecisionDependency,
    DependencyGraph,
)
from src.services.dependency_manager import (
    DecisionDependencyManager,
    CircularDependencyError,
)
from src.storage.database import get_db

router = APIRouter(prefix="/api/v1/dependencies", tags=["dependencies"])


class AddDependencyRequest(BaseModel):
    """Request to add a dependency."""

    source_session_id: UUID
    target_session_id: UUID
    dependency_type: str
    description: Optional[str] = None
    created_by: str


class DependencyResponse(BaseModel):
    """Response for dependency operations."""

    dependency: DecisionDependency


@router.post("", response_model=DependencyResponse, status_code=status.HTTP_201_CREATED)
async def add_dependency(
    request: AddDependencyRequest,
    db: AsyncSession = Depends(get_db),
) -> DependencyResponse:
    """
    Add a dependency between two decisions.

    **What it does:**
    - Creates a dependency link from source to target decision
    - Validates that dependency doesn't create circular references
    - Tracks dependency type and description

    **Dependency types:**
    - `blocks`: Source decision is blocked by target
    - `related_to`: Source decision is related to target
    - `supersedes`: Source decision supersedes target
    - `depends_on`: Source decision depends on outcome of target

    **Circular dependency detection:**
    - Automatically detects and prevents cycles
    - Returns 409 Conflict if cycle would be created

    **Example:**
    ```json
    {
        "source_session_id": "session-A",
        "target_session_id": "session-B",
        "dependency_type": "blocks",
        "description": "Pricing depends on feature scope",
        "created_by": "user-123"
    }
    ```

    **Returns:**
    - 201: Dependency created
    - 409: Circular dependency detected
    - 404: Session not found
    """
    try:
        manager = DecisionDependencyManager(db)

        dependency = await manager.add_dependency(
            source_session_id=request.source_session_id,
            target_session_id=request.target_session_id,
            dependency_type=request.dependency_type,
            description=request.description,
            created_by=request.created_by,
        )

        return DependencyResponse(dependency=dependency)

    except CircularDependencyError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add dependency: {str(e)}",
        )


@router.delete("/{dependency_id}")
async def remove_dependency(
    dependency_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Remove a dependency.

    **Use cases:**
    - Dependency no longer relevant
    - Correcting mistaken dependency link
    """
    try:
        manager = DecisionDependencyManager(db)
        await manager.remove_dependency(dependency_id)

        return {
            "success": True,
            "dependency_id": str(dependency_id),
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove dependency: {str(e)}",
        )


@router.post("/{dependency_id}/resolve")
async def resolve_dependency(
    dependency_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Mark a dependency as resolved.

    **What it means:**
    - Target decision has been completed
    - Source decision is no longer blocked
    - Dependency remains in history for audit

    **Use case:**
    - Automatically called when target decision completes
    - Manually called to unblock dependent decision
    """
    try:
        manager = DecisionDependencyManager(db)
        await manager.resolve_dependency(dependency_id)

        return {
            "success": True,
            "dependency_id": str(dependency_id),
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve dependency: {str(e)}",
        )


@router.get("/session/{session_id}")
async def get_session_dependencies(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get all dependencies for a session.

    **Returns:**
    - Incoming dependencies (this session depends on others)
    - Outgoing dependencies (others depend on this session)
    """
    try:
        manager = DecisionDependencyManager(db)
        dependencies = await manager.get_dependencies_for_session(session_id)

        # Separate incoming and outgoing
        incoming = [d for d in dependencies if d.source_session_id == session_id]
        outgoing = [d for d in dependencies if d.target_session_id == session_id]

        return {
            "session_id": str(session_id),
            "incoming": [d.model_dump(mode="json") for d in incoming],
            "outgoing": [d.model_dump(mode="json") for d in outgoing],
            "total": len(dependencies),
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dependencies: {str(e)}",
        )


@router.get("/session/{session_id}/blocking")
async def get_blocking_sessions(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get sessions that are blocking this session.

    **What it returns:**
    - List of sessions this decision depends on
    - Only unresolved dependencies
    - Ordered by priority

    **Use case:**
    - Determine why a decision is blocked
    - Find what needs to complete first
    """
    try:
        manager = DecisionDependencyManager(db)
        blocking = await manager.get_blocking_sessions(session_id)

        return {
            "session_id": str(session_id),
            "blocking_sessions": [str(s) for s in blocking],
            "count": len(blocking),
            "is_blocked": len(blocking) > 0,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get blocking sessions: {str(e)}",
        )


@router.get("/session/{session_id}/dependents")
async def get_dependent_sessions(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get sessions that depend on this session.

    **What it returns:**
    - List of sessions waiting for this decision
    - Shows impact of completing/changing this decision

    **Use case:**
    - Understand downstream impact
    - Prioritize high-impact decisions
    """
    try:
        manager = DecisionDependencyManager(db)
        dependents = await manager.get_dependent_sessions(session_id)

        return {
            "session_id": str(session_id),
            "dependent_sessions": [str(s) for s in dependents],
            "count": len(dependents),
            "has_dependents": len(dependents) > 0,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dependent sessions: {str(e)}",
        )


@router.get("/graph", response_model=DependencyGraph)
async def get_dependency_graph(
    organization_id: UUID = Query(..., description="Organization ID"),
    include_resolved: bool = Query(
        False, description="Include resolved dependencies"
    ),
    db: AsyncSession = Depends(get_db),
) -> DependencyGraph:
    """
    Get dependency graph for organization.

    **What it provides:**
    - Complete dependency graph visualization
    - Graph metrics (depth, bottlenecks, etc.)
    - Critical paths (longest dependency chains)
    - Bottleneck nodes (high centrality)

    **Use cases:**
    - Executive dashboard showing decision dependencies
    - Identifying decision bottlenecks
    - Understanding decision flow complexity
    - Planning resource allocation

    **Performance:**
    - Target: <2s for 100 decisions
    - Cached for 5 minutes

    **Graph metrics:**
    - `total_nodes`: Number of decisions
    - `total_edges`: Number of dependencies
    - `root_nodes`: Decisions with no dependencies
    - `leaf_nodes`: Decisions with no dependents
    - `max_depth`: Longest dependency chain
    - `blocked_nodes`: Decisions blocked by dependencies

    **Critical paths:**
    - Longest chains from root to leaf
    - Identifies most complex dependency sequences
    - Used for timeline estimation

    **Bottleneck nodes:**
    - Decisions with many dependents
    - High betweenness centrality
    - Completion unblocks many other decisions

    **Example response:**
    ```json
    {
        "organization_id": "org-123",
        "nodes": [
            {
                "session_id": "session-A",
                "decision_topic": "Pricing Strategy",
                "status": "complete",
                "dependencies_incoming": [],
                "dependencies_outgoing": ["session-B", "session-C"],
                "is_blocked": false,
                "depth": 0
            }
        ],
        "metrics": {
            "total_nodes": 10,
            "total_edges": 15,
            "max_depth": 3,
            "blocked_nodes": 2
        },
        "critical_paths": [
            ["session-A", "session-B", "session-D", "session-F"]
        ],
        "bottleneck_nodes": ["session-B"]
    }
    ```
    """
    try:
        manager = DecisionDependencyManager(db)

        graph = await manager.build_dependency_graph(
            organization_id=organization_id,
            include_resolved=include_resolved,
        )

        return graph

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build dependency graph: {str(e)}",
        )
