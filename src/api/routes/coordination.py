"""Cross-team coordination endpoints for Phase D6."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.portfolio import (
    CoordinationGroup,
    ConflictDetection,
    CoordinationView,
)
from src.services.coordination_manager import CrossTeamCoordinator
from src.storage.database import get_db

router = APIRouter(prefix="/api/v1/coordination", tags=["coordination"])


class CreateGroupRequest(BaseModel):
    """Request to create coordination group."""

    name: str
    description: str
    session_ids: List[UUID]
    created_by: str


class ResolveConflictRequest(BaseModel):
    """Request to resolve conflict."""

    resolution: str


@router.post("/groups", response_model=CoordinationGroup, status_code=status.HTTP_201_CREATED)
async def create_coordination_group(
    request: CreateGroupRequest,
    db: AsyncSession = Depends(get_db),
) -> CoordinationGroup:
    """
    Create a coordination group linking multiple team decisions.

    **What it does:**
    - Links related decisions across teams
    - Establishes coordination checkpoints
    - Enables cross-team visibility

    **Use cases:**
    - Product + Engineering alignment
    - Sales + Marketing coordination
    - Cross-functional initiatives

    **Example:**
    ```json
    {
        "name": "Q1 Product Launch",
        "description": "Coordinating pricing, marketing, and rollout decisions",
        "session_ids": ["session-A", "session-B", "session-C"],
        "created_by": "user-123"
    }
    ```
    """
    try:
        coordinator = CrossTeamCoordinator(db)

        group = await coordinator.create_coordination_group(
            name=request.name,
            description=request.description,
            session_ids=request.session_ids,
            created_by=request.created_by,
        )

        return group

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create coordination group: {str(e)}",
        )


@router.post("/detect-conflicts")
async def detect_conflicts(
    session_ids: List[UUID],
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Detect conflicts between decisions.

    **Conflict types detected:**
    - **Temporal**: Overlapping timelines causing resource strain
    - **Resource**: Same stakeholders overloaded across decisions
    - **Dependency**: Circular or excessive dependency chains
    - **Scope**: Overlapping decision boundaries

    **Severity levels:**
    - **high**: Requires immediate attention
    - **medium**: Should be addressed soon
    - **low**: Monitor for future impact

    **Example response:**
    ```json
    {
        "session_ids": ["session-A", "session-B", "session-C"],
        "conflicts": [
            {
                "conflict_id": "conflict-123",
                "conflict_type": "resource",
                "session_ids": ["session-A", "session-B"],
                "severity": "high",
                "description": "Key stakeholder involved in 3 simultaneous decisions",
                "resolution_suggestions": [
                    "Stagger decision timelines",
                    "Delegate to alternate stakeholders"
                ]
            }
        ],
        "total_conflicts": 1
    }
    ```

    **Performance:**
    - Target: <1s for 10 decisions
    """
    try:
        coordinator = CrossTeamCoordinator(db)

        conflicts = await coordinator.detect_conflicts(session_ids)

        return {
            "session_ids": [str(sid) for sid in session_ids],
            "conflicts": [c.model_dump(mode="json") for c in conflicts],
            "total_conflicts": len(conflicts),
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to detect conflicts: {str(e)}",
        )


@router.get("/view", response_model=CoordinationView)
async def get_coordination_view(
    organization_id: UUID = Query(..., description="Organization ID"),
    team_ids: Optional[List[UUID]] = Query(None, description="Filter by teams"),
    db: AsyncSession = Depends(get_db),
) -> CoordinationView:
    """
    Get cross-team coordination view.

    **What it provides:**
    - All active decisions across teams
    - Detected conflicts requiring resolution
    - Existing coordination groups
    - Coordination health status

    **Use cases:**
    - Executive dashboard: "Where do teams need coordination?"
    - PMO oversight: "What conflicts exist between initiatives?"
    - Resource planning: "Which stakeholders are overloaded?"

    **Performance:**
    - Target: <2s for 50 active decisions
    - Cached for 5 minutes

    **Example response:**
    ```json
    {
        "organization_id": "org-123",
        "active_decisions": ["session-A", "session-B", "session-C"],
        "conflicts": [
            {
                "conflict_type": "temporal",
                "severity": "medium",
                "session_ids": ["session-A", "session-B"],
                "description": "2 decisions active simultaneously"
            }
        ],
        "coordination_groups": [
            {
                "group_id": "group-1",
                "name": "Q1 Launch",
                "session_ids": ["session-A", "session-B"]
            }
        ],
        "coordination_needed": true
    }
    ```
    """
    try:
        coordinator = CrossTeamCoordinator(db)

        view = await coordinator.get_coordination_view(
            organization_id=organization_id,
            team_ids=team_ids,
        )

        return view

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get coordination view: {str(e)}",
        )


@router.post("/conflicts/{conflict_id}/resolve")
async def resolve_conflict(
    conflict_id: UUID,
    request: ResolveConflictRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Mark a conflict as resolved.

    **What it does:**
    - Records conflict resolution
    - Removes from active conflict list
    - Maintains audit trail

    **Use cases:**
    - After implementing resolution suggestions
    - When conflict naturally resolved
    - For documentation and learning
    """
    try:
        coordinator = CrossTeamCoordinator(db)

        await coordinator.resolve_conflict(
            conflict_id=conflict_id,
            resolution=request.resolution,
        )

        return {
            "success": True,
            "conflict_id": str(conflict_id),
            "resolution": request.resolution,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve conflict: {str(e)}",
        )
