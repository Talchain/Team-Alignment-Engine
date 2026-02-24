"""Performance benchmarking command."""

import asyncio
import time
import httpx
from typing import Dict, List
from datetime import datetime
import statistics

from src.config import settings


WORKLOADS = {
    "standard": {
        "sessions": 10,
        "profiles_per_session": 5,
        "options_per_session": 3,
        "concurrent_requests": 10,
    },
    "heavy": {
        "sessions": 50,
        "profiles_per_session": 10,
        "options_per_session": 10,
        "concurrent_requests": 50,
    },
    "stress": {
        "sessions": 100,
        "profiles_per_session": 20,
        "options_per_session": 20,
        "concurrent_requests": 100,
    },
}


async def run_benchmark(workload: str, duration: int) -> Dict:
    """
    Run performance benchmark against TAE.

    Args:
        workload: Workload type (standard, heavy, stress)
        duration: Duration in seconds

    Returns:
        Benchmark results with latency percentiles and throughput
    """
    if workload not in WORKLOADS:
        raise ValueError(f"Unknown workload: {workload}. Choose from: {list(WORKLOADS.keys())}")

    config = WORKLOADS[workload]
    base_url = f"http://localhost:8000"  # TODO: Make configurable

    # Warm-up phase
    await _warmup(base_url)

    # Benchmark phase
    start_time = time.time()
    latencies: List[float] = []
    errors = 0
    requests = 0

    async with httpx.AsyncClient(timeout=30.0) as client:
        while time.time() - start_time < duration:
            # Create batch of concurrent requests
            tasks = []
            for _ in range(config["concurrent_requests"]):
                tasks.append(_make_request(client, base_url))

            # Execute batch
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Collect results
            for result in results:
                requests += 1
                if isinstance(result, Exception):
                    errors += 1
                else:
                    latencies.append(result)

            # Brief pause between batches
            await asyncio.sleep(0.1)

    # Calculate statistics
    elapsed_time = time.time() - start_time

    if not latencies:
        raise RuntimeError("No successful requests completed")

    latencies.sort()
    n = len(latencies)

    results = {
        "workload": workload,
        "duration_seconds": round(elapsed_time, 2),
        "total_requests": requests,
        "successful_requests": len(latencies),
        "failed_requests": errors,
        "requests_per_second": round(len(latencies) / elapsed_time, 2),
        "min_latency_ms": round(latencies[0], 2),
        "max_latency_ms": round(latencies[-1], 2),
        "mean_latency_ms": round(statistics.mean(latencies), 2),
        "median_latency_ms": round(statistics.median(latencies), 2),
        "p95_latency_ms": round(latencies[int(n * 0.95)], 2),
        "p99_latency_ms": round(latencies[int(n * 0.99)], 2),
        "error_rate_percent": round((errors / requests) * 100, 2),
    }

    return results


async def _warmup(base_url: str):
    """Warm-up phase to initialize connections."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            await client.get(f"{base_url}/health")
        except Exception:
            pass  # Ignore warmup failures


async def _make_request(client: httpx.AsyncClient, base_url: str) -> float:
    """
    Make a single benchmark request.

    Returns:
        Request latency in milliseconds
    """
    start = time.perf_counter()

    try:
        response = await client.get(f"{base_url}/health")
        response.raise_for_status()

        latency_ms = (time.perf_counter() - start) * 1000
        return latency_ms

    except Exception as e:
        raise RuntimeError(f"Request failed: {e}")
