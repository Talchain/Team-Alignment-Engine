#!/usr/bin/env python3
"""Simple profiling demonstration.

Shows profiling infrastructure working with sync/async functions.
"""

import asyncio
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.profiling import (
    profile_async,
    profile_sync,
    profile_block,
    get_collector,
    print_stats,
)


@profile_sync("sync_calculation", capability="d1")
def calculate_something(n: int) -> int:
    """Simulated synchronous calculation."""
    time.sleep(0.1)  # Simulate work
    return sum(range(n))


@profile_async("async_data_fetch", capability="d5")
async def fetch_data(org_id: str) -> dict:
    """Simulated async data fetch."""
    await asyncio.sleep(0.05)  # Simulate I/O
    return {"org_id": org_id, "data": "sample"}


@profile_async("async_conflict_check", capability="d6")
async def check_conflicts(session_ids: list) -> list:
    """Simulated conflict detection."""
    await asyncio.sleep(0.08)  # Simulate processing
    return []


async def main():
    """Run profiling demo."""
    print("=" * 70)
    print("Profiling Infrastructure Demo")
    print("=" * 70)
    print()

    # Clear metrics
    collector = get_collector()
    collector.clear()

    print("Running profiled operations...")
    print()

    # Execute profiled sync functions
    for i in range(10):
        calculate_something(1000)

    # Execute profiled async functions
    for i in range(15):
        await fetch_data(f"org-{i}")

    for i in range(8):
        await check_conflicts([f"session-{i}"])

    # Use profile_block context manager
    for i in range(5):
        async with profile_block(
            "d2_realtime_polling",
            capability="d2",
            session_id=f"session-{i}",
            cache_hit=i % 2 == 0,
        ):
            await asyncio.sleep(0.02)

    print("=" * 70)
    print("Performance Results")
    print("=" * 70)
    print()

    # Overall stats
    print_stats()

    # Per-capability stats
    for cap in ["d1", "d2", "d5", "d6"]:
        stats = collector.get_stats(capability=cap)
        if stats["count"] > 0:
            print_stats(capability=cap)

    # Cache hit rate for d2
    cache_rate = collector.get_cache_hit_rate()
    print(f"Overall cache hit rate: {cache_rate:.1%}")
    print()

    # Generate report
    report = collector.generate_report()

    print("Report Summary:")
    print(f"  Total operations: {report['summary']['total_operations']}")
    print(f"  Capabilities tested: {len(report['capabilities'])}")
    print(f"  Operation types: {len(report['operations'])}")
    print()

    # Save report
    output_path = Path("reports/profiling_demo.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    collector.save_report(output_path)

    print(f"✓ Detailed report saved to: {output_path}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
