"""Prometheus metrics for Team Alignment Engine."""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
import time

# Counters
sessions_created_total = Counter(
    'tae_sessions_created_total',
    'Total number of alignment sessions created',
    ['decision_type', 'alignment_mode']
)

perspectives_collected_total = Counter(
    'tae_perspectives_collected_total',
    'Total number of stakeholder perspectives collected',
    ['extraction_source']
)

options_proposed_total = Counter(
    'tae_options_proposed_total',
    'Total number of options proposed',
    ['session_id']
)

validations_requested_total = Counter(
    'tae_validations_requested_total',
    'Total number of ISL validations requested',
    ['validation_status']
)

concerns_raised_total = Counter(
    'tae_concerns_raised_total',
    'Total number of minority concerns raised',
    ['concern_type']
)

decisions_recorded_total = Counter(
    'tae_decisions_recorded_total',
    'Total number of decisions recorded',
    ['consensus_level']
)

cee_calls_total = Counter(
    'tae_cee_calls_total',
    'Total number of CEE API calls',
    ['endpoint', 'status']
)

isl_calls_total = Counter(
    'tae_isl_calls_total',
    'Total number of ISL API calls',
    ['endpoint', 'status']
)

# Phase C Counters
ai_options_generated_total = Counter(
    'tae_ai_options_generated_total',
    'Total number of AI-generated options',
    ['mode']
)

options_synthesized_total = Counter(
    'tae_options_synthesized_total',
    'Total number of synthesized hybrid options'
)

options_tuned_total = Counter(
    'tae_options_tuned_total',
    'Total number of options tuned for minority concerns'
)

retrospectives_created_total = Counter(
    'tae_retrospectives_created_total',
    'Total number of decision retrospectives created'
)

sessions_reopened_total = Counter(
    'tae_sessions_reopened_total',
    'Total number of sessions reopened for multi-round deliberation'
)

# Histograms
request_duration_seconds = Histogram(
    'tae_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint', 'status_code'],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0)
)

profile_extraction_duration_seconds = Histogram(
    'tae_profile_extraction_duration_seconds',
    'Profile extraction duration in seconds',
    ['source'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0)
)

validation_duration_seconds = Histogram(
    'tae_validation_duration_seconds',
    'ISL validation duration in seconds',
    ['status'],
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0)
)

# Gauges
active_sessions = Gauge(
    'tae_active_sessions',
    'Number of currently active sessions',
    ['status']
)

average_consensus_strength = Gauge(
    'tae_average_consensus_strength',
    'Average consensus strength across recent decisions'
)


async def metrics_endpoint() -> Response:
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


class MetricsMiddleware:
    """Middleware to track request metrics."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope["method"]
        path = scope["path"]

        # Start timer
        start_time = time.time()

        # Status code will be set in send
        status_code = 200

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        await self.app(scope, receive, send_wrapper)

        # Record duration
        duration = time.time() - start_time
        request_duration_seconds.labels(
            method=method,
            endpoint=path,
            status_code=status_code
        ).observe(duration)
