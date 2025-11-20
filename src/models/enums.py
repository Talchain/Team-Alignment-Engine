"""Enumeration types for Team Alignment Engine."""

from enum import Enum


class SessionStatus(str, Enum):
    """Status of an alignment session."""

    COLLECTING = "collecting"
    ANALYZING = "analyzing"
    DELIBERATING = "deliberating"
    COMPLETE = "complete"


class AlignmentMode(str, Enum):
    """Alignment mode determining validation depth."""

    QUICK = "quick"  # Phase A only
    EVIDENCE_BACKED = "evidence_backed"  # Phase A + B


class StakeholderRole(str, Enum):
    """Role of a stakeholder in the session."""

    OWNER = "owner"  # Can close session, mark concerns addressed
    FACILITATOR = "facilitator"  # Can trigger extra ISL runs
    STAKEHOLDER = "stakeholder"  # Can propose, vote, flag concerns
    OBSERVER = "observer"  # Read-only access


class RiskLevel(str, Enum):
    """Risk tolerance level."""

    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class TimeHorizon(str, Enum):
    """Time horizon for decision outcomes."""

    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    MULTI_YEAR = "multi_year"


class FitLevel(str, Enum):
    """Fit level categorization."""

    STRONG = "strong"  # 0.7-1.0
    MODERATE = "moderate"  # 0.4-0.7
    POOR = "poor"  # 0-0.4


class ConsensusLevel(str, Enum):
    """Consensus level among stakeholders."""

    STRONG = "strong"  # >0.8 alignment
    MODERATE = "moderate"  # 0.6-0.8
    WEAK = "weak"  # 0.4-0.6
    NONE = "none"  # <0.4


class ValidationStatus(str, Enum):
    """Status of causal validation."""

    VALIDATED = "validated"
    UNCERTAIN = "uncertain"
    INSUFFICIENT_DATA = "insufficient_data"
    UNAVAILABLE = "unavailable"  # ISL timeout
    INVALID = "invalid"  # Cannot identify


class EvidenceLevel(str, Enum):
    """Strength of evidence for an assumption."""

    STRONG = "strong"
    MEDIUM = "medium"
    WEAK = "weak"
    NONE = "none"


class ImpactLevel(str, Enum):
    """Impact level if assumption is wrong."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ConcernStatus(str, Enum):
    """Status of a minority concern."""

    RAISED = "raised"
    VALIDATING = "validating"
    VALIDATED = "validated"
    DISMISSED = "dismissed"
    ADDRESSED = "addressed"


class DecisionType(str, Enum):
    """Type of decision being made."""

    PRICING = "pricing"
    FEATURE_PRIORITIZATION = "feature_prioritization"
    GTM_STRATEGY = "gtm_strategy"
    RESOURCE_ALLOCATION = "resource_allocation"
    CUSTOM = "custom"
