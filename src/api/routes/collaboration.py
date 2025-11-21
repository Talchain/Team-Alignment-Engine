"""Real-time collaboration endpoints for Phase D2."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
import logging
import json
from datetime import datetime

from src.models.portfolio import CollaborationAction, SessionState
from src.services.collaboration_manager import CollaborationManager
from src.storage.cache import get_cache

router = APIRouter(prefix="/api/v1/collaboration", tags=["collaboration"])
logger = logging.getLogger(__name__)


class PresenceUpdate(BaseModel):
    """Request to update user presence."""

    user_id: str
    metadata: Optional[dict] = None


class BroadcastActionRequest(BaseModel):
    """Request to broadcast an action."""

    user_id: str
    action: CollaborationAction


@router.websocket("/ws/{session_id}")
async def collaboration_websocket(
    websocket: WebSocket,
    session_id: UUID,
    user_id: str = Query(..., description="User ID connecting to session"),
):
    """
    WebSocket endpoint for real-time collaboration.

    **Protocol:**
    - Client connects and provides user_id
    - Server broadcasts presence_joined to all participants
    - Client sends heartbeat every 10s to maintain presence
    - Client sends actions (votes, proposals, concerns)
    - Server broadcasts actions to all participants
    - Client disconnects, server broadcasts presence_left

    **Message types from client:**
    ```json
    {
        "type": "heartbeat",
        "timestamp": "2025-01-01T00:00:00Z"
    }
    {
        "type": "action",
        "action_type": "vote_cast",
        "target_id": "option-uuid",
        "data": {"value": "strong"}
    }
    ```

    **Message types to client:**
    ```json
    {
        "event_type": "presence_joined",
        "data": {"user_id": "user123"},
        "timestamp": "2025-01-01T00:00:00Z"
    }
    {
        "event_type": "collaboration_action",
        "data": {
            "user_id": "user123",
            "action_type": "vote_cast",
            "target_id": "option-uuid",
            "data": {"value": "strong"}
        },
        "timestamp": "2025-01-01T00:00:00Z"
    }
    ```

    **Performance:**
    - Target: <100ms broadcast latency p95
    - Support: 50 concurrent users per session
    """
    await websocket.accept()

    redis = await get_cache()
    collaboration_manager = CollaborationManager(redis)

    try:
        # Track initial presence
        await collaboration_manager.track_presence(
            session_id=session_id, user_id=user_id
        )

        logger.info(
            "websocket_connected",
            extra={
                "session_id": str(session_id),
                "user_id": user_id,
            },
        )

        # Send initial session state
        session_state = await collaboration_manager.get_session_state(session_id)
        await websocket.send_json(
            {
                "event_type": "session_state",
                "data": session_state.model_dump(mode="json"),
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        # Subscribe to session events (non-blocking)
        # We'll handle this in a separate task to avoid blocking receive
        import asyncio

        async def listen_to_events():
            """Listen to Redis pub/sub and forward to WebSocket."""
            try:
                async for event in collaboration_manager.subscribe_to_session(
                    session_id
                ):
                    await websocket.send_json(event)
            except WebSocketDisconnect:
                pass
            except Exception as e:
                logger.error(
                    "event_listener_error",
                    extra={
                        "session_id": str(session_id),
                        "user_id": user_id,
                        "error": str(e),
                    },
                    exc_info=True,
                )

        # Start event listener task
        event_task = asyncio.create_task(listen_to_events())

        try:
            # Handle incoming messages
            while True:
                data = await websocket.receive_json()

                message_type = data.get("type")

                if message_type == "heartbeat":
                    # Update presence
                    await collaboration_manager.track_presence(
                        session_id=session_id,
                        user_id=user_id,
                        metadata=data.get("metadata"),
                    )

                elif message_type == "action":
                    # Broadcast action
                    action = CollaborationAction(
                        action_type=data.get("action_type"),
                        target_id=UUID(data["target_id"])
                        if data.get("target_id")
                        else None,
                        data=data.get("data", {}),
                        persist=data.get("persist", True),
                    )

                    await collaboration_manager.broadcast_action(
                        session_id=session_id, action=action, user_id=user_id
                    )

                else:
                    logger.warning(
                        "unknown_message_type",
                        extra={
                            "session_id": str(session_id),
                            "user_id": user_id,
                            "message_type": message_type,
                        },
                    )

        except WebSocketDisconnect:
            logger.info(
                "websocket_disconnected",
                extra={
                    "session_id": str(session_id),
                    "user_id": user_id,
                },
            )
        finally:
            # Cancel event listener
            event_task.cancel()
            try:
                await event_task
            except asyncio.CancelledError:
                pass

    except Exception as e:
        logger.error(
            "websocket_error",
            extra={
                "session_id": str(session_id),
                "user_id": user_id,
                "error": str(e),
            },
            exc_info=True,
        )
    finally:
        # Remove presence
        await collaboration_manager.remove_presence(
            session_id=session_id, user_id=user_id
        )


@router.get("/{session_id}/state", response_model=SessionState)
async def get_session_state(session_id: UUID) -> SessionState:
    """
    Get current session collaboration state.

    Returns active users and recent actions without WebSocket connection.
    Useful for initial page load before establishing WebSocket.

    **Performance:**
    - Target: <500ms response time
    """
    try:
        redis = await get_cache()
        collaboration_manager = CollaborationManager(redis)

        session_state = await collaboration_manager.get_session_state(session_id)

        logger.info(
            "session_state_retrieved",
            extra={
                "session_id": str(session_id),
                "active_users_count": len(session_state.active_users),
                "recent_actions_count": len(session_state.recent_actions),
            },
        )

        return session_state

    except Exception as e:
        logger.error(
            "failed_to_get_session_state",
            extra={
                "session_id": str(session_id),
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve session state",
        )


@router.post("/{session_id}/presence")
async def update_presence(
    session_id: UUID, presence: PresenceUpdate
) -> dict:
    """
    Update user presence (alternative to WebSocket heartbeat).

    Useful for clients that can't maintain WebSocket connections.
    Presence expires after 30 seconds without update.

    **Use case:**
    - Mobile clients with unstable connections
    - Polling-based fallback
    """
    try:
        redis = await get_cache()
        collaboration_manager = CollaborationManager(redis)

        await collaboration_manager.track_presence(
            session_id=session_id,
            user_id=presence.user_id,
            metadata=presence.metadata,
        )

        return {
            "success": True,
            "session_id": str(session_id),
            "user_id": presence.user_id,
        }

    except Exception as e:
        logger.error(
            "failed_to_update_presence",
            extra={
                "session_id": str(session_id),
                "user_id": presence.user_id,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update presence",
        )


@router.post("/{session_id}/broadcast")
async def broadcast_action(
    session_id: UUID, request: BroadcastActionRequest
) -> dict:
    """
    Broadcast a collaboration action (alternative to WebSocket).

    Useful for clients without WebSocket support.
    Action is broadcasted to all connected WebSocket clients.

    **Use case:**
    - REST API fallback
    - Server-side action triggers
    """
    try:
        redis = await get_cache()
        collaboration_manager = CollaborationManager(redis)

        await collaboration_manager.broadcast_action(
            session_id=session_id,
            action=request.action,
            user_id=request.user_id,
        )

        return {
            "success": True,
            "session_id": str(session_id),
            "action_type": request.action.action_type,
        }

    except Exception as e:
        logger.error(
            "failed_to_broadcast_action",
            extra={
                "session_id": str(session_id),
                "user_id": request.user_id,
                "action_type": request.action.action_type,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to broadcast action",
        )


@router.get("/{session_id}/active-users")
async def get_active_users(session_id: UUID) -> dict:
    """
    Get list of currently active users in a session.

    **Performance:**
    - Target: <200ms response time
    """
    try:
        redis = await get_cache()
        collaboration_manager = CollaborationManager(redis)

        active_users = await collaboration_manager.get_active_users(session_id)

        return {
            "session_id": str(session_id),
            "active_users": [user.model_dump(mode="json") for user in active_users],
            "count": len(active_users),
        }

    except Exception as e:
        logger.error(
            "failed_to_get_active_users",
            extra={
                "session_id": str(session_id),
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve active users",
        )
