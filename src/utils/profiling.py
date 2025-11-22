"""Performance profiling utilities for TAE services.

Provides decorators, context managers, and reporting tools to identify
performance bottlenecks across D1-D6 capabilities.
"""

import time
import functools
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import asynccontextmanager
import asyncio
import json
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ProfileMetric:
    """Single profiling measurement."""

    operation: str
    duration_ms: float
    timestamp: datetime
    capability: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    cache_hit: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "operation": self.operation,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
            "capability": self.capability,
            "session_id": self.session_id,
            "metadata": self.metadata,
            "cache_hit": self.cache_hit,
        }


class ProfileCollector:
    """Collects and aggregates profiling metrics."""

    def __init__(self):
        self.metrics: List[ProfileMetric] = []
        self._slow_threshold_ms = 1000.0  # Log operations >1s

    def record(self, metric: ProfileMetric):
        """Record a profiling metric."""
        self.metrics.append(metric)

        # Log slow operations
        if metric.duration_ms > self._slow_threshold_ms:
            logger.warning(
                f"Slow operation detected: {metric.operation}",
                extra={
                    "duration_ms": metric.duration_ms,
                    "capability": metric.capability,
                    "session_id": metric.session_id,
                    "metadata": metric.metadata,
                }
            )

    def get_stats(
        self,
        operation: Optional[str] = None,
        capability: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get statistical summary of metrics."""
        filtered = self.metrics

        if operation:
            filtered = [m for m in filtered if m.operation == operation]
        if capability:
            filtered = [m for m in filtered if m.capability == capability]

        if not filtered:
            return {
                "count": 0,
                "mean_ms": 0,
                "min_ms": 0,
                "max_ms": 0,
                "p50_ms": 0,
                "p95_ms": 0,
                "p99_ms": 0,
            }

        durations = sorted([m.duration_ms for m in filtered])
        count = len(durations)

        return {
            "count": count,
            "mean_ms": sum(durations) / count,
            "min_ms": durations[0],
            "max_ms": durations[-1],
            "p50_ms": durations[int(count * 0.50)],
            "p95_ms": durations[int(count * 0.95)],
            "p99_ms": durations[int(count * 0.99)],
        }

    def get_cache_hit_rate(self, operation: Optional[str] = None) -> float:
        """Calculate cache hit rate for operations."""
        filtered = [
            m for m in self.metrics
            if m.cache_hit is not None and (operation is None or m.operation == operation)
        ]

        if not filtered:
            return 0.0

        hits = sum(1 for m in filtered if m.cache_hit)
        return hits / len(filtered)

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        # Overall stats
        overall = self.get_stats()

        # Per-capability stats
        capabilities = {}
        for cap in ["d1", "d2", "d3", "d4", "d5", "d6"]:
            cap_metrics = [m for m in self.metrics if m.capability == cap]
            if cap_metrics:
                capabilities[cap] = self.get_stats(capability=cap)
                capabilities[cap]["cache_hit_rate"] = self.get_cache_hit_rate()

        # Per-operation stats
        operations = {}
        unique_ops = set(m.operation for m in self.metrics)
        for op in unique_ops:
            operations[op] = self.get_stats(operation=op)

        # Slowest operations
        slowest = sorted(self.metrics, key=lambda m: m.duration_ms, reverse=True)[:10]

        return {
            "summary": {
                "total_operations": len(self.metrics),
                "time_period": {
                    "start": min(m.timestamp for m in self.metrics).isoformat() if self.metrics else None,
                    "end": max(m.timestamp for m in self.metrics).isoformat() if self.metrics else None,
                },
                "overall_stats": overall,
            },
            "capabilities": capabilities,
            "operations": operations,
            "slowest_operations": [m.to_dict() for m in slowest],
        }

    def save_report(self, path: Path):
        """Save performance report to file."""
        report = self.generate_report()
        with open(path, "w") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Performance report saved to {path}")

    def clear(self):
        """Clear all collected metrics."""
        self.metrics.clear()


# Global collector instance
_collector = ProfileCollector()


def get_collector() -> ProfileCollector:
    """Get the global profiling collector."""
    return _collector


def profile_sync(
    operation: str,
    capability: Optional[str] = None
) -> Callable:
    """Decorator to profile synchronous functions.

    Args:
        operation: Name of the operation being profiled
        capability: Optional capability name (d1-d6)

    Example:
        @profile_sync("calculate_consensus", capability="d1")
        def calculate_consensus(session):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration_ms = (time.perf_counter() - start) * 1000
                metric = ProfileMetric(
                    operation=operation,
                    duration_ms=duration_ms,
                    timestamp=datetime.utcnow(),
                    capability=capability,
                )
                _collector.record(metric)
        return wrapper
    return decorator


def profile_async(
    operation: str,
    capability: Optional[str] = None
) -> Callable:
    """Decorator to profile async functions.

    Args:
        operation: Name of the operation being profiled
        capability: Optional capability name (d1-d6)

    Example:
        @profile_async("get_analytics", capability="d5")
        async def _get_analytics(self, org_id):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration_ms = (time.perf_counter() - start) * 1000
                metric = ProfileMetric(
                    operation=operation,
                    duration_ms=duration_ms,
                    timestamp=datetime.utcnow(),
                    capability=capability,
                )
                _collector.record(metric)
        return wrapper
    return decorator


@asynccontextmanager
async def profile_block(
    operation: str,
    capability: Optional[str] = None,
    session_id: Optional[str] = None,
    cache_hit: Optional[bool] = None,
    **metadata
):
    """Context manager to profile a code block.

    Args:
        operation: Name of the operation being profiled
        capability: Optional capability name (d1-d6)
        session_id: Optional session ID
        cache_hit: Optional cache hit indicator
        **metadata: Additional metadata to record

    Example:
        async with profile_block("d5_analytics", capability="d5", session_id=sid):
            result = await analytics_engine.analyze_trends(...)
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        metric = ProfileMetric(
            operation=operation,
            duration_ms=duration_ms,
            timestamp=datetime.utcnow(),
            capability=capability,
            session_id=session_id,
            cache_hit=cache_hit,
            metadata=metadata,
        )
        _collector.record(metric)


def print_stats(
    operation: Optional[str] = None,
    capability: Optional[str] = None
):
    """Print profiling statistics to console.

    Args:
        operation: Filter by operation name
        capability: Filter by capability (d1-d6)
    """
    stats = _collector.get_stats(operation=operation, capability=capability)

    filter_desc = []
    if operation:
        filter_desc.append(f"operation={operation}")
    if capability:
        filter_desc.append(f"capability={capability}")
    filter_str = f" ({', '.join(filter_desc)})" if filter_desc else ""

    print(f"\n{'='*60}")
    print(f"Profiling Statistics{filter_str}")
    print(f"{'='*60}")
    print(f"Count:    {stats['count']}")
    print(f"Mean:     {stats['mean_ms']:.2f}ms")
    print(f"Min:      {stats['min_ms']:.2f}ms")
    print(f"Max:      {stats['max_ms']:.2f}ms")
    print(f"p50:      {stats['p50_ms']:.2f}ms")
    print(f"p95:      {stats['p95_ms']:.2f}ms")
    print(f"p99:      {stats['p99_ms']:.2f}ms")

    if operation:
        cache_rate = _collector.get_cache_hit_rate(operation=operation)
        if cache_rate > 0:
            print(f"Cache hit rate: {cache_rate:.1%}")

    print(f"{'='*60}\n")
