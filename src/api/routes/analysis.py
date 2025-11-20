"""Analysis endpoints."""

from fastapi import APIRouter, HTTPException, status
from uuid import UUID

from src.models import SessionStatus
from src.services import SessionManager, ProfileExtractor, DisagreementAnalyzer

router = APIRouter(prefix="/api/v1/alignment/sessions", tags=["analysis"])

# Global service instances
session_manager = SessionManager()
profile_extractor = ProfileExtractor()
disagreement_analyzer = DisagreementAnalyzer()


@router.post("/{session_id}/analyze", status_code=status.HTTP_200_OK)
async def generate_analysis(session_id: UUID):
    """
    Generate shared ground and disagreement map.

    Triggered automatically when all profiles collected.
    """
    session = await session_manager.get(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    # Get all profiles
    profiles = await profile_extractor.get_all(session_id)

    if not profiles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No profiles collected yet",
        )

    # Generate shared ground
    shared_ground = await disagreement_analyzer.find_common_ground(
        profiles, session.decision_context
    )
    await session_manager.update_shared_ground(session_id, shared_ground.dict())

    # Generate disagreement map
    disagreement_map = await disagreement_analyzer.map_tensions(
        profiles, session.decision_context
    )
    await session_manager.update_disagreement_map(
        session_id, disagreement_map.dict()
    )

    # Update status to deliberating
    await session_manager.update_status(session_id, SessionStatus.DELIBERATING)

    return {
        "shared_ground": shared_ground.dict(),
        "disagreement_map": disagreement_map.dict(),
    }
