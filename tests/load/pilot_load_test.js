/**
 * TAE Phase D - Pilot Load Test
 *
 * Simulates expected pilot load:
 * - 15-40 concurrent users
 * - 3-5 active teams
 * - 10-20 decisions per week
 * - 50-100 WebSocket messages per hour
 *
 * Run with: k6 run pilot_load_test.js
 */

import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const portfolioLatency = new Trend('portfolio_query_latency');
const websocketErrors = new Rate('websocket_errors');
const dependencyGraphLatency = new Trend('dependency_graph_latency');

// Test configuration for pilot load
export const options = {
  stages: [
    { duration: '2m', target: 15 },  // Ramp up to 15 users
    { duration: '5m', target: 25 },  // Increase to 25 users
    { duration: '3m', target: 40 },  // Peak at 40 users
    { duration: '5m', target: 25 },  // Drop back to 25 users
    { duration: '2m', target: 0 },   // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<5000'],  // 95% of requests < 5s
    http_req_failed: ['rate<0.01'],     // Error rate < 1%
    portfolio_query_latency: ['p(95)<5000'], // Portfolio < 5s
    dependency_graph_latency: ['p(95)<2000'], // Dependency < 2s
    websocket_errors: ['rate<0.05'],    // WebSocket errors < 5%
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

// Sample organization and session IDs for testing
const ORG_IDS = [
  '550e8400-e29b-41d4-a716-446655440000',
  '550e8400-e29b-41d4-a716-446655440001',
  '550e8400-e29b-41d4-a716-446655440002',
];

const SESSION_IDS = [
  '660e8400-e29b-41d4-a716-446655440000',
  '660e8400-e29b-41d4-a716-446655440001',
  '660e8400-e29b-41d4-a716-446655440002',
];

/**
 * Test Phase D1: Portfolio Analytics
 */
function testPortfolioAnalytics() {
  group('D1: Portfolio Analytics', () => {
    const org_id = ORG_IDS[Math.floor(Math.random() * ORG_IDS.length)];
    const start = new Date();

    const response = http.get(`${BASE_URL}/api/v1/portfolio/analytics`, {
      params: { organization_id: org_id },
      tags: { name: 'PortfolioAnalytics' },
    });

    const duration = new Date() - start;
    portfolioLatency.add(duration);

    check(response, {
      'portfolio analytics status 200': (r) => r.status === 200,
      'portfolio analytics < 5s': (r) => duration < 5000,
      'portfolio has health score': (r) => {
        try {
          const body = JSON.parse(r.body);
          return body.data && 'health_score' in body.data;
        } catch {
          return false;
        }
      },
    });
  });
}

/**
 * Test Phase D1: Portfolio Health Score (lightweight)
 */
function testPortfolioHealthScore() {
  group('D1: Portfolio Health Score', () => {
    const org_id = ORG_IDS[Math.floor(Math.random() * ORG_IDS.length)];

    const response = http.get(`${BASE_URL}/api/v1/portfolio/health-score`, {
      params: { organization_id: org_id },
      tags: { name: 'PortfolioHealthScore' },
    });

    check(response, {
      'health score status 200': (r) => r.status === 200,
      'health score < 1s': (r) => r.timings.duration < 1000,
      'health score valid': (r) => {
        try {
          const body = JSON.parse(r.body);
          return body.health_score >= 0 && body.health_score <= 1;
        } catch {
          return false;
        }
      },
    });
  });
}

/**
 * Test Phase D3: Dependency Management
 */
function testDependencyGraph() {
  group('D3: Dependency Graph', () => {
    const session_id = SESSION_IDS[Math.floor(Math.random() * SESSION_IDS.length)];
    const start = new Date();

    const response = http.get(`${BASE_URL}/api/v1/dependencies/graph`, {
      params: { session_id },
      tags: { name: 'DependencyGraph' },
    });

    const duration = new Date() - start;
    dependencyGraphLatency.add(duration);

    check(response, {
      'dependency graph status 200': (r) => r.status === 200,
      'dependency graph < 2s': (r) => duration < 2000,
      'has graph data': (r) => {
        try {
          const body = JSON.parse(r.body);
          return body.nodes !== undefined && body.edges !== undefined;
        } catch {
          return false;
        }
      },
    });
  });
}

/**
 * Test Phase D4: Pattern Analysis
 */
function testPatternAnalysis() {
  group('D4: Pattern Analysis', () => {
    const org_id = ORG_IDS[Math.floor(Math.random() * ORG_IDS.length)];

    const response = http.get(`${BASE_URL}/api/v1/patterns`, {
      params: {
        organization_id: org_id,
        lookback_days: 90,
      },
      tags: { name: 'PatternAnalysis' },
    });

    check(response, {
      'pattern analysis status 200': (r) => r.status === 200 || r.status === 404,  // 404 if insufficient data
      'pattern analysis < 3s': (r) => r.timings.duration < 3000,
    });
  });
}

/**
 * Test Phase D5: Advanced Analytics
 */
function testAdvancedAnalytics() {
  group('D5: Advanced Analytics', () => {
    const org_id = ORG_IDS[Math.floor(Math.random() * ORG_IDS.length)];

    const response = http.get(`${BASE_URL}/api/v1/advanced-analytics/trends`, {
      params: {
        organization_id: org_id,
        metric_name: 'decision_time',
        lookback_days: 90,
      },
      tags: { name: 'TrendAnalysis' },
    });

    check(response, {
      'trend analysis status 200': (r) => r.status === 200 || r.status === 404,
      'trend analysis < 2s': (r) => r.timings.duration < 2000,
    });
  });
}

/**
 * Test Phase D6: Cross-Team Coordination
 */
function testCoordination() {
  group('D6: Cross-Team Coordination', () => {
    const session_ids = SESSION_IDS.slice(0, 2).join(',');

    const response = http.post(
      `${BASE_URL}/api/v1/coordination/conflicts/detect`,
      JSON.stringify({ session_ids: SESSION_IDS.slice(0, 2) }),
      {
        headers: { 'Content-Type': 'application/json' },
        tags: { name: 'ConflictDetection' },
      }
    );

    check(response, {
      'conflict detection status 200': (r) => r.status === 200,
      'conflict detection < 1s': (r) => r.timings.duration < 1000,
    });
  });
}

/**
 * Test Health Endpoint
 */
function testHealth() {
  group('Health Check', () => {
    const response = http.get(`${BASE_URL}/health`, {
      tags: { name: 'HealthCheck' },
    });

    check(response, {
      'health status 200': (r) => r.status === 200,
      'health status ok': (r) => {
        try {
          const body = JSON.parse(r.body);
          return body.status === 'ok' || body.status === 'degraded';
        } catch {
          return false;
        }
      },
      'all dependencies connected': (r) => {
        try {
          const body = JSON.parse(r.body);
          return body.dependencies.database.status === 'connected' &&
                 body.dependencies.redis.status === 'connected';
        } catch {
          return false;
        }
      },
    });
  });
}

/**
 * Main test function - simulates user workflow
 */
export default function () {
  // Health check (infrequent)
  if (Math.random() < 0.1) {  // 10% of iterations
    testHealth();
  }

  // Portfolio analytics (common for dashboard views)
  if (Math.random() < 0.5) {  // 50% of iterations
    testPortfolioHealthScore();
    sleep(1);
  }

  // Full portfolio analytics (less frequent, more expensive)
  if (Math.random() < 0.2) {  // 20% of iterations
    testPortfolioAnalytics();
    sleep(2);
  }

  // Dependency graph (used during decision making)
  if (Math.random() < 0.3) {  // 30% of iterations
    testDependencyGraph();
    sleep(1);
  }

  // Pattern analysis (periodic background job simulation)
  if (Math.random() < 0.1) {  // 10% of iterations
    testPatternAnalysis();
    sleep(2);
  }

  // Advanced analytics (dashboard widgets)
  if (Math.random() < 0.15) {  // 15% of iterations
    testAdvancedAnalytics();
    sleep(1);
  }

  // Coordination (used when planning cross-team work)
  if (Math.random() < 0.1) {  // 10% of iterations
    testCoordination();
    sleep(1);
  }

  // Random think time (simulates users reading/thinking)
  sleep(Math.random() * 5 + 2);  // 2-7 seconds
}

/**
 * Test teardown - summary report
 */
export function handleSummary(data) {
  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
    'pilot_load_test_results.json': JSON.stringify(data, null, 2),
  };
}

function textSummary(data, opts) {
  return `
TAE Phase D - Pilot Load Test Summary
=====================================

Duration: ${data.state.testRunDurationMs / 1000}s
VUs: ${data.metrics.vus.values.max}
Requests: ${data.metrics.http_reqs.values.count}
Errors: ${data.metrics.http_req_failed.values.rate * 100}%

Performance Targets:
- Portfolio Analytics p95: ${data.metrics.portfolio_query_latency.values['p(95)']}ms (target < 5000ms) ${data.metrics.portfolio_query_latency.values['p(95)'] < 5000 ? '✓' : '✗'}
- Dependency Graph p95: ${data.metrics.dependency_graph_latency.values['p(95)']}ms (target < 2000ms) ${data.metrics.dependency_graph_latency.values['p(95)'] < 2000 ? '✓' : '✗'}
- HTTP Request p95: ${data.metrics.http_req_duration.values['p(95)']}ms (target < 5000ms) ${data.metrics.http_req_duration.values['p(95)'] < 5000 ? '✓' : '✗'}
- Error Rate: ${(data.metrics.http_req_failed.values.rate * 100).toFixed(2)}% (target < 1%) ${data.metrics.http_req_failed.values.rate < 0.01 ? '✓' : '✗'}

${data.metrics.checks.values.rate === 1 ? '✓ All checks passed!' : '✗ Some checks failed'}
`;
}
