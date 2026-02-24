"""Seed test data for local development and testing."""

import asyncio
import logging
from typing import Dict, List
from uuid import uuid4
from datetime import datetime, timedelta
from sqlalchemy import select, delete

from src.storage.database import AsyncSessionLocal
from src.storage.db_models import (
    SessionDB,
    ProfileDB,
    OptionDB,
    ValidationDB,
    FitDB,
    ConcernDB,
    DecisionBriefDB,
    DecisionDependencyDB,
    PatternAnalysisCacheDB,
    CoordinationGroupDB,
    DetectedConflictDB,
    AnalyticsCacheDB,
)
from src.models.enums import (
    SessionStatus,
    AlignmentMode,
    DecisionType,
    StakeholderRole,
    RiskLevel,
    TimeHorizon,
    ValidationStatus,
    ConcernStatus,
)

logger = logging.getLogger(__name__)


# Sample data templates
SAMPLE_TEAMS = [
    uuid4(),
    uuid4(),
    uuid4(),
]

SAMPLE_ORGANIZATIONS = [
    uuid4(),
    uuid4(),
]

SAMPLE_USERS = [
    {"id": uuid4(), "name": "Alice Chen", "email": "alice@example.com", "role": "PM"},
    {"id": uuid4(), "name": "Bob Martinez", "email": "bob@example.com", "role": "Designer"},
    {"id": uuid4(), "name": "Carol Johnson", "email": "carol@example.com", "role": "Engineer"},
    {"id": uuid4(), "name": "David Kim", "email": "david@example.com", "role": "Marketing"},
    {"id": uuid4(), "name": "Eve Thompson", "email": "eve@example.com", "role": "Sales"},
    {"id": uuid4(), "name": "Frank Wilson", "email": "frank@example.com", "role": "Engineering Manager"},
    {"id": uuid4(), "name": "Grace Lee", "email": "grace@example.com", "role": "Product Designer"},
    {"id": uuid4(), "name": "Henry Davis", "email": "henry@example.com", "role": "Data Scientist"},
]

DECISION_TOPICS = {
    DecisionType.PRICING: [
        ("Q2 Pricing Strategy", "Balance revenue growth with customer retention"),
        ("Enterprise Tier Pricing", "Determine pricing for new enterprise tier"),
        ("Discount Policy Update", "Revise discount policy for annual contracts"),
    ],
    DecisionType.FEATURE_PRIORITIZATION: [
        ("Mobile App Roadmap", "Prioritize features for mobile app launch"),
        ("Dashboard Redesign Scope", "Determine scope for dashboard redesign"),
        ("API Integration Features", "Choose which integrations to build first"),
    ],
    DecisionType.GTM_STRATEGY: [
        ("Product Launch Strategy", "Go-to-market plan for new product"),
        ("Marketing Channel Mix", "Allocate budget across marketing channels"),
        ("Sales Territory Planning", "Restructure sales territories"),
    ],
    DecisionType.RESOURCE_ALLOCATION: [
        ("Engineering Team Allocation", "Distribute engineers across projects"),
        ("Q3 Budget Distribution", "Allocate Q3 budget across departments"),
        ("Hiring Priorities", "Determine hiring priorities for next quarter"),
    ],
}

OPTIONS_TEMPLATES = {
    DecisionType.PRICING: [
        {
            "title": "Aggressive Growth Pricing",
            "description": "Lower prices to maximize customer acquisition",
            "expected_outcome": "30% increase in new customers, 10% revenue growth",
            "causal_rationale": "Lower barriers to entry will attract price-sensitive customers",
        },
        {
            "title": "Premium Positioning",
            "description": "Increase prices to position as premium product",
            "expected_outcome": "20% higher revenue per customer, potential 5% churn",
            "causal_rationale": "Premium pricing signals quality and attracts enterprise customers",
        },
        {
            "title": "Value-Based Pricing",
            "description": "Price based on customer value tiers",
            "expected_outcome": "15% revenue increase, improved retention",
            "causal_rationale": "Customers pay based on value received, reducing churn",
        },
    ],
    DecisionType.FEATURE_PRIORITIZATION: [
        {
            "title": "User-Requested Features",
            "description": "Focus on most-requested features from users",
            "expected_outcome": "Higher satisfaction scores, 20% increase in engagement",
            "causal_rationale": "Building what users ask for will increase satisfaction",
        },
        {
            "title": "Technical Debt Reduction",
            "description": "Prioritize refactoring and technical improvements",
            "expected_outcome": "30% faster development velocity in 6 months",
            "causal_rationale": "Reducing tech debt enables faster feature development",
        },
        {
            "title": "Competitive Parity Features",
            "description": "Build features competitors have",
            "expected_outcome": "Reduce competitive disadvantage, improve win rate",
            "causal_rationale": "Matching competitor features prevents customer loss",
        },
    ],
}


async def seed_database(scenario: str, clear_existing: bool = False) -> Dict[str, int]:
    """
    Seed database with test data.

    Args:
        scenario: Scenario type (default, complex, stress)
        clear_existing: Whether to clear existing data first

    Returns:
        Dictionary with counts of created entities
    """
    counts = {
        "sessions": 0,
        "profiles": 0,
        "options": 0,
        "validations": 0,
        "fits": 0,
        "concerns": 0,
        "decision_briefs": 0,
        "dependencies": 0,
        "patterns": 0,
        "coordination_groups": 0,
        "conflicts": 0,
    }

    async with AsyncSessionLocal() as db:
        try:
            # Clear existing data if requested
            if clear_existing:
                await _clear_all_data(db)
                logger.info("Cleared existing test data")

            # Seed based on scenario
            if scenario == "default":
                counts = await _seed_default_scenario(db)
            elif scenario == "complex":
                counts = await _seed_complex_scenario(db)
            elif scenario == "stress":
                counts = await _seed_stress_scenario(db)
            else:
                raise ValueError(f"Unknown scenario: {scenario}")

            await db.commit()
            logger.info(f"Successfully seeded {scenario} scenario")

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to seed database: {e}")
            raise

    return counts


async def _clear_all_data(db) -> None:
    """Clear all test data from database."""
    # Delete in reverse order of dependencies
    await db.execute(delete(AnalyticsCacheDB))
    await db.execute(delete(DetectedConflictDB))
    await db.execute(delete(CoordinationGroupDB))
    await db.execute(delete(PatternAnalysisCacheDB))
    await db.execute(delete(DecisionDependencyDB))
    await db.execute(delete(DecisionBriefDB))
    await db.execute(delete(ConcernDB))
    await db.execute(delete(FitDB))
    await db.execute(delete(ValidationDB))
    await db.execute(delete(OptionDB))
    await db.execute(delete(ProfileDB))
    await db.execute(delete(SessionDB))
    await db.flush()


async def _seed_default_scenario(db) -> Dict[str, int]:
    """Seed default scenario (2-3 sessions for quick testing)."""
    counts = {
        "sessions": 0,
        "profiles": 0,
        "options": 0,
        "validations": 0,
        "fits": 0,
        "concerns": 0,
        "decision_briefs": 0,
        "dependencies": 0,
        "patterns": 0,
        "coordination_groups": 0,
        "conflicts": 0,
    }

    # Create 3 sessions with different decision types
    decision_types = [DecisionType.PRICING, DecisionType.FEATURE_PRIORITIZATION, DecisionType.GTM_STRATEGY]

    for i, decision_type in enumerate(decision_types):
        topic, context = DECISION_TOPICS[decision_type][0]

        session = SessionDB(
            session_id=uuid4(),
            team_id=SAMPLE_TEAMS[i % len(SAMPLE_TEAMS)],
            organization_id=SAMPLE_ORGANIZATIONS[0],
            decision_topic=topic,
            decision_context=context,
            decision_type=decision_type,
            alignment_mode=AlignmentMode.EVIDENCE_BACKED,
            status=SessionStatus.DELIBERATING if i == 0 else SessionStatus.COLLECTING,
            stakeholders=[
                {"user_id": str(user["id"]), "role": user["role"], "name": user["name"], "email": user["email"]}
                for user in SAMPLE_USERS[:4]
            ],
            created_by=SAMPLE_USERS[0]["id"],
            created_at=datetime.utcnow() - timedelta(days=i+1),
        )
        db.add(session)
        counts["sessions"] += 1

        # Create stakeholder profiles
        for j, user in enumerate(SAMPLE_USERS[:4]):
            profile = ProfileDB(
                profile_id=uuid4(),
                session_id=session.session_id,
                user_id=user["id"],
                role=user["role"],
                stakeholder_role=StakeholderRole.OWNER if j == 0 else StakeholderRole.STAKEHOLDER,
                desired_outcome=f"Achieve optimal {decision_type.value} outcome",
                key_concerns=["timeline", "cost", "quality"][:j+1],
                goal_weights={"revenue_growth": 0.8, "customer_retention": 0.6, "product_quality": 0.7},
                risk_tolerance=list(RiskLevel)[j % len(RiskLevel)],
                time_horizon=list(TimeHorizon)[j % len(TimeHorizon)],
                must_have_constraints=[f"Constraint {j+1}"],
                red_lines=[f"Red line {j+1}"] if j < 2 else [],
            )
            db.add(profile)
            counts["profiles"] += 1

        # Create options
        option_templates = OPTIONS_TEMPLATES.get(decision_type, OPTIONS_TEMPLATES[DecisionType.PRICING])[:3]

        for k, option_template in enumerate(option_templates):
            option = OptionDB(
                option_id=uuid4(),
                session_id=session.session_id,
                proposed_by=str(SAMPLE_USERS[k % len(SAMPLE_USERS)]["id"]),
                round_number=1,
                title=option_template["title"],
                description=option_template["description"],
                expected_outcome=option_template["expected_outcome"],
                causal_rationale=option_template["causal_rationale"],
                addresses_goals=["revenue_growth", "customer_retention"],
                trade_offs=["cost vs speed", "quality vs time"],
                key_assumptions=[
                    {"assumption_id": f"a{k+1}", "assumption_text": f"Assumption {k+1} holds true"}
                ],
                is_baseline=(k == 0),
                status="validated" if k < 2 else "proposed",
            )
            db.add(option)
            counts["options"] += 1

            # Add validation for first option
            if k == 0:
                validation = ValidationDB(
                    validation_id=uuid4(),
                    option_id=option.option_id,
                    is_identifiable=True,
                    validation_status=ValidationStatus.VALIDATED,
                    data_sufficiency="sufficient",
                    predicted_outcomes={"revenue_growth": 0.15, "churn_rate": 0.05},
                    key_assumptions=[{"id": "a1", "validated": True}],
                    warnings=[],
                    quality_concerns=[],
                    sensitivity_factors={"price_sensitivity": 0.8},
                    isl_response={"status": "success"},
                )
                db.add(validation)
                counts["validations"] += 1

                # Add fit analysis
                fit = FitDB(
                    fit_id=uuid4(),
                    option_id=option.option_id,
                    stakeholder_fits={
                        str(user["id"]): {"fit_score": 0.7 + (j * 0.05), "concerns": []}
                        for j, user in enumerate(SAMPLE_USERS[:4])
                    },
                    overall_alignment=0.75,
                    consensus_level="moderate",
                )
                db.add(fit)
                counts["fits"] += 1

            # Add concern for second option
            if k == 1 and i == 0:
                concern = ConcernDB(
                    concern_id=uuid4(),
                    option_id=option.option_id,
                    raised_by=SAMPLE_USERS[2]["id"],
                    concern_text="This option may negatively impact existing customers",
                    concern_type="outcome_risk",
                    assumption_id_tested="a1",
                    sensitivity_tested=True,
                    causal_validation={"validated": True, "concern_severity": "medium"},
                    status=ConcernStatus.VALIDATED,
                )
                db.add(concern)
                counts["concerns"] += 1

    await db.flush()
    return counts


async def _seed_complex_scenario(db) -> Dict[str, int]:
    """Seed complex scenario (5-10 sessions with full workflows)."""
    counts = await _seed_default_scenario(db)

    # Add additional sessions
    for i in range(5):
        decision_type = list(DecisionType)[i % len(DecisionType)]
        topics = DECISION_TOPICS.get(decision_type, [("Custom Decision", "Custom context")])
        topic, context = topics[min(i, len(topics)-1)]

        session = SessionDB(
            session_id=uuid4(),
            team_id=SAMPLE_TEAMS[i % len(SAMPLE_TEAMS)],
            organization_id=SAMPLE_ORGANIZATIONS[i % len(SAMPLE_ORGANIZATIONS)],
            decision_topic=topic,
            decision_context=context,
            decision_type=decision_type,
            alignment_mode=AlignmentMode.EVIDENCE_BACKED,
            status=list(SessionStatus)[i % len(SessionStatus)],
            stakeholders=[
                {"user_id": str(user["id"]), "role": user["role"], "name": user["name"], "email": user["email"]}
                for user in SAMPLE_USERS[:6]
            ],
            created_by=SAMPLE_USERS[0]["id"],
            created_at=datetime.utcnow() - timedelta(days=10+i),
        )
        db.add(session)
        counts["sessions"] += 1

        # Create profiles and options (similar to default but with more)
        for j, user in enumerate(SAMPLE_USERS[:6]):
            profile = ProfileDB(
                profile_id=uuid4(),
                session_id=session.session_id,
                user_id=user["id"],
                role=user["role"],
                stakeholder_role=list(StakeholderRole)[j % len(StakeholderRole)],
                desired_outcome=f"Achieve optimal outcome for {decision_type.value}",
                key_concerns=["timeline", "cost", "quality", "team_capacity"][:j+1],
                goal_weights={"revenue_growth": 0.6 + (j * 0.05), "customer_retention": 0.7},
                risk_tolerance=list(RiskLevel)[j % len(RiskLevel)],
                time_horizon=list(TimeHorizon)[j % len(TimeHorizon)],
                must_have_constraints=[f"Constraint {j+1}"],
                red_lines=[],
            )
            db.add(profile)
            counts["profiles"] += 1

        # Create 5 options per session
        for k in range(5):
            option = OptionDB(
                option_id=uuid4(),
                session_id=session.session_id,
                proposed_by=str(SAMPLE_USERS[k % len(SAMPLE_USERS)]["id"]),
                round_number=1 + (k // 3),
                title=f"Option {k+1}: {decision_type.value} approach",
                description=f"Detailed description of approach {k+1} for {decision_type.value}",
                expected_outcome=f"Expected outcome for option {k+1}",
                causal_rationale=f"Causal rationale for option {k+1}",
                addresses_goals=["revenue_growth", "customer_retention", "product_quality"],
                trade_offs=["cost vs speed", "quality vs time"],
                key_assumptions=[
                    {"assumption_id": f"a{k+1}", "assumption_text": f"Assumption {k+1}"}
                ],
                is_baseline=(k == 0),
                status="validated" if k < 3 else "proposed",
            )
            db.add(option)
            counts["options"] += 1

    # Add Phase D entities
    # Get session IDs for dependencies and coordination
    result = await db.execute(select(SessionDB.session_id).limit(10))
    session_ids = [row[0] for row in result.fetchall()]

    if len(session_ids) >= 2:
        # Add decision dependencies
        for i in range(min(3, len(session_ids) - 1)):
            dependency = DecisionDependencyDB(
                dependency_id=uuid4(),
                source_session_id=session_ids[i],
                target_session_id=session_ids[i+1],
                dependency_type="depends_on" if i % 2 == 0 else "related_to",
                description=f"Dependency between decisions",
                created_by=str(SAMPLE_USERS[0]["id"]),
            )
            db.add(dependency)
            counts["dependencies"] += 1

        # Add coordination group
        coordination_group = CoordinationGroupDB(
            group_id=uuid4(),
            name="Q3 Strategic Initiatives",
            description="Coordinated decisions for Q3 planning",
            session_ids=[str(sid) for sid in session_ids[:4]],
            created_by=str(SAMPLE_USERS[0]["id"]),
        )
        db.add(coordination_group)
        counts["coordination_groups"] += 1

        # Add detected conflict
        conflict = DetectedConflictDB(
            conflict_id=uuid4(),
            conflict_type="resource",
            session_ids=[str(sid) for sid in session_ids[:2]],
            severity="medium",
            description="Resource conflict detected between parallel decisions",
            resolution_suggestions=["Prioritize decision 1", "Allocate additional resources"],
        )
        db.add(conflict)
        counts["conflicts"] += 1

    # Add pattern analysis cache
    pattern_cache = PatternAnalysisCacheDB(
        cache_id=uuid4(),
        organization_id=SAMPLE_ORGANIZATIONS[0],
        decision_type="pricing",
        pattern_type="success",
        sample_size=15,
        common_characteristics={"avg_stakeholders": 5, "avg_options": 3},
        avg_metrics={"consensus": 0.75, "decision_quality": 8.5},
        confidence=0.85,
        recommendations=["Include diverse stakeholders", "Validate with causal analysis"],
        analysis_period_days=90,
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db.add(pattern_cache)
    counts["patterns"] += 1

    await db.flush()
    return counts


async def _seed_stress_scenario(db) -> Dict[str, int]:
    """Seed stress scenario (50+ sessions for load testing)."""
    counts = {
        "sessions": 0,
        "profiles": 0,
        "options": 0,
        "validations": 0,
        "fits": 0,
        "concerns": 0,
        "decision_briefs": 0,
        "dependencies": 0,
        "patterns": 0,
        "coordination_groups": 0,
        "conflicts": 0,
    }

    # Create 50 sessions
    for i in range(50):
        decision_type = list(DecisionType)[i % len(DecisionType)]
        topics = DECISION_TOPICS.get(decision_type, [("Custom Decision", "Custom context")])
        topic, context = topics[i % len(topics)]

        session = SessionDB(
            session_id=uuid4(),
            team_id=SAMPLE_TEAMS[i % len(SAMPLE_TEAMS)],
            organization_id=SAMPLE_ORGANIZATIONS[i % len(SAMPLE_ORGANIZATIONS)],
            decision_topic=f"{topic} #{i+1}",
            decision_context=context,
            decision_type=decision_type,
            alignment_mode=AlignmentMode.EVIDENCE_BACKED if i % 2 == 0 else AlignmentMode.QUICK,
            status=list(SessionStatus)[i % len(SessionStatus)],
            stakeholders=[
                {"user_id": str(user["id"]), "role": user["role"], "name": user["name"], "email": user["email"]}
                for user in SAMPLE_USERS
            ],
            created_by=SAMPLE_USERS[i % len(SAMPLE_USERS)]["id"],
            created_at=datetime.utcnow() - timedelta(days=30+i),
        )
        db.add(session)
        counts["sessions"] += 1

        # Create 10 stakeholders per session
        for j, user in enumerate(SAMPLE_USERS):
            profile = ProfileDB(
                profile_id=uuid4(),
                session_id=session.session_id,
                user_id=user["id"],
                role=user["role"],
                stakeholder_role=list(StakeholderRole)[j % len(StakeholderRole)],
                desired_outcome=f"Achieve optimal outcome for {decision_type.value} #{i+1}",
                key_concerns=["timeline", "cost", "quality", "team_capacity"],
                goal_weights={"revenue_growth": 0.5 + (j * 0.05), "customer_retention": 0.6 + (j * 0.04)},
                risk_tolerance=list(RiskLevel)[j % len(RiskLevel)],
                time_horizon=list(TimeHorizon)[j % len(TimeHorizon)],
                must_have_constraints=[f"Constraint {j+1}"],
                red_lines=[],
            )
            db.add(profile)
            counts["profiles"] += 1

        # Create 10 options per session
        for k in range(10):
            option = OptionDB(
                option_id=uuid4(),
                session_id=session.session_id,
                proposed_by=str(SAMPLE_USERS[k % len(SAMPLE_USERS)]["id"]),
                round_number=1 + (k // 4),
                title=f"Option {k+1} for {decision_type.value} #{i+1}",
                description=f"Description of option {k+1}",
                expected_outcome=f"Expected outcome {k+1}",
                causal_rationale=f"Rationale {k+1}",
                addresses_goals=["revenue_growth", "customer_retention"],
                trade_offs=["cost vs speed"],
                key_assumptions=[
                    {"assumption_id": f"a{k+1}", "assumption_text": f"Assumption {k+1}"}
                ],
                is_baseline=(k == 0),
                status="validated" if k < 5 else "proposed",
            )
            db.add(option)
            counts["options"] += 1

        # Commit every 10 sessions to avoid memory issues
        if (i + 1) % 10 == 0:
            await db.flush()
            logger.info(f"Seeded {i+1}/50 sessions...")

    await db.flush()
    logger.info("Stress scenario seeding complete")
    return counts
