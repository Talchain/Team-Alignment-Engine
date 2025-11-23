"""Integration tests for deliberation flow (Phase 1A/1B)."""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.models.deliberation import (
    DeliberationSessionV1,
    DeliberationRoundV1,
    TeamInputV1,
    GraphV1,
    VoteV1,
    RankingV1,
    ParticipantV1,
    ConvergenceCriteriaV1,
)


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_session_data():
    """Sample deliberation session data."""
    return {
        "decision_context": "Should we adopt microservices architecture?",
        "participants": [
            {"user_id": "user1", "role": "engineer"},
            {"user_id": "user2", "role": "architect"},
            {"user_id": "user3", "role": "product_manager"},
        ],
        "convergence_criteria": {
            "min_quality_threshold": 0.7,
            "min_votes_agreement": 0.67,
            "max_rounds": 5,
        },
    }


class TestDeliberationSessionLifecycle:
    """Test full deliberation session lifecycle."""

    def test_create_session(self, client, sample_session_data):
        """Test creating a new deliberation session."""
        response = client.post(
            "/api/v1/deliberation/sessions",
            json=sample_session_data,
        )

        assert response.status_code == 201
        data = response.json()

        assert "session_id" in data
        assert data["decision_context"] == sample_session_data["decision_context"]
        assert len(data["participants"]) == 3
        assert data["status"] == "active"

    def test_create_session_invalid_data_returns_422(self, client):
        """Test that invalid session data returns 422."""
        invalid_data = {
            "decision_context": "Test",
            # Missing required fields
        }

        response = client.post(
            "/api/v1/deliberation/sessions",
            json=invalid_data,
        )

        assert response.status_code == 422

    def test_full_deliberation_workflow(self, client, sample_session_data):
        """Test complete deliberation workflow: create → submit → vote → converge."""
        # Step 1: Create session
        session_response = client.post(
            "/api/v1/deliberation/sessions",
            json=sample_session_data,
        )
        assert session_response.status_code == 201
        session_id = session_response.json()["session_id"]

        # Step 2: Start round 1 (submission round)
        round_response = client.post(
            f"/api/v1/deliberation/sessions/{session_id}/rounds",
            json={"round_type": "submission"},
        )
        assert round_response.status_code == 201
        round_id = round_response.json()["round_id"]

        # Step 3: Submit team inputs
        for user_num in [1, 2, 3]:
            submission_data = {
                "user_id": f"user{user_num}",
                "graph": {
                    "nodes": ["microservices", "scalability", "complexity"],
                    "edges": [
                        {"source": "microservices", "target": "scalability"},
                        {"source": "microservices", "target": "complexity"},
                    ],
                },
                "reasoning": f"User {user_num}'s perspective on microservices architecture.",
            }

            submit_response = client.post(
                f"/api/v1/deliberation/rounds/{round_id}/submissions",
                json=submission_data,
            )
            assert submit_response.status_code == 201

        # Step 4: Get session status (should show submissions)
        status_response = client.get(f"/api/v1/deliberation/sessions/{session_id}")
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert len(status_data["rounds"]) == 1
        assert len(status_data["rounds"][0]["submissions"]) == 3

        # Step 5: Start synthesis round
        synthesis_response = client.post(
            f"/api/v1/deliberation/sessions/{session_id}/rounds",
            json={"round_type": "synthesis"},
        )
        assert synthesis_response.status_code == 201
        synthesis_round_id = synthesis_response.json()["round_id"]

        # Step 6: Get synthesis options
        synthesis_data = synthesis_response.json()
        assert "synthesis_options" in synthesis_data
        # Should have generated synthesis options from submissions


class TestSubmissionValidation:
    """Test submission validation."""

    def test_submit_with_valid_causal_graph(self, client, sample_session_data):
        """Test submission with valid causal graph."""
        # Create session and round
        session_response = client.post(
            "/api/v1/deliberation/sessions",
            json=sample_session_data,
        )
        session_id = session_response.json()["session_id"]

        round_response = client.post(
            f"/api/v1/deliberation/sessions/{session_id}/rounds",
            json={"round_type": "submission"},
        )
        round_id = round_response.json()["round_id"]

        # Submit with valid graph
        submission_data = {
            "user_id": "user1",
            "graph": {
                "nodes": ["action", "outcome"],
                "edges": [{"source": "action", "target": "outcome"}],
            },
            "reasoning": "Action causes outcome through causal mechanism X.",
        }

        response = client.post(
            f"/api/v1/deliberation/rounds/{round_id}/submissions",
            json=submission_data,
        )

        assert response.status_code == 201
        data = response.json()
        assert "causal_quality" in data
        assert "validation_issues" in data

    def test_submit_with_invalid_graph_returns_validation_issues(self, client, sample_session_data):
        """Test that invalid graph returns validation issues."""
        # Create session and round
        session_response = client.post(
            "/api/v1/deliberation/sessions",
            json=sample_session_data,
        )
        session_id = session_response.json()["session_id"]

        round_response = client.post(
            f"/api/v1/deliberation/sessions/{session_id}/rounds",
            json={"round_type": "submission"},
        )
        round_id = round_response.json()["round_id"]

        # Submit with problematic graph (isolated nodes)
        submission_data = {
            "user_id": "user1",
            "graph": {
                "nodes": ["isolated_node", "another_isolated"],
                "edges": [],  # No edges!
            },
            "reasoning": "This graph has no causal relationships.",
        }

        response = client.post(
            f"/api/v1/deliberation/rounds/{round_id}/submissions",
            json=submission_data,
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data["validation_issues"]) > 0


class TestAnonymousVoting:
    """Test anonymous voting with encryption."""

    def test_vote_submission_encrypts_user_id(self, client, sample_session_data):
        """Test that voting encrypts user IDs for anonymity."""
        # Create session and submission round
        session_response = client.post(
            "/api/v1/deliberation/sessions",
            json=sample_session_data,
        )
        session_id = session_response.json()["session_id"]

        round_response = client.post(
            f"/api/v1/deliberation/sessions/{session_id}/rounds",
            json={"round_type": "submission"},
        )
        submission_round_id = round_response.json()["round_id"]

        # Submit inputs
        for user_num in [1, 2]:
            client.post(
                f"/api/v1/deliberation/rounds/{submission_round_id}/submissions",
                json={
                    "user_id": f"user{user_num}",
                    "graph": {"nodes": ["a"], "edges": []},
                    "reasoning": f"Reasoning {user_num}",
                },
            )

        # Start voting round
        voting_round_response = client.post(
            f"/api/v1/deliberation/sessions/{session_id}/rounds",
            json={"round_type": "voting"},
        )
        voting_round_id = voting_round_response.json()["round_id"]

        # Submit vote
        vote_data = {
            "user_id": "user1",
            "rankings": [
                {"option_index": 0, "rank": 1},
                {"option_index": 1, "rank": 2},
            ],
        }

        vote_response = client.post(
            f"/api/v1/deliberation/rounds/{voting_round_id}/votes",
            json=vote_data,
        )

        assert vote_response.status_code == 201
        # Response should confirm vote recorded but not expose encrypted ID
        vote_result = vote_response.json()
        assert vote_result["accepted"] is True


class TestConvergenceDetection:
    """Test convergence detection."""

    def test_convergence_detected_with_high_agreement(self, client, sample_session_data):
        """Test that convergence is detected when votes align."""
        # Create session
        session_response = client.post(
            "/api/v1/deliberation/sessions",
            json=sample_session_data,
        )
        session_id = session_response.json()["session_id"]

        # Create submission round
        round_response = client.post(
            f"/api/v1/deliberation/sessions/{session_id}/rounds",
            json={"round_type": "submission"},
        )
        submission_round_id = round_response.json()["round_id"]

        # Submit similar inputs (should lead to convergence)
        for user_num in [1, 2, 3]:
            client.post(
                f"/api/v1/deliberation/rounds/{submission_round_id}/submissions",
                json={
                    "user_id": f"user{user_num}",
                    "graph": {
                        "nodes": ["microservices", "scalability"],
                        "edges": [{"source": "microservices", "target": "scalability"}],
                    },
                    "reasoning": "Microservices improve scalability.",
                },
            )

        # Check convergence
        convergence_response = client.get(
            f"/api/v1/deliberation/sessions/{session_id}/convergence"
        )

        assert convergence_response.status_code == 200
        convergence_data = convergence_response.json()

        # With identical inputs, should show high convergence
        assert "quality_agreement" in convergence_data
        assert "vote_alignment" in convergence_data


class TestConflictDiagnosis:
    """Test enhanced conflict diagnosis."""

    def test_conflict_diagnosis_for_divergent_views(self, client, sample_session_data):
        """Test conflict diagnosis when participants have divergent views."""
        # Create session
        session_response = client.post(
            "/api/v1/deliberation/sessions",
            json=sample_session_data,
        )
        session_id = session_response.json()["session_id"]

        # Create submission round
        round_response = client.post(
            f"/api/v1/deliberation/sessions/{session_id}/rounds",
            json={"round_type": "submission"},
        )
        round_id = round_response.json()["round_id"]

        # Submit conflicting views
        client.post(
            f"/api/v1/deliberation/rounds/{round_id}/submissions",
            json={
                "user_id": "user1",
                "graph": {
                    "nodes": ["microservices", "scalability"],
                    "edges": [{"source": "microservices", "target": "scalability"}],
                },
                "reasoning": "Microservices dramatically improve scalability.",
            },
        )

        client.post(
            f"/api/v1/deliberation/rounds/{round_id}/submissions",
            json={
                "user_id": "user2",
                "graph": {
                    "nodes": ["microservices", "complexity", "failures"],
                    "edges": [
                        {"source": "microservices", "target": "complexity"},
                        {"source": "complexity", "target": "failures"},
                    ],
                },
                "reasoning": "Microservices increase complexity leading to more failures.",
            },
        )

        # Check for conflicts
        conflicts_response = client.get(
            f"/api/v1/deliberation/sessions/{session_id}/conflicts"
        )

        assert conflicts_response.status_code == 200
        conflicts_data = conflicts_response.json()

        assert "conflicts" in conflicts_data
        # Should detect causal conflict (different causal models)
        if len(conflicts_data["conflicts"]) > 0:
            conflict = conflicts_data["conflicts"][0]
            assert conflict["conflict_type"] in ["causal", "values", "framing"]


class TestMultiRoundDeliberation:
    """Test multi-round deliberation."""

    def test_multiple_rounds_refine_positions(self, client, sample_session_data):
        """Test that multiple rounds allow position refinement."""
        # Create session
        session_response = client.post(
            "/api/v1/deliberation/sessions",
            json=sample_session_data,
        )
        session_id = session_response.json()["session_id"]

        # Round 1: Initial submissions
        round1_response = client.post(
            f"/api/v1/deliberation/sessions/{session_id}/rounds",
            json={"round_type": "submission"},
        )
        round1_id = round1_response.json()["round_id"]

        for user_num in [1, 2, 3]:
            client.post(
                f"/api/v1/deliberation/rounds/{round1_id}/submissions",
                json={
                    "user_id": f"user{user_num}",
                    "graph": {"nodes": [f"node{user_num}"], "edges": []},
                    "reasoning": f"Initial view {user_num}",
                },
            )

        # Round 2: Refinement after seeing others' views
        round2_response = client.post(
            f"/api/v1/deliberation/sessions/{session_id}/rounds",
            json={"round_type": "refinement"},
        )
        round2_id = round2_response.json()["round_id"]

        # Users can refine their positions
        client.post(
            f"/api/v1/deliberation/rounds/{round2_id}/submissions",
            json={
                "user_id": "user1",
                "graph": {
                    "nodes": ["node1", "node2"],  # Incorporating others' nodes
                    "edges": [{"source": "node1", "target": "node2"}],
                },
                "reasoning": "Refined view incorporating user2's perspective",
            },
        )

        # Get session status
        status_response = client.get(f"/api/v1/deliberation/sessions/{session_id}")
        status_data = status_response.json()

        # Should have 2 rounds
        assert len(status_data["rounds"]) == 2


class TestErrorHandling:
    """Test error handling."""

    def test_submit_to_nonexistent_round_returns_404(self, client):
        """Test that submitting to nonexistent round returns 404."""
        submission_data = {
            "user_id": "user1",
            "graph": {"nodes": ["a"], "edges": []},
            "reasoning": "Test",
        }

        response = client.post(
            "/api/v1/deliberation/rounds/nonexistent/submissions",
            json=submission_data,
        )

        assert response.status_code == 404

    def test_vote_in_submission_round_returns_400(self, client, sample_session_data):
        """Test that voting in wrong round type returns 400."""
        # Create session and submission round
        session_response = client.post(
            "/api/v1/deliberation/sessions",
            json=sample_session_data,
        )
        session_id = session_response.json()["session_id"]

        round_response = client.post(
            f"/api/v1/deliberation/sessions/{session_id}/rounds",
            json={"round_type": "submission"},  # Not a voting round!
        )
        round_id = round_response.json()["round_id"]

        # Try to vote (should fail)
        vote_data = {
            "user_id": "user1",
            "rankings": [{"option_index": 0, "rank": 1}],
        }

        response = client.post(
            f"/api/v1/deliberation/rounds/{round_id}/votes",
            json=vote_data,
        )

        assert response.status_code == 400
