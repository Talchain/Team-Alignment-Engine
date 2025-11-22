#!/usr/bin/env python3
"""Performance profiling script for TAE services.

Generates realistic load across D1-D6 capabilities and produces
a comprehensive performance report.

Usage:
    python scripts/profile_performance.py --iterations 50
    python scripts/profile_performance.py --capabilities d1,d5,d6 --output reports/perf.json
"""

import asyncio
import argparse
import sys
from pathlib import Path
from datetime import datetime
from uuid import uuid4
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.profiling import get_collector, print_stats
from src.services.orchestration import OrchestrationService
from src.services.session_manager import SessionManager
from src.services.dependency_manager import DecisionDependencyManager
from src.services.pattern_analyzer import PatternAnalyzer
from src.services.analytics_engine import AdvancedAnalyticsEngine
from src.services.coordination_manager import CrossTeamCoordinator
from src.services.collaboration_manager import CollaborationManager
from src.models.session import SessionStatus
from src.storage.database import get_async_session
from src.config import settings


async def create_test_session(db, org_id: str) -> str:
    """Create a test session with realistic data."""
    session_manager = SessionManager()

    session = await session_manager.create(
        organization_id=org_id,
        title=f"Test Session {uuid4().hex[:8]}",
        description="Performance profiling test session",
        created_by="profiler-script",
    )

    # Add some test stakeholders
    session.stakeholders = ["user-001", "user-002", "user-003"]
    session.status = SessionStatus.DELIBERATING

    # Add shared ground data
    session.shared_ground = {
        "summary": "Team aligned on core objectives",
        "goal_weights": {"speed": 0.7, "quality": 0.8},
        "common_priorities": ["Improve performance", "Reduce latency", "Better observability"],
    }

    # Add disagreement map
    session.disagreement_map = {
        "summary": "Minor disagreements on implementation approach",
        "axes": [
            {
                "dimension": "technical_approach",
                "stakeholders": ["user-001", "user-002"],
                "severity": 0.4,
                "description": "Debate between caching strategies",
            }
        ],
    }

    return str(session.id)


async def profile_capability(
    orchestration: OrchestrationService,
    capability: str,
    session_id: str,
    org_id: str,
    iterations: int,
) -> Dict[str, Any]:
    """Profile a specific capability with multiple iterations."""
    print(f"  Profiling {capability} ({iterations} iterations)...")

    for i in range(iterations):
        try:
            if capability == "core_alignment":
                await orchestration._get_core_alignment(session_id)
            elif capability == "d3_dependencies":
                await orchestration._get_dependencies(session_id)
            elif capability == "d4_patterns":
                await orchestration._get_patterns(session_id, org_id)
            elif capability == "d5_analytics":
                await orchestration._get_analytics(org_id)
            elif capability == "d6_coordination":
                await orchestration._get_conflicts(session_id, org_id)
            elif capability == "d2_collaboration":
                await orchestration._get_collaboration(session_id)
        except Exception as e:
            print(f"    Warning: Iteration {i+1} failed: {e}")

    return {"capability": capability, "iterations": iterations}


async def profile_full_payload(
    orchestration: OrchestrationService,
    session_id: str,
    org_id: str,
    iterations: int,
) -> Dict[str, Any]:
    """Profile full payload build with all capabilities."""
    print(f"  Profiling full payload build ({iterations} iterations)...")

    capabilities = [
        "core_alignment",
        "d3_dependencies",
        "d4_patterns",
        "d5_analytics",
        "d6_coordination",
        "d2_collaboration",
    ]

    for i in range(iterations):
        try:
            await orchestration.build_alignment_payload(
                session_id=session_id,
                organization_id=org_id,
                capabilities=capabilities,
                context={},
                request_id=f"profile-{i}",
            )
        except Exception as e:
            print(f"    Warning: Iteration {i+1} failed: {e}")

    return {"test": "full_payload", "iterations": iterations}


async def main():
    """Run performance profiling."""
    parser = argparse.ArgumentParser(description="Profile TAE performance")
    parser.add_argument(
        "--iterations",
        type=int,
        default=20,
        help="Number of iterations per capability (default: 20)",
    )
    parser.add_argument(
        "--capabilities",
        type=str,
        default="all",
        help="Comma-separated capabilities to test (default: all)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output path for JSON report (default: None, print to console)",
    )
    parser.add_argument(
        "--full-payload",
        action="store_true",
        help="Also test full payload builds",
    )

    args = parser.parse_args()

    print("=" * 70)
    print("TAE Performance Profiling")
    print("=" * 70)
    print(f"Iterations per capability: {args.iterations}")
    print(f"Capabilities: {args.capabilities}")
    print(f"Full payload test: {args.full_payload}")
    print()

    # Clear any existing metrics
    collector = get_collector()
    collector.clear()

    # Setup test data
    org_id = str(uuid4())
    session_id = None

    async with get_async_session() as db:
        # Create test session
        print("Setting up test session...")
        session_id = await create_test_session(db, org_id)
        print(f"  Created session: {session_id}")
        print()

        # Initialize orchestration service
        orchestration = OrchestrationService(db=db)

        # Determine which capabilities to test
        if args.capabilities == "all":
            capabilities_to_test = [
                "core_alignment",
                "d3_dependencies",
                "d4_patterns",
                "d5_analytics",
                "d6_coordination",
                "d2_collaboration",
            ]
        else:
            capabilities_to_test = [c.strip() for c in args.capabilities.split(",")]

        # Profile each capability
        print("Running capability profiling...")
        for capability in capabilities_to_test:
            await profile_capability(
                orchestration, capability, session_id, org_id, args.iterations
            )
        print()

        # Profile full payload if requested
        if args.full_payload:
            print("Running full payload profiling...")
            await profile_full_payload(
                orchestration, session_id, org_id, args.iterations
            )
            print()

    # Generate report
    print("=" * 70)
    print("Performance Report")
    print("=" * 70)
    print()

    # Overall stats
    print_stats()

    # Per-capability stats
    for cap in ["d1", "d2", "d3", "d4", "d5", "d6"]:
        stats = collector.get_stats(capability=cap)
        if stats["count"] > 0:
            print_stats(capability=cap)

    # Generate detailed report
    report = collector.generate_report()

    # Identify slow operations (p95 > 1000ms)
    print("Slow Operations Analysis (p95 > 1000ms):")
    print("-" * 70)
    for op_name, op_stats in report["operations"].items():
        if op_stats["p95_ms"] > 1000:
            print(f"  {op_name}:")
            print(f"    p50: {op_stats['p50_ms']:.0f}ms")
            print(f"    p95: {op_stats['p95_ms']:.0f}ms")
            print(f"    p99: {op_stats['p99_ms']:.0f}ms")
            print(f"    count: {op_stats['count']}")
    print()

    # Check if any capability exceeds p95 < 5s target
    print("Latency Target Analysis (p95 < 5000ms):")
    print("-" * 70)
    target_met = True
    for cap_name, cap_stats in report["capabilities"].items():
        p95 = cap_stats.get("p95_ms", 0)
        status = "✓ PASS" if p95 < 5000 else "✗ FAIL"
        print(f"  {cap_name}: {p95:.0f}ms {status}")
        if p95 >= 5000:
            target_met = False
    print()

    if target_met:
        print("✓ All capabilities meet p95 < 5s target")
    else:
        print("✗ Some capabilities exceed p95 < 5s target - optimization needed")
    print()

    # Save report if output specified
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        collector.save_report(output_path)
        print(f"Detailed report saved to: {output_path}")

    print("=" * 70)

    return 0 if target_met else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
