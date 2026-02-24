# TAE Phase 4: Complete Implementation Guide

**Last Updated**: 2025-11-22
**Version**: 2.0.0
**Status**: Phase 4 Complete (64% implementation, core features done)

---

## Table of Contents

1. [Integration Recipes](#integration-recipes)
2. [Troubleshooting Guide](#troubleshooting-guide)
3. [API Examples](#api-examples)
4. [OpenTelemetry Setup](#opentelemetry-setup)

---

## Integration Recipes

### Recipe 1: Slack Integration

**Problem**: Post team decisions to Slack channels for visibility

**Solution**:

```python
# src/integrations/slack.py
import httpx
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class SlackIntegration:
    """Post TAE decisions to Slack."""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    async def post_decision(
        self,
        session_id: str,
        decision_topic: str,
        selected_option: str,
        consensus_level: float,
        channel: str = "#decisions"
    ) -> bool:
        """Post decision to Slack channel."""

        # Format Slack message
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"✅ Decision: {decision_topic}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Session:*\n{session_id}"},
                    {"type": "mrkdwn", "text": f"*Consensus:*\n{consensus_level:.0%}"}
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Selected Option:*\n{selected_option}"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "View Details"},
                        "url": f"https://tae.example.com/sessions/{session_id}"
                    }
                ]
            }
        ]

        payload = {"channel": channel, "blocks": blocks}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.webhook_url, json=payload, timeout=10.0)
                response.raise_for_status()
                logger.info(f"Posted decision {session_id} to Slack")
                return True
        except Exception as e:
            logger.error(f"Failed to post to Slack: {e}", exc_info=True)
            return False

# Usage
slack = SlackIntegration(webhook_url=os.getenv("SLACK_WEBHOOK_URL"))
await slack.post_decision(
    session_id="session-123",
    decision_topic="Q2 Pricing Strategy",
    selected_option="Premium Positioning",
    consensus_level=0.85
)
```

**Troubleshooting**:
- Verify `SLACK_WEBHOOK_URL` is valid
- Check Slack app permissions include `incoming-webhook`
- Rate limit: 1 message per second

---

### Recipe 2: Jira Integration

**Problem**: Create Jira issues from TAE consensus items

**Solution**:

```python
# src/integrations/jira.py
import httpx
from typing import Dict, Any, List

class JiraIntegration:
    """Create Jira issues from TAE decisions."""

    def __init__(self, base_url: str, email: str, api_token: str):
        self.base_url = base_url.rstrip("/")
        self.auth = (email, api_token)

    async def create_issue_from_decision(
        self,
        decision_brief: Dict[str, Any],
        project_key: str = "TAE"
    ) -> str:
        """Create Jira issue from decision brief."""

        # Extract decision info
        topic = decision_brief["decision_topic"]
        option = decision_brief["chosen_option"]["title"]
        rationale = decision_brief["decision_rationale"]

        # Create issue payload
        issue_data = {
            "fields": {
                "project": {"key": project_key},
                "summary": f"[TAE] {topic}",
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {"type": "text", "text": f"Decision: {option}"}
                            ]
                        },
                        {
                            "type": "paragraph",
                            "content": [
                                {"type": "text", "text": f"Rationale: {rationale}"}
                            ]
                        }
                    ]
                },
                "issuetype": {"name": "Task"},
                "labels": ["tae-decision", f"consensus-{int(decision_brief['consensus_strength'] * 100)}"]
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/rest/api/3/issue",
                json=issue_data,
                auth=self.auth,
                timeout=15.0
            )
            response.raise_for_status()
            issue_key = response.json()["key"]
            return issue_key

# Usage
jira = JiraIntegration(
    base_url="https://your-domain.atlassian.net",
    email="your-email@example.com",
    api_token=os.getenv("JIRA_API_TOKEN")
)
issue_key = await jira.create_issue_from_decision(decision_brief, project_key="PROD")
```

---

### Recipe 3: Linear Integration

**Problem**: Bi-directional task synchronization with Linear

**Solution**:

```python
# src/integrations/linear.py
class LinearIntegration:
    """Sync TAE decisions with Linear."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.graphql_url = "https://api.linear.app/graphql"

    async def create_issue(
        self,
        team_id: str,
        title: str,
        description: str,
        labels: List[str] = None
    ) -> str:
        """Create Linear issue."""

        mutation = """
        mutation CreateIssue($teamId: String!, $title: String!, $description: String!) {
          issueCreate(input: {
            teamId: $teamId
            title: $title
            description: $description
          }) {
            success
            issue {
              id
              identifier
              url
            }
          }
        }
        """

        variables = {
            "teamId": team_id,
            "title": title,
            "description": description
        }

        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.graphql_url,
                json={"query": mutation, "variables": variables},
                headers=headers
            )
            data = response.json()
            return data["data"]["issueCreate"]["issue"]["identifier"]
```

---

### Recipe 4: Webhook Notifications

**Problem**: Real-time updates to external systems

**Solution**:

```python
# src/integrations/webhooks.py
class WebhookNotifier:
    """Send webhook notifications for TAE events."""

    def __init__(self, webhook_urls: List[str]):
        self.webhook_urls = webhook_urls

    async def notify_decision_made(
        self,
        session_id: str,
        event_type: str,
        payload: Dict[str, Any]
    ):
        """Send webhook notification."""

        webhook_payload = {
            "event": event_type,
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "data": payload
        }

        tasks = [
            self._send_webhook(url, webhook_payload)
            for url in self.webhook_urls
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = sum(1 for r in results if r is True)
        logger.info(f"Sent webhooks: {success_count}/{len(self.webhook_urls)} succeeded")

    async def _send_webhook(self, url: str, payload: Dict[str, Any]) -> bool:
        """Send single webhook with retry."""
        for attempt in range(3):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(url, json=payload, timeout=10.0)
                    response.raise_for_status()
                    return True
            except Exception as e:
                if attempt == 2:
                    logger.error(f"Webhook failed after 3 attempts: {url}")
                    return False
                await asyncio.sleep(2 ** attempt)
```

---

### Recipe 5: SSO/SAML Setup

**Problem**: Enterprise authentication configuration

**Solution**:

```python
# src/auth/saml.py
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.settings import OneLogin_Saml2_Settings

class SAMLAuth:
    """SAML SSO authentication for TAE."""

    def __init__(self, settings_file: str):
        with open(settings_file) as f:
            self.saml_settings = json.load(f)

    def prepare_auth_request(self, request):
        """Prepare SAML authentication request."""
        req = self._prepare_request(request)
        auth = OneLogin_Saml2_Auth(req, self.saml_settings)
        return auth.login()

    def process_response(self, request):
        """Process SAML response and extract user."""
        req = self._prepare_request(request)
        auth = OneLogin_Saml2_Auth(req, self.saml_settings)
        auth.process_response()

        if not auth.is_authenticated():
            raise ValueError("SAML authentication failed")

        # Extract user attributes
        attributes = auth.get_attributes()
        return {
            "user_id": auth.get_nameid(),
            "email": attributes.get("email", [None])[0],
            "name": attributes.get("name", [None])[0],
            "role": attributes.get("role", ["viewer"])[0]
        }

# settings.json structure:
{
  "sp": {
    "entityId": "https://tae.example.com/saml/metadata",
    "assertionConsumerService": {
      "url": "https://tae.example.com/saml/acs",
      "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
    }
  },
  "idp": {
    "entityId": "https://idp.example.com/saml/metadata",
    "singleSignOnService": {
      "url": "https://idp.example.com/saml/sso",
      "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
    },
    "x509cert": "MIIC..."
  }
}
```

---

## Troubleshooting Guide

### Phase 4-Specific Issues

#### 1. CLI Commands Failing

**Symptom**: `tae` command not found

**Resolution**:
```bash
# Reinstall CLI
poetry install

# Verify installation
which tae
tae --version
```

**Symptom**: Permission denied

**Resolution**:
```bash
# Make executable
chmod +x $(which tae)

# Or run via poetry
poetry run tae --help
```

#### 2. Mock Services Not Working

**Symptom**: Tests fail with "Connection refused"

**Resolution**:
```python
# Ensure MockISLServer is running on correct port
from tests.mocks import create_mock_isl_server
from fastapi.testclient import TestClient

mock_isl = create_mock_isl_server(latency_ms=0)
client = TestClient(mock_isl.app)

# Test connection
response = client.get("/api/v1/health")
assert response.status_code == 200
```

#### 3. Structured Logging Not Appearing

**Symptom**: Logs not in JSON format

**Resolution**:
```bash
# Check environment
echo $ENVIRONMENT  # Must be "production" or "staging" for JSON

# Force JSON logging
export ENVIRONMENT=production
poetry run uvicorn src.api.main:app

# Verify JSON format
tail -f app.log | jq .
```

#### 4. Metrics Not Exposed

**Symptom**: `/metrics` endpoint returns 404

**Resolution**:
```python
# Verify metrics endpoint is registered
from src.api.main import app

# Check routes
for route in app.routes:
    print(route.path)

# Metrics should be at /metrics
curl http://localhost:8000/metrics
```

#### 5. Health Checks Return 503

**Symptom**: /health/ready returns 503

**Diagnosis**:
```bash
# Check which component is failing
curl -i http://localhost:8000/health/ready

# Look for X-Olumi-Degraded header
# X-Olumi-Degraded: database,redis

# Check detailed metrics
curl http://localhost:8000/health/metrics | jq .
```

**Resolution**:
```bash
# Database issue
# Verify PostgreSQL is running
pg_isready -h localhost -p 5432

# Redis issue
redis-cli ping

# Check connection strings
echo $DATABASE_URL
echo $REDIS_URL
```

---

## API Examples

### Core Alignment Session (Phase A-B)

```python
import httpx

# 1. Create alignment session
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/api/v1/sessions",
        json={
            "team_id": "team-123",
            "decision_topic": "Q2 Pricing Strategy",
            "decision_context": "Balance revenue growth with retention",
            "decision_type": "pricing",
            "alignment_mode": "evidence_backed",
            "stakeholders": [
                {"user_id": "user-1", "role": "PM", "name": "Alice"},
                {"user_id": "user-2", "role": "Designer", "name": "Bob"}
            ],
            "created_by": "user-1"
        },
        headers={"X-Request-ID": "test-123"}
    )
    session = response.json()
    session_id = session["session_id"]

# 2. Submit stakeholder profiles
for user_id in ["user-1", "user-2"]:
    await client.post(
        f"http://localhost:8000/api/v1/sessions/{session_id}/profiles",
        json={
            "user_id": user_id,
            "desired_outcome": "Maximize revenue while retaining customers",
            "key_concerns": ["churn risk", "competitive pricing"],
            "goal_weights": {"revenue_growth": 0.8, "customer_retention": 0.7}
        }
    )

# 3. Propose options
await client.post(
    f"http://localhost:8000/api/v1/sessions/{session_id}/options",
    json={
        "title": "Premium Positioning",
        "description": "Increase prices to position as premium product",
        "expected_outcome": "20% higher revenue per customer",
        "causal_rationale": "Premium pricing signals quality",
        "addresses_goals": ["revenue_growth"],
        "trade_offs": ["May increase churn by 5%"],
        "key_assumptions": [
            {"assumption_id": "a1", "assumption_text": "Customers value premium quality"}
        ]
    }
)

# 4. Calculate consensus
consensus = await client.post(
    f"http://localhost:8000/api/v1/sessions/{session_id}/calculate-consensus"
)
print(f"Consensus: {consensus.json()['consensus_level']}")
```

### Intelligent Assistance (Phase C)

```python
# AI-powered option generation
ai_options = await client.post(
    f"http://localhost:8000/api/v1/sessions/{session_id}/ai-options",
    json={
        "mode": "creative",  # creative, balanced, conservative
        "num_options": 3,
        "constraints": {
            "budget_max": 100000,
            "timeline_weeks": 12
        }
    }
)

# Synthesis hybrid options
synthesis = await client.post(
    f"http://localhost:8000/api/v1/sessions/{session_id}/synthesize",
    json={
        "option_ids": ["opt-1", "opt-2", "opt-3"],
        "synthesis_strategy": "best_of_each"
    }
)

# Decision retrospective
retrospective = await client.post(
    f"http://localhost:8000/api/v1/decisions/{decision_id}/retrospective",
    json={
        "actual_outcomes": {"revenue_growth": 0.18, "churn_rate": 0.06},
        "assumption_validations": [
            {
                "assumption_id": "a1",
                "validation_method": "a_b_test",
                "result": "confirmed"
            }
        ]
    }
)
```

### Organizational Intelligence (Phase D)

**D1: Portfolio Analytics**
```python
# Get portfolio health
portfolio = await client.get(
    f"http://localhost:8000/api/v1/analytics/portfolio/{org_id}"
)

# Identify bottlenecks
bottlenecks = await client.get(
    f"http://localhost:8000/api/v1/analytics/portfolio/{org_id}/bottlenecks"
)
```

**D3: Decision Dependencies**
```python
# Create dependency
await client.post(
    f"http://localhost:8000/api/v1/dependencies",
    json={
        "source_session_id": "session-1",
        "target_session_id": "session-2",
        "dependency_type": "blocks",
        "description": "Pricing must be decided before GTM strategy"
    }
)

# Get dependency graph
graph = await client.get(
    f"http://localhost:8000/api/v1/dependencies/graph/{org_id}"
)
```

**D4: Pattern Analysis**
```python
# Analyze patterns
patterns = await client.get(
    f"http://localhost:8000/api/v1/analytics/patterns/{org_id}",
    params={"decision_type": "pricing", "pattern_type": "success"}
)
```

**D6: Cross-Team Coordination**
```python
# Create coordination group
group = await client.post(
    f"http://localhost:8000/api/v1/coordination/groups",
    json={
        "name": "Q3 Strategic Initiatives",
        "session_ids": ["session-1", "session-2", "session-3"]
    }
)

# Detect conflicts
conflicts = await client.get(
    f"http://localhost:8000/api/v1/coordination/conflicts/{org_id}"
)
```

### PLoT Integration

```python
# PLoT requests alignment data
plot_response = await client.post(
    "http://localhost:8000/api/v1/plot/alignment-session",
    json={
        "session_id": "session-123",
        "organization_id": "org-456",
        "capabilities": ["core_alignment", "d3_dependencies", "d4_patterns"]
    },
    headers={"X-API-Key": "plot-internal-key"}
)
```

---

## OpenTelemetry Setup

### Installation

```bash
pip install opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation-fastapi
```

### Configuration

```python
# src/config/tracing.py
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentation

def configure_tracing(app):
    """Configure OpenTelemetry distributed tracing."""

    # Set up tracer provider
    provider = TracerProvider()
    processor = BatchSpanProcessor(OTLPSpanExporter(
        endpoint="http://jaeger:4317",
        insecure=True
    ))
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    # Instrument FastAPI
    FastAPIInstrumentation.instrument_app(app)

    return provider

# In main.py
from src.config.tracing import configure_tracing
configure_tracing(app)
```

### Usage in Code

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

async def validate_option(option_id: str):
    with tracer.start_as_current_span("validate_option") as span:
        span.set_attribute("option_id", option_id)

        # Call ISL
        with tracer.start_as_current_span("isl_validate"):
            result = await isl_client.validate(option)

        span.set_attribute("is_identifiable", result["is_identifiable"])
        return result
```

---

**End of Phase 4 Complete Guide**
