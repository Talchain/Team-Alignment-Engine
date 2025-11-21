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

# Phase D: Organizational Intelligence Metrics

# D1: Portfolio Analytics
portfolio_analytics_requests_total = Counter(
    'tae_portfolio_analytics_requests_total',
    'Total portfolio analytics requests'
)

portfolio_health_score = Gauge(
    'tae_portfolio_health_score',
    'Current portfolio health score',
    ['organization_id']
)

portfolio_bottlenecks_detected = Gauge(
    'tae_portfolio_bottlenecks_detected',
    'Number of bottlenecks detected in portfolio',
    ['organization_id', 'severity']
)

# D2: Real-time Collaboration
websocket_connections_total = Counter(
    'tae_websocket_connections_total',
    'Total WebSocket connections established'
)

websocket_connections_active = Gauge(
    'tae_websocket_connections_active',
    'Currently active WebSocket connections',
    ['session_id']
)

collaboration_actions_broadcasted_total = Counter(
    'tae_collaboration_actions_broadcasted_total',
    'Total collaboration actions broadcasted',
    ['action_type']
)

presence_updates_total = Counter(
    'tae_presence_updates_total',
    'Total presence updates processed'
)

websocket_broadcast_duration_seconds = Histogram(
    'tae_websocket_broadcast_duration_seconds',
    'WebSocket broadcast latency in seconds',
    buckets=(0.01, 0.05, 0.1, 0.2, 0.5, 1.0)
)

# D3: Decision Dependencies
dependencies_created_total = Counter(
    'tae_dependencies_created_total',
    'Total decision dependencies created',
    ['dependency_type']
)

dependencies_resolved_total = Counter(
    'tae_dependencies_resolved_total',
    'Total dependencies resolved'
)

circular_dependencies_prevented_total = Counter(
    'tae_circular_dependencies_prevented_total',
    'Total circular dependencies prevented'
)

dependency_graph_size = Gauge(
    'tae_dependency_graph_size',
    'Number of nodes in dependency graph',
    ['organization_id']
)

dependency_graph_complexity = Gauge(
    'tae_dependency_graph_complexity',
    'Max depth of dependency graph',
    ['organization_id']
)

dependency_graph_generation_duration_seconds = Histogram(
    'tae_dependency_graph_generation_duration_seconds',
    'Dependency graph generation duration in seconds',
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0)
)

# D4: Organizational Patterns
pattern_analysis_requests_total = Counter(
    'tae_pattern_analysis_requests_total',
    'Total pattern analysis requests'
)

patterns_identified_total = Gauge(
    'tae_patterns_identified_total',
    'Number of patterns identified',
    ['organization_id', 'pattern_type']
)

pattern_confidence_average = Gauge(
    'tae_pattern_confidence_average',
    'Average confidence of identified patterns',
    ['organization_id']
)

# D5: Advanced Analytics
trend_analysis_requests_total = Counter(
    'tae_trend_analysis_requests_total',
    'Total trend analysis requests',
    ['metric_name']
)

benchmark_requests_total = Counter(
    'tae_benchmark_requests_total',
    'Total benchmark comparison requests',
    ['decision_type']
)

trend_analysis_duration_seconds = Histogram(
    'tae_trend_analysis_duration_seconds',
    'Trend analysis computation duration in seconds',
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0)
)

metric_percentile_ranking = Gauge(
    'tae_metric_percentile_ranking',
    'Percentile ranking for organizational metrics',
    ['organization_id', 'metric_name']
)

# D6: Cross-Team Coordination
conflicts_detected_total = Counter(
    'tae_conflicts_detected_total',
    'Total conflicts detected',
    ['conflict_type', 'severity']
)

conflicts_resolved_total = Counter(
    'tae_conflicts_resolved_total',
    'Total conflicts resolved',
    ['conflict_type']
)

coordination_groups_created_total = Counter(
    'tae_coordination_groups_created_total',
    'Total coordination groups created'
)

active_conflicts = Gauge(
    'tae_active_conflicts',
    'Number of active unresolved conflicts',
    ['organization_id', 'severity']
)

coordination_group_size = Histogram(
    'tae_coordination_group_size',
    'Number of sessions in coordination groups',
    buckets=(2, 3, 5, 10, 20)
)

# Cache Performance
cache_hits_total = Counter(
    'tae_cache_hits_total',
    'Total cache hits',
    ['cache_type']
)

cache_misses_total = Counter(
    'tae_cache_misses_total',
    'Total cache misses',
    ['cache_type']
)

cache_expiry_total = Counter(
    'tae_cache_expiry_total',
    'Total cache entries expired',
    ['cache_type']
)
