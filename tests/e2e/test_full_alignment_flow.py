"""End-to-end test for full alignment flow."""

import pytest
from uuid import uuid4
from httpx import AsyncClient

from src.api.main import app


@pytest.mark.asyncio
async def test_full_alignment_flow_quick_mode():
    """
    Test complete alignment flow in quick mode (without ISL validation).

    Scenario: 3 stakeholders, 3 options, majority consensus reached.
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Step 1: Create session
        team_id = str(uuid4())
        user1, user2, user3 = str(uuid4()), str(uuid4()), str(uuid4())

        session_response = await client.post(
            "/api/v1/alignment/sessions",
            json={
                "team_id": team_id,
                "decision_topic": "Q2 Pricing Strategy - E2E Test",
                "decision_context": "Balance growth and retention",
                "decision_type": "pricing",
                "alignment_mode": "quick",  # No ISL validation
                "stakeholders": [
                    {"user_id": user1, "role": "owner", "name": "Alice", "email": "alice@test.com"},
                    {"user_id": user2, "role": "stakeholder", "name": "Bob", "email": "bob@test.com"},
                    {"user_id": user3, "role": "stakeholder", "name": "Charlie", "email": "charlie@test.com"},
                ],
                "created_by": user1,
            },
        )

        assert session_response.status_code == 201
        session_data = session_response.json()
        session_id = session_data["session_id"]
        assert session_data["status"] == "collecting"

        # Step 2: Submit perspectives for all stakeholders
        perspectives = [
            {
                "user_id": user1,
                "role": "PM",
                "desired_outcome": "Increase revenue by 15% while keeping churn below 5%",
                "key_concerns": ["Customer reaction", "Competitive pressure"],
            },
            {
                "user_id": user2,
                "role": "Designer",
                "desired_outcome": "Maintain brand perception and customer satisfaction",
                "key_concerns": ["User experience", "Value perception"],
            },
            {
                "user_id": user3,
                "role": "Engineer",
                "desired_outcome": "Implement changes within 8-week timeline",
                "key_concerns": ["Technical complexity", "Timeline risk"],
            },
        ]

        for perspective in perspectives:
            response = await client.post(
                f"/api/v1/alignment/sessions/{session_id}/perspectives",
                json=perspective,
            )
            assert response.status_code == 201

        # Step 3: Check session moved to analyzing (after all profiles collected)
        session_status = await client.get(f"/api/v1/alignment/sessions/{session_id}")
        assert session_status.status_code == 200

        # Step 4: Trigger analysis manually (would be automatic in production)
        analysis_response = await client.post(
            f"/api/v1/alignment/sessions/{session_id}/analyze"
        )
        assert analysis_response.status_code == 200
        analysis_data = analysis_response.json()

        # Should have shared ground and disagreement map
        assert "shared_ground" in analysis_data
        assert "disagreement_map" in analysis_data

        # Step 5: Propose options
        options = [
            {
                "proposed_by": user1,
                "title": "15% Price Increase with Feature Bundle",
                "description": "Increase price 15% while adding value features",
                "expected_outcome": "Revenue +15%, Churn <5%",
                "causal_rationale": "Price elasticity research indicates low sensitivity",
                "addresses_goals": ["revenue_growth", "customer_retention"],
                "trade_offs": ["Implementation time"],
                "key_assumptions": [
                    {"assumption_id": "a1", "assumption_text": "Price elasticity < 0.5"}
                ],
            },
            {
                "proposed_by": user2,
                "title": "10% Increase with Premium Tier",
                "description": "Smaller increase with new premium option",
                "expected_outcome": "Revenue +12%, Churn <3%",
                "causal_rationale": "Value-based pricing approach",
                "addresses_goals": ["revenue_growth", "brand_perception"],
                "trade_offs": ["Lower revenue target"],
                "key_assumptions": [
                    {"assumption_id": "a2", "assumption_text": "Premium adoption >20%"}
                ],
            },
            {
                "proposed_by": user3,
                "title": "Status Quo (Baseline)",
                "description": "Maintain current pricing",
                "expected_outcome": "No change",
                "causal_rationale": "Minimize risk",
                "addresses_goals": ["customer_retention"],
                "trade_offs": ["No revenue growth"],
                "key_assumptions": [
                    {"assumption_id": "a3", "assumption_text": "Market remains stable"}
                ],
            },
        ]

        option_ids = []
        for option in options:
            response = await client.post(
                f"/api/v1/alignment/sessions/{session_id}/options",
                json=option,
            )
            assert response.status_code == 201
            option_ids.append(response.json()["option_id"])

        # Step 6: Get option details (should include fit scores)
        for option_id in option_ids:
            response = await client.get(
                f"/api/v1/alignment/sessions/{session_id}/options/{option_id}"
            )
            assert response.status_code == 200
            option_data = response.json()

            # Should have fit summary
            assert "tier1_summary" in option_data
            assert "fit_summary" in option_data["tier1_summary"]

        # Step 7: Record decision (choose option 1)
        from datetime import datetime, timedelta

        decision_response = await client.post(
            f"/api/v1/alignment/sessions/{session_id}/decide",
            json={
                "decided_by": user1,
                "chosen_option_id": option_ids[0],
                "decision_rationale": "Best balance of revenue growth and retention",
                "stakeholder_support": {
                    user1: "strong",
                    user2: "moderate",
                    user3: "strong",
                },
                "accepted_assumptions": [
                    {
                        "assumption_id": "a1",
                        "assumption_text": "Price elasticity < 0.5",
                        "evidence_strength": "medium",
                        "impact_if_wrong": "high",
                    }
                ],
                "monitored_risks": ["Market reaction", "Competitor response"],
                "minority_concerns_addressed": [],
                "review_date": (datetime.utcnow() + timedelta(days=90)).isoformat(),
                "success_criteria": ["Revenue +12%", "Churn <5%"],
                "monitoring_plan": ["Weekly dashboard", "Monthly review"],
            },
        )

        assert decision_response.status_code == 201
        decision_data = decision_response.json()
        assert decision_data["status"] == "complete"

        # Step 8: Export decision brief
        brief_response = await client.get(
            f"/api/v1/alignment/sessions/{session_id}/brief"
        )
        assert brief_response.status_code == 200
        brief_data = brief_response.json()

        # Verify brief has all required fields
        assert "chosen_option" in brief_data
        assert "decision_rationale" in brief_data
        assert "consensus_strength" in brief_data
        assert brief_data["consensus_strength"] > 0.7  # Strong consensus
        assert "success_criteria" in brief_data
        assert len(brief_data["success_criteria"]) > 0


@pytest.mark.asyncio
async def test_minority_concern_flow():
    """Test minority concern validation flow."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create session and collect perspectives (abbreviated)
        team_id = str(uuid4())
        user1, user2 = str(uuid4()), str(uuid4())

        session_response = await client.post(
            "/api/v1/alignment/sessions",
            json={
                "team_id": team_id,
                "decision_topic": "Test Concern Flow",
                "decision_context": "Test",
                "decision_type": "custom",
                "alignment_mode": "quick",
                "stakeholders": [
                    {"user_id": user1, "role": "owner", "name": "User1", "email": "u1@test.com"},
                    {"user_id": user2, "role": "stakeholder", "name": "User2", "email": "u2@test.com"},
                ],
                "created_by": user1,
            },
        )

        session_id = session_response.json()["session_id"]

        # Submit perspectives
        for user_id in [user1, user2]:
            await client.post(
                f"/api/v1/alignment/sessions/{session_id}/perspectives",
                json={
                    "user_id": user_id,
                    "role": "PM",
                    "desired_outcome": "Test outcome",
                    "key_concerns": ["Test concern"],
                },
            )

        # Trigger analysis
        await client.post(f"/api/v1/alignment/sessions/{session_id}/analyze")

        # Propose option
        option_response = await client.post(
            f"/api/v1/alignment/sessions/{session_id}/options",
            json={
                "proposed_by": user1,
                "title": "Test Option",
                "description": "Test",
                "expected_outcome": "Test",
                "causal_rationale": "Test",
                "addresses_goals": ["test_goal"],
                "trade_offs": [],
                "key_assumptions": [
                    {"assumption_id": "a1", "assumption_text": "Test assumption"}
                ],
            },
        )

        option_id = option_response.json()["option_id"]

        # Flag concern
        concern_response = await client.post(
            f"/api/v1/alignment/sessions/{session_id}/options/{option_id}/concerns",
            json={
                "raised_by": user2,
                "concern_text": "Timeline assumption seems unrealistic",
                "concern_type": "assumption",
                "assumption_id_tested": "a1",
                "request_sensitivity_test": False,  # Quick mode, no ISL
            },
        )

        assert concern_response.status_code == 201
        concern_data = concern_response.json()
        assert "concern_id" in concern_data

        # Get concern details
        concern_id = concern_data["concern_id"]
        get_concern = await client.get(
            f"/api/v1/alignment/sessions/{session_id}/concerns/{concern_id}"
        )

        assert get_concern.status_code == 200
        assert get_concern.json()["concern_text"] == "Timeline assumption seems unrealistic"
