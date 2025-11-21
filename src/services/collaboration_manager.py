"""Collaboration manager service for Phase D2."""

import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Set
from uuid import UUID
from collections import defaultdict

from redis.asyncio import Redis

from src.models.portfolio import (
    UserPresence,
    CollaborationAction,
    SessionState,
)

logger = logging.getLogger(__name__)


class CollaborationManager:
    """Manage real-time collaboration for sessions."""

    def __init__(self, redis: Redis):
        """
        Initialize collaboration manager.

        Args:
            redis: Redis client for pub/sub and presence tracking
        """
        self.redis = redis
        self.presence_ttl = 30  # Seconds before presence expires
        self.action_history_ttl = 3600  # Keep action history for 1 hour

    async def track_presence(
        self, session_id: UUID, user_id: str, metadata: Optional[Dict] = None
    ) -> None:
        """
        Track user presence in a session.

        Args:
            session_id: Session ID
            user_id: User ID
            metadata: Optional metadata (cursor position, etc.)
        """
        try:
            key = f"presence:{session_id}"
            presence = UserPresence(
                user_id=user_id,
                session_id=session_id,
                joined_at=datetime.utcnow(),
                last_seen=datetime.utcnow(),
                metadata=metadata or {},
            )

            # Store presence with TTL
            await self.redis.hset(
                key, user_id, json.dumps(presence.model_dump(mode="json"))
            )
            await self.redis.expire(key, self.presence_ttl)

            # Publish presence event
            await self._publish_event(
                session_id=session_id,
                event_type="presence_joined",
                data={"user_id": user_id, "metadata": metadata},
            )

            logger.debug(
                "user_presence_tracked",
                extra={
                    "session_id": str(session_id),
                    "user_id": user_id,
                },
            )

        except Exception as e:
            logger.error(
                "failed_to_track_presence",
                extra={
                    "session_id": str(session_id),
                    "user_id": user_id,
                    "error": str(e),
                },
                exc_info=True,
            )

    async def remove_presence(self, session_id: UUID, user_id: str) -> None:
        """
        Remove user presence from a session.

        Args:
            session_id: Session ID
            user_id: User ID
        """
        try:
            key = f"presence:{session_id}"
            await self.redis.hdel(key, user_id)

            # Publish presence event
            await self._publish_event(
                session_id=session_id,
                event_type="presence_left",
                data={"user_id": user_id},
            )

            logger.debug(
                "user_presence_removed",
                extra={
                    "session_id": str(session_id),
                    "user_id": user_id,
                },
            )

        except Exception as e:
            logger.error(
                "failed_to_remove_presence",
                extra={
                    "session_id": str(session_id),
                    "user_id": user_id,
                    "error": str(e),
                },
                exc_info=True,
            )

    async def get_active_users(self, session_id: UUID) -> List[UserPresence]:
        """
        Get list of active users in a session.

        Args:
            session_id: Session ID

        Returns:
            List of active user presences
        """
        try:
            key = f"presence:{session_id}"
            presences_data = await self.redis.hgetall(key)

            presences = []
            for user_id, data in presences_data.items():
                try:
                    presence_dict = json.loads(data)
                    presences.append(UserPresence(**presence_dict))
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(
                        "invalid_presence_data",
                        extra={
                            "session_id": str(session_id),
                            "user_id": user_id.decode() if isinstance(user_id, bytes) else user_id,
                            "error": str(e),
                        },
                    )

            return presences

        except Exception as e:
            logger.error(
                "failed_to_get_active_users",
                extra={
                    "session_id": str(session_id),
                    "error": str(e),
                },
                exc_info=True,
            )
            return []

    async def broadcast_action(
        self,
        session_id: UUID,
        action: CollaborationAction,
        user_id: str,
    ) -> None:
        """
        Broadcast a collaboration action to all session participants.

        Args:
            session_id: Session ID
            action: Collaboration action
            user_id: User who performed the action
        """
        try:
            # Store action in history if persist is True
            if action.persist:
                await self._store_action(session_id, user_id, action)

            # Publish action event
            await self._publish_event(
                session_id=session_id,
                event_type="collaboration_action",
                data={
                    "user_id": user_id,
                    "action_type": action.action_type,
                    "target_id": str(action.target_id) if action.target_id else None,
                    "data": action.data,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

            logger.debug(
                "action_broadcasted",
                extra={
                    "session_id": str(session_id),
                    "user_id": user_id,
                    "action_type": action.action_type,
                },
            )

        except Exception as e:
            logger.error(
                "failed_to_broadcast_action",
                extra={
                    "session_id": str(session_id),
                    "user_id": user_id,
                    "action_type": action.action_type,
                    "error": str(e),
                },
                exc_info=True,
            )

    async def get_session_state(self, session_id: UUID) -> SessionState:
        """
        Get current session state (presence + recent actions).

        Args:
            session_id: Session ID

        Returns:
            Current session state
        """
        try:
            # Get active users
            active_users = await self.get_active_users(session_id)

            # Get recent actions
            recent_actions = await self._get_recent_actions(session_id, limit=50)

            return SessionState(
                session_id=session_id,
                active_users=active_users,
                recent_actions=recent_actions,
                last_activity=datetime.utcnow(),
            )

        except Exception as e:
            logger.error(
                "failed_to_get_session_state",
                extra={
                    "session_id": str(session_id),
                    "error": str(e),
                },
                exc_info=True,
            )
            # Return empty state on error
            return SessionState(
                session_id=session_id,
                active_users=[],
                recent_actions=[],
                last_activity=datetime.utcnow(),
            )

    async def _publish_event(
        self, session_id: UUID, event_type: str, data: Dict
    ) -> None:
        """
        Publish event to Redis pub/sub channel.

        Args:
            session_id: Session ID
            event_type: Type of event
            data: Event data
        """
        channel = f"session:{session_id}"
        message = {
            "event_type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }

        await self.redis.publish(channel, json.dumps(message))

    async def _store_action(
        self, session_id: UUID, user_id: str, action: CollaborationAction
    ) -> None:
        """
        Store action in Redis for history.

        Args:
            session_id: Session ID
            user_id: User ID
            action: Collaboration action
        """
        key = f"actions:{session_id}"
        action_data = {
            "user_id": user_id,
            "action_type": action.action_type,
            "target_id": str(action.target_id) if action.target_id else None,
            "data": action.data,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Add to sorted set with timestamp as score
        score = datetime.utcnow().timestamp()
        await self.redis.zadd(key, {json.dumps(action_data): score})

        # Set TTL on action history
        await self.redis.expire(key, self.action_history_ttl)

    async def _get_recent_actions(
        self, session_id: UUID, limit: int = 50
    ) -> List[Dict]:
        """
        Get recent actions from session history.

        Args:
            session_id: Session ID
            limit: Maximum number of actions to retrieve

        Returns:
            List of recent actions
        """
        key = f"actions:{session_id}"

        # Get most recent actions (highest scores)
        actions_data = await self.redis.zrevrange(key, 0, limit - 1)

        actions = []
        for data in actions_data:
            try:
                if isinstance(data, bytes):
                    data = data.decode()
                action_dict = json.loads(data)
                actions.append(action_dict)
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(
                    "invalid_action_data",
                    extra={
                        "session_id": str(session_id),
                        "error": str(e),
                    },
                )

        return actions

    async def subscribe_to_session(self, session_id: UUID):
        """
        Subscribe to session events via Redis pub/sub.

        Args:
            session_id: Session ID

        Yields:
            Event messages from the session channel
        """
        channel = f"session:{session_id}"
        pubsub = self.redis.pubsub()

        try:
            await pubsub.subscribe(channel)
            logger.info(
                "subscribed_to_session",
                extra={"session_id": str(session_id)},
            )

            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        yield data
                    except json.JSONDecodeError as e:
                        logger.warning(
                            "invalid_pubsub_message",
                            extra={
                                "session_id": str(session_id),
                                "error": str(e),
                            },
                        )

        except Exception as e:
            logger.error(
                "pubsub_error",
                extra={
                    "session_id": str(session_id),
                    "error": str(e),
                },
                exc_info=True,
            )
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
            logger.info(
                "unsubscribed_from_session",
                extra={"session_id": str(session_id)},
            )

    async def cleanup_stale_presence(self, session_id: UUID, threshold_seconds: int = 60) -> int:
        """
        Clean up stale presence records (users who haven't sent heartbeat).

        Args:
            session_id: Session ID
            threshold_seconds: Seconds of inactivity before considering stale

        Returns:
            Number of stale presences removed
        """
        try:
            key = f"presence:{session_id}"
            presences_data = await self.redis.hgetall(key)

            now = datetime.utcnow()
            stale_users = []

            for user_id, data in presences_data.items():
                try:
                    presence_dict = json.loads(data)
                    last_seen = datetime.fromisoformat(presence_dict["last_seen"])

                    if (now - last_seen).total_seconds() > threshold_seconds:
                        stale_users.append(user_id)
                except (json.JSONDecodeError, ValueError, KeyError) as e:
                    logger.warning(
                        "invalid_presence_during_cleanup",
                        extra={
                            "session_id": str(session_id),
                            "error": str(e),
                        },
                    )
                    stale_users.append(user_id)

            # Remove stale presences
            if stale_users:
                await self.redis.hdel(key, *stale_users)

                # Publish leave events
                for user_id in stale_users:
                    await self._publish_event(
                        session_id=session_id,
                        event_type="presence_left",
                        data={
                            "user_id": user_id.decode() if isinstance(user_id, bytes) else user_id,
                            "reason": "stale",
                        },
                    )

            logger.debug(
                "cleaned_stale_presence",
                extra={
                    "session_id": str(session_id),
                    "count": len(stale_users),
                },
            )

            return len(stale_users)

        except Exception as e:
            logger.error(
                "failed_to_cleanup_stale_presence",
                extra={
                    "session_id": str(session_id),
                    "error": str(e),
                },
                exc_info=True,
            )
            return 0
