"""Unit tests for CollaborationManager service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime
import json

from src.models.portfolio import CollaborationAction, UserPresence
from src.services.collaboration_manager import CollaborationManager


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis = AsyncMock()
    redis.hset = AsyncMock()
    redis.hdel = AsyncMock()
    redis.hgetall = AsyncMock(return_value={})
    redis.expire = AsyncMock()
    redis.publish = AsyncMock()
    redis.zadd = AsyncMock()
    redis.zrevrange = AsyncMock(return_value=[])
    return redis


@pytest.fixture
def session_id():
    """Sample session ID."""
    return uuid4()


@pytest.fixture
def user_id():
    """Sample user ID."""
    return "test-user-123"


@pytest.fixture
def collaboration_action():
    """Sample collaboration action."""
    return CollaborationAction(
        action_type="vote_cast",
        target_id=uuid4(),
        data={"value": "strong"},
        persist=True,
    )


class TestCollaborationManager:
    """Tests for CollaborationManager service."""

    @pytest.mark.asyncio
    async def test_track_presence(self, mock_redis, session_id, user_id):
        """Test tracking user presence."""
        manager = CollaborationManager(mock_redis)
        metadata = {"cursor_x": 100, "cursor_y": 200}

        await manager.track_presence(session_id, user_id, metadata)

        # Should store presence in Redis
        mock_redis.hset.assert_called_once()
        call_args = mock_redis.hset.call_args
        assert call_args[0][0] == f"presence:{session_id}"
        assert call_args[0][1] == user_id

        # Should set TTL
        mock_redis.expire.assert_called_once()

        # Should publish presence event
        mock_redis.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_presence(self, mock_redis, session_id, user_id):
        """Test removing user presence."""
        manager = CollaborationManager(mock_redis)

        await manager.remove_presence(session_id, user_id)

        # Should delete presence from Redis
        mock_redis.hdel.assert_called_once_with(f"presence:{session_id}", user_id)

        # Should publish presence event
        mock_redis.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_active_users(self, mock_redis, session_id):
        """Test getting active users."""
        # Mock presence data
        user1_presence = UserPresence(
            user_id="user1",
            session_id=session_id,
            joined_at=datetime.utcnow(),
            last_seen=datetime.utcnow(),
            metadata={},
        )
        user2_presence = UserPresence(
            user_id="user2",
            session_id=session_id,
            joined_at=datetime.utcnow(),
            last_seen=datetime.utcnow(),
            metadata={"status": "typing"},
        )

        mock_redis.hgetall = AsyncMock(
            return_value={
                b"user1": json.dumps(user1_presence.model_dump(mode="json")),
                b"user2": json.dumps(user2_presence.model_dump(mode="json")),
            }
        )

        manager = CollaborationManager(mock_redis)
        active_users = await manager.get_active_users(session_id)

        assert len(active_users) == 2
        assert any(u.user_id == "user1" for u in active_users)
        assert any(u.user_id == "user2" for u in active_users)

    @pytest.mark.asyncio
    async def test_get_active_users_empty(self, mock_redis, session_id):
        """Test getting active users when none present."""
        mock_redis.hgetall = AsyncMock(return_value={})

        manager = CollaborationManager(mock_redis)
        active_users = await manager.get_active_users(session_id)

        assert len(active_users) == 0

    @pytest.mark.asyncio
    async def test_broadcast_action(
        self, mock_redis, session_id, user_id, collaboration_action
    ):
        """Test broadcasting a collaboration action."""
        manager = CollaborationManager(mock_redis)

        await manager.broadcast_action(session_id, collaboration_action, user_id)

        # Should store action (because persist=True)
        mock_redis.zadd.assert_called_once()

        # Should publish action event
        assert mock_redis.publish.call_count >= 1

    @pytest.mark.asyncio
    async def test_broadcast_action_no_persist(self, mock_redis, session_id, user_id):
        """Test broadcasting action with persist=False."""
        action = CollaborationAction(
            action_type="typing_start",
            target_id=None,
            data={},
            persist=False,
        )

        manager = CollaborationManager(mock_redis)

        await manager.broadcast_action(session_id, action, user_id)

        # Should not store action (persist=False)
        mock_redis.zadd.assert_not_called()

        # Should still publish event
        mock_redis.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_session_state(self, mock_redis, session_id):
        """Test getting session state."""
        # Mock active users
        mock_redis.hgetall = AsyncMock(return_value={})

        # Mock recent actions
        mock_redis.zrevrange = AsyncMock(return_value=[])

        manager = CollaborationManager(mock_redis)
        state = await manager.get_session_state(session_id)

        assert state.session_id == session_id
        assert isinstance(state.active_users, list)
        assert isinstance(state.recent_actions, list)
        assert isinstance(state.last_activity, datetime)

    @pytest.mark.asyncio
    async def test_get_session_state_with_data(self, mock_redis, session_id):
        """Test getting session state with data."""
        # Mock active user
        user_presence = UserPresence(
            user_id="user1",
            session_id=session_id,
            joined_at=datetime.utcnow(),
            last_seen=datetime.utcnow(),
            metadata={},
        )
        mock_redis.hgetall = AsyncMock(
            return_value={
                b"user1": json.dumps(user_presence.model_dump(mode="json")),
            }
        )

        # Mock recent action
        action_data = {
            "user_id": "user1",
            "action_type": "vote_cast",
            "target_id": str(uuid4()),
            "data": {"value": "strong"},
            "timestamp": datetime.utcnow().isoformat(),
        }
        mock_redis.zrevrange = AsyncMock(
            return_value=[json.dumps(action_data).encode()]
        )

        manager = CollaborationManager(mock_redis)
        state = await manager.get_session_state(session_id)

        assert len(state.active_users) == 1
        assert len(state.recent_actions) == 1

    @pytest.mark.asyncio
    async def test_cleanup_stale_presence(self, mock_redis, session_id):
        """Test cleanup of stale presence records."""
        # Mock stale presence (last_seen 2 minutes ago)
        from datetime import timedelta

        stale_time = datetime.utcnow() - timedelta(minutes=2)
        stale_presence = UserPresence(
            user_id="stale_user",
            session_id=session_id,
            joined_at=stale_time,
            last_seen=stale_time,
            metadata={},
        )

        mock_redis.hgetall = AsyncMock(
            return_value={
                b"stale_user": json.dumps(stale_presence.model_dump(mode="json")),
            }
        )

        manager = CollaborationManager(mock_redis)

        # Cleanup with 60 second threshold
        removed = await manager.cleanup_stale_presence(session_id, threshold_seconds=60)

        assert removed == 1
        mock_redis.hdel.assert_called_once()
        mock_redis.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_stale_presence_no_stale(self, mock_redis, session_id):
        """Test cleanup with no stale records."""
        # Mock recent presence
        recent_presence = UserPresence(
            user_id="active_user",
            session_id=session_id,
            joined_at=datetime.utcnow(),
            last_seen=datetime.utcnow(),
            metadata={},
        )

        mock_redis.hgetall = AsyncMock(
            return_value={
                b"active_user": json.dumps(recent_presence.model_dump(mode="json")),
            }
        )

        manager = CollaborationManager(mock_redis)

        removed = await manager.cleanup_stale_presence(session_id, threshold_seconds=60)

        assert removed == 0
        mock_redis.hdel.assert_not_called()

    @pytest.mark.asyncio
    async def test_publish_event(self, mock_redis, session_id):
        """Test publishing event to Redis channel."""
        manager = CollaborationManager(mock_redis)

        await manager._publish_event(
            session_id=session_id,
            event_type="test_event",
            data={"key": "value"},
        )

        # Should publish to session channel
        mock_redis.publish.assert_called_once()
        call_args = mock_redis.publish.call_args
        assert call_args[0][0] == f"session:{session_id}"

        # Message should be JSON
        message = json.loads(call_args[0][1])
        assert message["event_type"] == "test_event"
        assert message["data"]["key"] == "value"

    @pytest.mark.asyncio
    async def test_store_action(
        self, mock_redis, session_id, user_id, collaboration_action
    ):
        """Test storing action in Redis."""
        manager = CollaborationManager(mock_redis)

        await manager._store_action(session_id, user_id, collaboration_action)

        # Should add to sorted set
        mock_redis.zadd.assert_called_once()
        call_args = mock_redis.zadd.call_args
        assert call_args[0][0] == f"actions:{session_id}"

        # Should set TTL
        mock_redis.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_recent_actions(self, mock_redis, session_id):
        """Test getting recent actions."""
        # Mock action data
        action1 = {
            "user_id": "user1",
            "action_type": "vote_cast",
            "target_id": str(uuid4()),
            "data": {"value": "strong"},
            "timestamp": datetime.utcnow().isoformat(),
        }
        action2 = {
            "user_id": "user2",
            "action_type": "option_proposed",
            "target_id": str(uuid4()),
            "data": {"title": "New option"},
            "timestamp": datetime.utcnow().isoformat(),
        }

        mock_redis.zrevrange = AsyncMock(
            return_value=[
                json.dumps(action1).encode(),
                json.dumps(action2).encode(),
            ]
        )

        manager = CollaborationManager(mock_redis)
        actions = await manager._get_recent_actions(session_id, limit=10)

        assert len(actions) == 2
        assert actions[0]["user_id"] == "user1"
        assert actions[1]["user_id"] == "user2"

    @pytest.mark.asyncio
    async def test_get_recent_actions_with_limit(self, mock_redis, session_id):
        """Test getting recent actions with limit."""
        manager = CollaborationManager(mock_redis)

        await manager._get_recent_actions(session_id, limit=5)

        # Should query with limit
        mock_redis.zrevrange.assert_called_once_with(f"actions:{session_id}", 0, 4)

    @pytest.mark.asyncio
    async def test_track_presence_error_handling(self, session_id, user_id):
        """Test presence tracking error handling."""
        # Mock Redis to raise exception
        mock_redis = AsyncMock()
        mock_redis.hset = AsyncMock(side_effect=Exception("Redis error"))

        manager = CollaborationManager(mock_redis)

        # Should not raise exception
        await manager.track_presence(session_id, user_id)

    @pytest.mark.asyncio
    async def test_get_active_users_invalid_json(self, mock_redis, session_id):
        """Test getting active users with invalid JSON data."""
        mock_redis.hgetall = AsyncMock(
            return_value={
                b"user1": b"invalid json data",
            }
        )

        manager = CollaborationManager(mock_redis)
        active_users = await manager.get_active_users(session_id)

        # Should handle gracefully and return empty list
        assert len(active_users) == 0
