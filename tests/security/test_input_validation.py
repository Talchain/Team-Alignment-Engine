"""Security tests for input validation and SQL injection prevention."""

import pytest
from pydantic import ValidationError
from uuid import uuid4

from src.models.validated_requests import (
    CreateOptionRequest,
    CreateConcernRequest,
    contains_sql_injection_pattern,
)


class TestSQLInjectionPrevention:
    """Test SQL injection pattern detection."""

    def test_detect_simple_sql_injection(self):
        """Test detection of simple SQL injection patterns."""
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "admin' --",
            "1' OR '1'='1",
            "' UNION SELECT * FROM passwords --",
            "'; EXEC xp_cmdshell('dir'); --",
        ]

        for malicious_input in malicious_inputs:
            assert contains_sql_injection_pattern(malicious_input), \
                f"Failed to detect SQL injection in: {malicious_input}"

    def test_allow_safe_strings(self):
        """Test that safe strings are not flagged as SQL injection."""
        safe_inputs = [
            "This is a normal decision topic",
            "Consider option A vs option B",
            "Team alignment for Q4 planning",
            "Should we migrate to microservices?",
        ]

        for safe_input in safe_inputs:
            assert not contains_sql_injection_pattern(safe_input), \
                f"False positive SQL injection detection in: {safe_input}"


class TestInputLengthValidation:
    """Test input length constraints."""

    def test_option_title_max_length(self):
        """Test that option titles enforce max length."""
        long_title = "A" * 201  # Exceeds 200 char limit

        with pytest.raises(ValidationError) as exc_info:
            CreateOptionRequest(
                session_id=uuid4(),
                title=long_title,
                description="Valid description with enough length",
                expected_outcome="Valid outcome",
                causal_rationale="Valid rationale with enough length",
                addresses_goals=["goal1"],
                trade_offs=[],
                key_assumptions=["assumption1"],
                proposed_by="test_user"
            )

        assert "title" in str(exc_info.value)

    def test_option_description_min_length(self):
        """Test that descriptions enforce minimum length."""
        short_description = "short"  # Less than 10 chars

        with pytest.raises(ValidationError) as exc_info:
            CreateOptionRequest(
                session_id=uuid4(),
                title="Valid Title",
                description=short_description,
                expected_outcome="Valid outcome",
                causal_rationale="Valid rationale with enough length",
                addresses_goals=["goal1"],
                trade_offs=[],
                key_assumptions=["assumption1"],
                proposed_by="test_user"
            )

        assert "description" in str(exc_info.value)

    def test_concern_text_min_length(self):
        """Test that concern text enforces minimum length."""
        short_concern = "short"  # Less than 10 chars

        with pytest.raises(ValidationError) as exc_info:
            CreateConcernRequest(
                option_id=uuid4(),
                concern_text=short_concern,
                concern_type="assumption"
            )

        assert "concern_text" in str(exc_info.value)


class TestListValidation:
    """Test list size and content validation."""

    def test_addresses_goals_min_items(self):
        """Test that addresses_goals requires at least 1 item."""
        with pytest.raises(ValidationError) as exc_info:
            CreateOptionRequest(
                session_id=uuid4(),
                title="Valid Title",
                description="Valid description with enough length",
                expected_outcome="Valid outcome",
                causal_rationale="Valid rationale with enough length",
                addresses_goals=[],  # Empty list not allowed
                trade_offs=[],
                key_assumptions=["assumption1"],
                proposed_by="test_user"
            )

        assert "addresses_goals" in str(exc_info.value)

    def test_key_assumptions_max_items(self):
        """Test that key_assumptions enforces max items."""
        too_many_assumptions = [f"assumption_{i}" for i in range(51)]  # Exceeds 50

        with pytest.raises(ValidationError) as exc_info:
            CreateOptionRequest(
                session_id=uuid4(),
                title="Valid Title",
                description="Valid description with enough length",
                expected_outcome="Valid outcome",
                causal_rationale="Valid rationale with enough length",
                addresses_goals=["goal1"],
                trade_offs=[],
                key_assumptions=too_many_assumptions,
                proposed_by="test_user"
            )

        assert "key_assumptions" in str(exc_info.value)


class TestEnumValidation:
    """Test enum field validation."""

    def test_concern_type_validation(self):
        """Test that concern_type accepts only valid values."""
        valid_types = ["assumption", "outcome", "fairness", "risk"]

        for concern_type in valid_types:
            request = CreateConcernRequest(
                option_id=uuid4(),
                concern_text="This is a valid concern with enough length",
                concern_type=concern_type
            )
            assert request.concern_type == concern_type

    def test_concern_type_invalid(self):
        """Test that invalid concern types are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            CreateConcernRequest(
                option_id=uuid4(),
                concern_text="This is a valid concern with enough length",
                concern_type="invalid_type"
            )

        assert "concern_type" in str(exc_info.value)


class TestWhitespaceHandling:
    """Test handling of whitespace in inputs."""

    def test_concern_text_strips_whitespace(self):
        """Test that concern text is stripped of leading/trailing whitespace."""
        concern_text = "  Valid concern text with whitespace  "

        request = CreateConcernRequest(
            option_id=uuid4(),
            concern_text=concern_text,
            concern_type="assumption"
        )

        assert request.concern_text == concern_text.strip()

    def test_empty_after_strip_rejected(self):
        """Test that strings empty after stripping are rejected."""
        with pytest.raises(ValidationError):
            CreateConcernRequest(
                option_id=uuid4(),
                concern_text="          ",  # Only whitespace
                concern_type="assumption"
            )
