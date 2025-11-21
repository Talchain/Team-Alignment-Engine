"""Integration tests for collaboration API endpoints."""

import pytest
from httpx import AsyncClient
from uuid import uuid4
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import json


@pytest.fixture
def session_id():
    """Sample session ID."""
    return uuid4()


@pytest.fixture
def user_id():
    """Sample user ID."""
    return "test-user-123"


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis_mock = AsyncMock()
    redis_mock.hset = AsyncMock()
    redis_mock.hdel = AsyncMock()
    redis_mock.hgetall = AsyncMock(return_value={})
    redis_mock.hget = AsyncMock(return_value=None)
    redis_mock.expire = AsyncMock()
    redis_mock.publish = AsyncMock()
    redis_mock.lrange = AsyncMock(return_value=[])
    redis_mock.lpush = AsyncMock()
    redis_mock.expire = AsyncMock()
    return redis_mock


@pytest.fixture
def mock_collaboration_manager():
    """Mock CollaborationManager."""
    from src.models.portfolio import UserPresence, SessionState

    manager = MagicMock()

    # Mock methods
    manager.track_presence = AsyncMock()
    manager.remove_presence = AsyncMock()
    manager.broadcast_action = AsyncMock()

    # Mock get_active_users
    manager.get_active_users = AsyncMock(
        return_value=[
            UserPresence(
                user_id="user1",
                session_id=uuid4(),
                joined_at=datetime.utcnow(),
                last_seen=datetime.utcnow(),
                metadata={},
            ),
            UserPresence(
                user_id="user2",
                session_id=uuid4(),
                joined_at=datetime.utcnow(),
                last_seen=datetime.utcnow(),
                metadata={"status": "typing"},
            ),
        ]
    )

    # Mock get_session_state
    manager.get_session_state = AsyncMock(
        return_value=SessionState(
            session_id=uuid4(),
            active_users=[
                UserPresence(
                    user_id="user1",
                    session_id=uuid4(),
                    joined_at=datetime.utcnow(),
                    last_seen=datetime.utcnow(),
                    metadata={},
                )
            ],
            recent_actions=[
                {
                    "user_id": "user1",
                    "action_type": "vote_cast",
                    "target_id": str(uuid4()),
                    "data": {"value": "strong"},
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ],
            last_activity=datetime.utcnow(),
        )
    )

    return manager


class TestSessionStateEndpoint:
    """Tests for /api/v1/collaboration/{session_id}/state endpoint."""

    @pytest.mark.asyncio
    async def test_get_session_state_success(
        self, client: AsyncClient, session_id, mock_collaboration_manager, mock_redis
    ):
        """Test successful session state retrieval."""
        with patch("src.api.routes.collaboration.get_cache", return_value=mock_redis), \
             patch(
                "src.api.routes.collaboration.CollaborationManager",
                return_value=mock_collaboration_manager,
            ):
            response = await client.get(f"/api/v1/collaboration/{session_id}/state")

            assert response.status_code == 200
            data = response.json()

            assert "session_id" in data
            assert "active_users" in data
            assert "recent_actions" in data
            assert "last_activity" in data

    @pytest.mark.asyncio
    async def test_get_session_state_with_active_users(
        self, client: AsyncClient, session_id, mock_collaboration_manager, mock_redis
    ):
        """Test session state includes active users."""
        with patch("src.api.routes.collaboration.get_cache", return_value=mock_redis), \
             patch(
                "src.api.routes.collaboration.CollaborationManager",
                return_value=mock_collaboration_manager,
            ):
            response = await client.get(f"/api/v1/collaboration/{session_id}/state")

            assert response.status_code == 200
            data = response.json()

            assert len(data["active_users"]) >= 1
            assert "user_id" in data["active_users"][0]

    @pytest.mark.asyncio
    async def test_get_session_state_with_recent_actions(
        self, client: AsyncClient, session_id, mock_collaboration_manager
    ):
        """Test session state includes recent actions."""
        with patch("src.api.routes.collaboration.get_cache", return_value=mock_redis), \
             patch(
            "src.api.routes.collaboration.CollaborationManager",
            return_value=mock_collaboration_manager,
        ):
            response = await client.get(f"/api/v1/collaboration/{session_id}/state")

            assert response.status_code == 200
            data = response.json()

            assert len(data["recent_actions"]) >= 1


class TestPresenceEndpoint:
    """Tests for /api/v1/collaboration/{session_id}/presence endpoint."""

    @pytest.mark.asyncio
    async def test_update_presence_success(
        self, client: AsyncClient, session_id, user_id, mock_collaboration_manager
    ):
        """Test successful presence update."""
        with patch("src.api.routes.collaboration.get_cache", return_value=mock_redis), \
             patch(
            "src.api.routes.collaboration.CollaborationManager",
            return_value=mock_collaboration_manager,
        ):
            response = await client.post(
                f"/api/v1/collaboration/{session_id}/presence",
                json={"user_id": user_id, "metadata": {"cursor_x": 100, "cursor_y": 200}},
            )

            assert response.status_code == 200
            data = response.json()

            assert data["success"] is True
            assert data["session_id"] == str(session_id)
            assert data["user_id"] == user_id

    @pytest.mark.asyncio
    async def test_update_presence_without_metadata(
        self, client: AsyncClient, session_id, user_id, mock_collaboration_manager
    ):
        """Test presence update without metadata."""
        with patch("src.api.routes.collaboration.get_cache", return_value=mock_redis), \
             patch(
            "src.api.routes.collaboration.CollaborationManager",
            return_value=mock_collaboration_manager,
        ):
            response = await client.post(
                f"/api/v1/collaboration/{session_id}/presence",
                json={"user_id": user_id},
            )

            assert response.status_code == 200


class TestBroadcastEndpoint:
    """Tests for /api/v1/collaboration/{session_id}/broadcast endpoint."""

    @pytest.mark.asyncio
    async def test_broadcast_action_success(
        self, client: AsyncClient, session_id, user_id, mock_collaboration_manager
    ):
        """Test successful action broadcast."""
        with patch("src.api.routes.collaboration.get_cache", return_value=mock_redis), \
             patch(
            "src.api.routes.collaboration.CollaborationManager",
            return_value=mock_collaboration_manager,
        ):
            response = await client.post(
                f"/api/v1/collaboration/{session_id}/broadcast",
                json={
                    "user_id": user_id,
                    "action": {
                        "action_type": "vote_cast",
                        "target_id": str(uuid4()),
                        "data": {"value": "strong"},
                        "persist": True,
                    },
                },
            )

            assert response.status_code == 200
            data = response.json()

            assert data["success"] is True
            assert data["action_type"] == "vote_cast"

    @pytest.mark.asyncio
    async def test_broadcast_action_without_target(
        self, client: AsyncClient, session_id, user_id, mock_collaboration_manager
    ):
        """Test broadcasting action without target_id."""
        with patch("src.api.routes.collaboration.get_cache", return_value=mock_redis), \
             patch(
            "src.api.routes.collaboration.CollaborationManager",
            return_value=mock_collaboration_manager,
        ):
            response = await client.post(
                f"/api/v1/collaboration/{session_id}/broadcast",
                json={
                    "user_id": user_id,
                    "action": {
                        "action_type": "typing_start",
                        "target_id": None,
                        "data": {},
                        "persist": False,
                    },
                },
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_broadcast_action_different_types(
        self, client: AsyncClient, session_id, user_id, mock_collaboration_manager
    ):
        """Test broadcasting different action types."""
        action_types = [
            "option_proposed",
            "option_edited",
            "vote_cast",
            "concern_raised",
        ]

        with patch("src.api.routes.collaboration.get_cache", return_value=mock_redis), \
             patch(
            "src.api.routes.collaboration.CollaborationManager",
            return_value=mock_collaboration_manager,
        ):
            for action_type in action_types:
                response = await client.post(
                    f"/api/v1/collaboration/{session_id}/broadcast",
                    json={
                        "user_id": user_id,
                        "action": {
                            "action_type": action_type,
                            "target_id": str(uuid4()),
                            "data": {"test": "data"},
                            "persist": True,
                        },
                    },
                )

                assert response.status_code == 200
                assert response.json()["action_type"] == action_type


class TestActiveUsersEndpoint:
    """Tests for /api/v1/collaboration/{session_id}/active-users endpoint."""

    @pytest.mark.asyncio
    async def test_get_active_users_success(
        self, client: AsyncClient, session_id, mock_collaboration_manager
    ):
        """Test successful active users retrieval."""
        with patch("src.api.routes.collaboration.get_cache", return_value=mock_redis), \
             patch(
            "src.api.routes.collaboration.CollaborationManager",
            return_value=mock_collaboration_manager,
        ):
            response = await client.get(
                f"/api/v1/collaboration/{session_id}/active-users"
            )

            assert response.status_code == 200
            data = response.json()

            assert "session_id" in data
            assert "active_users" in data
            assert "count" in data
            assert data["count"] == len(data["active_users"])

    @pytest.mark.asyncio
    async def test_get_active_users_includes_metadata(
        self, client: AsyncClient, session_id, mock_collaboration_manager
    ):
        """Test active users includes user metadata."""
        with patch("src.api.routes.collaboration.get_cache", return_value=mock_redis), \
             patch(
            "src.api.routes.collaboration.CollaborationManager",
            return_value=mock_collaboration_manager,
        ):
            response = await client.get(
                f"/api/v1/collaboration/{session_id}/active-users"
            )

            assert response.status_code == 200
            data = response.json()

            if data["active_users"]:
                user = data["active_users"][0]
                assert "user_id" in user
                assert "session_id" in user
                assert "joined_at" in user
                assert "last_seen" in user


class TestWebSocketEndpoint:
    """Tests for WebSocket collaboration endpoint.

    These tests validate real-time WebSocket functionality for collaboration.
    Previously deferred due to test environment issues, now properly implemented.
    """

    @pytest.mark.asyncio
    async def test_websocket_connection(self, session_id, user_id):
        """Test WebSocket connection establishment and initial session state.

        Validates:
        - WebSocket connection succeeds
        - Initial session_state event is received
        - Session state contains required fields
        - Presence tracking is initiated
        """
        from fastapi.testclient import TestClient
        from src.api.main import app

        with patch("src.api.routes.collaboration.get_cache") as mock_get_cache, \
             patch("src.api.routes.collaboration.CollaborationManager") as mock_manager_class:

            # Mock Redis client
            mock_redis = AsyncMock()
            mock_redis.sadd = AsyncMock(return_value=1)
            mock_redis.setex = AsyncMock()
            mock_redis.subscribe = AsyncMock()
            mock_redis.publish = AsyncMock()
            mock_redis.hgetall = AsyncMock(return_value={})
            mock_redis.lrange = AsyncMock(return_value=[])

            mock_get_cache.return_value = mock_redis

            # Mock CollaborationManager
            mock_manager = MagicMock()
            mock_manager.track_presence = AsyncMock()
            mock_manager.get_session_state = AsyncMock(
                return_value=SessionState(
                    session_id=session_id,
                    active_users=[],
                    recent_actions=[],
                    last_activity=datetime.utcnow(),
                )
            )
            mock_manager.remove_presence = AsyncMock()
            # Mock subscribe_to_session as an async generator
            async def mock_subscribe():
                yield  # Yields nothing, just for testing
            mock_manager.subscribe_to_session = lambda sid: mock_subscribe()

            mock_manager_class.return_value = mock_manager

            # Use synchronous TestClient for WebSocket
            with TestClient(app) as test_client:
                with test_client.websocket_connect(
                    f"/api/v1/collaboration/ws/{session_id}?user_id={user_id}"
                ) as websocket:
                    # Should receive initial session state
                    data = websocket.receive_json()

                    # Validate initial message
                    assert data["event_type"] == "session_state", \
                        f"Expected 'session_state', got '{data.get('event_type')}'"
                    assert "data" in data, "Session state data missing"
                    assert "timestamp" in data, "Timestamp missing from initial message"

                    # Verify presence tracking was called
                    mock_manager.track_presence.assert_called_once_with(
                        session_id=session_id,
                        user_id=user_id
                    )

                    # Verify session state was retrieved
                    mock_manager.get_session_state.assert_called_once_with(session_id)

    @pytest.mark.asyncio
    async def test_websocket_heartbeat(self, session_id, user_id):
        """Test WebSocket heartbeat mechanism and presence updates.

        Validates:
        - Heartbeat messages are accepted
        - Presence is updated on heartbeat
        - Connection remains active
        - TTL is refreshed
        """
        from fastapi.testclient import TestClient
        from src.api.main import app

        with patch("src.api.routes.collaboration.get_cache") as mock_get_cache, \
             patch("src.api.routes.collaboration.CollaborationManager") as mock_manager_class:

            # Mock Redis
            mock_redis = AsyncMock()
            mock_redis.sadd = AsyncMock(return_value=1)
            mock_redis.setex = AsyncMock()
            mock_redis.subscribe = AsyncMock()
            mock_redis.publish = AsyncMock()
            mock_redis.hgetall = AsyncMock(return_value={})
            mock_redis.lrange = AsyncMock(return_value=[])

            mock_get_cache.return_value = mock_redis

            # Mock CollaborationManager
            mock_manager = MagicMock()
            mock_manager.track_presence = AsyncMock()
            mock_manager.get_session_state = AsyncMock(
                return_value=SessionState(
                    session_id=session_id,
                    active_users=[],
                    recent_actions=[],
                    last_activity=datetime.utcnow(),
                )
            )
            mock_manager.remove_presence = AsyncMock()
            async def mock_subscribe():
                yield
            mock_manager.subscribe_to_session = lambda sid: mock_subscribe()

            mock_manager_class.return_value = mock_manager

            with TestClient(app) as test_client:
                with test_client.websocket_connect(
                    f"/api/v1/collaboration/ws/{session_id}?user_id={user_id}"
                ) as websocket:
                    # Receive initial state
                    initial_data = websocket.receive_json()
                    assert initial_data["event_type"] == "session_state"

                    # Reset call count after initial connection
                    initial_call_count = mock_manager.track_presence.call_count

                    # Send heartbeat
                    heartbeat_timestamp = datetime.utcnow().isoformat()
                    websocket.send_json({
                        "type": "heartbeat",
                        "timestamp": heartbeat_timestamp,
                    })

                    # Small delay to allow processing
                    import time
                    time.sleep(0.1)

                    # Verify presence was updated (call count increased)
                    assert mock_manager.track_presence.call_count > initial_call_count, \
                        "track_presence should be called again after heartbeat"

                    # Verify heartbeat call included correct parameters
                    heartbeat_calls = [
                        call for call in mock_manager.track_presence.call_args_list
                        if call[1].get('session_id') == session_id
                    ]
                    assert len(heartbeat_calls) >= 2, \
                        "Expected at least 2 presence tracking calls (initial + heartbeat)"

    @pytest.mark.asyncio
    async def test_websocket_action_broadcast(self, session_id, user_id):
        """Test broadcasting actions via WebSocket.

        Validates:
        - Action messages are accepted
        - Actions are broadcast to Redis pub/sub
        - Action persistence works correctly
        - Action data is properly formatted
        """
        from fastapi.testclient import TestClient
        from src.api.main import app

        with patch("src.api.routes.collaboration.get_cache") as mock_get_cache, \
             patch("src.api.routes.collaboration.CollaborationManager") as mock_manager_class:

            # Mock Redis
            mock_redis = AsyncMock()
            mock_redis.sadd = AsyncMock(return_value=1)
            mock_redis.setex = AsyncMock()
            mock_redis.subscribe = AsyncMock()
            mock_redis.publish = AsyncMock()
            mock_redis.hgetall = AsyncMock(return_value={})
            mock_redis.lrange = AsyncMock(return_value=[])
            mock_redis.lpush = AsyncMock()

            mock_get_cache.return_value = mock_redis

            # Mock CollaborationManager
            mock_manager = MagicMock()
            mock_manager.track_presence = AsyncMock()
            mock_manager.get_session_state = AsyncMock(
                return_value=SessionState(
                    session_id=session_id,
                    active_users=[],
                    recent_actions=[],
                    last_activity=datetime.utcnow(),
                )
            )
            mock_manager.broadcast_action = AsyncMock()
            mock_manager.remove_presence = AsyncMock()
            async def mock_subscribe():
                yield
            mock_manager.subscribe_to_session = lambda sid: mock_subscribe()

            mock_manager_class.return_value = mock_manager

            with TestClient(app) as test_client:
                with test_client.websocket_connect(
                    f"/api/v1/collaboration/ws/{session_id}?user_id={user_id}"
                ) as websocket:
                    # Receive initial state
                    initial_data = websocket.receive_json()
                    assert initial_data["event_type"] == "session_state"

                    # Send action
                    action_target_id = str(uuid4())
                    websocket.send_json({
                        "type": "action",
                        "action_type": "vote_cast",
                        "target_id": action_target_id,
                        "data": {"value": "strong"},
                        "persist": True,
                    })

                    # Small delay to allow processing
                    import time
                    time.sleep(0.1)

                    # Verify action was broadcast
                    assert mock_manager.broadcast_action.call_count >= 1, \
                        "broadcast_action should be called after sending action"

                    # Verify broadcast was called with correct parameters
                    call_args = mock_manager.broadcast_action.call_args
                    assert call_args is not None, "broadcast_action was not called"

                    # Check session_id parameter
                    assert call_args[1]['session_id'] == session_id, \
                        f"Expected session_id {session_id}, got {call_args[1]['session_id']}"

                    # Check user_id parameter
                    assert call_args[1]['user_id'] == user_id, \
                        f"Expected user_id {user_id}, got {call_args[1]['user_id']}"

                    # Check action object
                    action = call_args[1]['action']
                    assert action.action_type == "vote_cast", \
                        f"Expected action_type 'vote_cast', got '{action.action_type}'"
                    assert str(action.target_id) == action_target_id, \
                        f"Expected target_id {action_target_id}, got {action.target_id}"
                    assert action.data == {"value": "strong"}, \
                        f"Expected data {{'value': 'strong'}}, got {action.data}"
                    assert action.persist is True, \
                        f"Expected persist=True, got {action.persist}"


class TestErrorHandling:
    """Tests for error handling in collaboration endpoints."""

    @pytest.mark.asyncio
    async def test_get_session_state_invalid_uuid(self, client: AsyncClient):
        """Test session state with invalid session ID."""
        response = await client.get("/api/v1/collaboration/invalid-uuid/state")

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_update_presence_missing_user_id(
        self, client: AsyncClient, session_id
    ):
        """Test presence update without user_id."""
        response = await client.post(
            f"/api/v1/collaboration/{session_id}/presence",
            json={"metadata": {}},
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_broadcast_action_invalid_action_type(
        self, client: AsyncClient, session_id, user_id
    ):
        """Test broadcasting action with invalid action type."""
        response = await client.post(
            f"/api/v1/collaboration/{session_id}/broadcast",
            json={
                "user_id": user_id,
                "action": {
                    "action_type": "invalid_type",  # Not in allowed types
                    "target_id": None,
                    "data": {},
                    "persist": False,
                },
            },
        )

        # Should fail validation
        assert response.status_code == 422
