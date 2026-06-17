/**
 * MiLyfe Brain Load Tests using k6.
 *
 * Usage:
 *   k6 run k6_test.js
 *   k6 run --vus 50 --duration 5m k6_test.js
 *   k6 run --out csv=results.csv k6_test.js
 *
 * Environment variables:
 *   BASE_URL - Target URL (default: http://localhost:8200)
 *   API_KEY  - Optional API key
 */

import http from 'k6/http';
import { check, group, sleep, fail } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';
import { randomItem, randomIntBetween } from 'https://jslib.k6.io/k6-utils/1.4.0/index.js';

// ─── Custom Metrics ──────────────────────────────────────────────────

const errorRate = new Rate('errors');
const playbook_creation_time = new Trend('playbook_creation_time', true);
const chat_response_time = new Trend('chat_response_time', true);
const health_check_time = new Trend('health_check_time', true);

// ─── Configuration ───────────────────────────────────────────────────

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8200';
const API_KEY = __ENV.API_KEY || '';

const headers = {
  'Content-Type': 'application/json',
  ...(API_KEY ? { 'X-API-Key': API_KEY } : {}),
};

// ─── Test Scenarios ──────────────────────────────────────────────────

export const options = {
  scenarios: {
    // Smoke test: minimal load to verify system works
    smoke: {
      executor: 'constant-vus',
      vus: 1,
      duration: '30s',
      tags: { scenario: 'smoke' },
      exec: 'smokeTest',
    },

    // Load test: normal expected traffic
    load: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '1m', target: 20 },   // Ramp up
        { duration: '3m', target: 20 },   // Sustain
        { duration: '1m', target: 50 },   // Push higher
        { duration: '2m', target: 50 },   // Sustain peak
        { duration: '1m', target: 0 },    // Ramp down
      ],
      startTime: '35s',
      tags: { scenario: 'load' },
      exec: 'loadTest',
    },

    // Stress test: beyond normal capacity
    stress: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '30s', target: 100 },
        { duration: '1m', target: 100 },
        { duration: '30s', target: 200 },
        { duration: '1m', target: 200 },
        { duration: '30s', target: 0 },
      ],
      startTime: '9m',
      tags: { scenario: 'stress' },
      exec: 'stressTest',
    },

    // Spike test: sudden burst
    spike: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '10s', target: 300 },  // Instant spike
        { duration: '30s', target: 300 },  // Hold
        { duration: '10s', target: 0 },    // Drop
      ],
      startTime: '13m',
      tags: { scenario: 'spike' },
      exec: 'spikeTest',
    },
  },

  thresholds: {
    http_req_duration: ['p(95)<2000', 'p(99)<5000'],  // 95% under 2s, 99% under 5s
    http_req_failed: ['rate<0.05'],                    // Less than 5% errors
    errors: ['rate<0.1'],                              // Less than 10% custom errors
    health_check_time: ['p(95)<500'],                  // Health check fast
    chat_response_time: ['p(95)<30000'],               // Chat can be slow (LLM)
    playbook_creation_time: ['p(95)<3000'],            // Playbook creation
  },
};

// ─── Test Data ───────────────────────────────────────────────────────

const PLAYBOOK_TITLES = [
  'Build REST API', 'Create landing page', 'Write unit tests',
  'Refactor auth', 'Deploy staging', 'Generate docs',
  'Fix memory leak', 'Add error handling', 'Create migration',
  'Implement search',
];

const CHAT_MESSAGES = [
  'Explain how the agent swarm works',
  'What models are available?',
  'Help me debug this error',
  'Create a React component',
  'What playbooks ran today?',
];

// ─── Scenario Functions ──────────────────────────────────────────────

export function smokeTest() {
  group('Smoke - Health', () => {
    const res = http.get(`${BASE_URL}/health`, { headers });
    const success = check(res, {
      'status is 200': (r) => r.status === 200,
      'has status field': (r) => JSON.parse(r.body).status !== undefined,
    });
    errorRate.add(!success);
    health_check_time.add(res.timings.duration);
  });

  group('Smoke - List Playbooks', () => {
    const res = http.get(`${BASE_URL}/api/playbooks/`, { headers });
    check(res, { 'status is 200': (r) => r.status === 200 });
  });

  group('Smoke - Agent Roles', () => {
    const res = http.get(`${BASE_URL}/api/agents/roles`, { headers });
    check(res, { 'status is 200': (r) => r.status === 200 });
  });

  sleep(1);
}

export function loadTest() {
  // Mix of read and write operations
  const action = randomIntBetween(1, 10);

  if (action <= 3) {
    // 30% - Health check
    group('Load - Health', () => {
      const res = http.get(`${BASE_URL}/health`, { headers });
      check(res, { 'healthy': (r) => r.status === 200 });
      health_check_time.add(res.timings.duration);
    });
  } else if (action <= 6) {
    // 30% - Read operations
    group('Load - Read', () => {
      http.get(`${BASE_URL}/api/playbooks/`, { headers });
      http.get(`${BASE_URL}/api/agents/active`, { headers });
      http.get(`${BASE_URL}/api/queue/status`, { headers });
    });
  } else if (action <= 8) {
    // 20% - Create playbook
    group('Load - Create Playbook', () => {
      const payload = JSON.stringify({
        title: randomItem(PLAYBOOK_TITLES),
        description: `Load test - ${Date.now()}`,
        auto_execute: false,
      });
      const res = http.post(`${BASE_URL}/api/playbooks/`, payload, { headers });
      const success = check(res, {
        'created': (r) => r.status === 201 || r.status === 200,
      });
      errorRate.add(!success);
      playbook_creation_time.add(res.timings.duration);
    });
  } else {
    // 20% - Chat
    group('Load - Chat', () => {
      const payload = JSON.stringify({
        message: randomItem(CHAT_MESSAGES),
        session_id: `k6-${__VU}`,
      });
      const res = http.post(`${BASE_URL}/api/chat/send`, payload, {
        headers,
        timeout: '60s',
      });
      const success = check(res, {
        'chat ok': (r) => r.status === 200 || r.status === 503,
      });
      errorRate.add(!success && res.status !== 503);
      if (res.status === 200) {
        chat_response_time.add(res.timings.duration);
      }
    });
  }

  sleep(randomIntBetween(1, 3));
}

export function stressTest() {
  // Primarily read operations under high concurrency
  group('Stress - Reads', () => {
    const responses = http.batch([
      ['GET', `${BASE_URL}/health`, null, { headers }],
      ['GET', `${BASE_URL}/api/playbooks/`, null, { headers }],
      ['GET', `${BASE_URL}/api/agents/active`, null, { headers }],
      ['GET', `${BASE_URL}/api/queue/status`, null, { headers }],
      ['GET', `${BASE_URL}/api/notifications/`, null, { headers }],
    ]);

    for (const res of responses) {
      const success = check(res, {
        'not 5xx': (r) => r.status < 500,
      });
      errorRate.add(!success);
    }
  });

  sleep(randomIntBetween(0, 2));
}

export function spikeTest() {
  // Rapid health checks and list operations
  const res = http.get(`${BASE_URL}/health`, { headers });
  check(res, {
    'survives spike': (r) => r.status === 200 || r.status === 429,
  });
  health_check_time.add(res.timings.duration);

  sleep(0.1);
}

// ─── Lifecycle Hooks ─────────────────────────────────────────────────

export function handleSummary(data) {
  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
    'results/summary.json': JSON.stringify(data, null, 2),
  };
}

function textSummary(data, opts) {
  // k6 built-in summary handles this
  return '';
}
