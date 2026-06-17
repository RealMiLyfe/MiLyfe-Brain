# Load Tests

Performance and load testing for MiLyfe Brain.

## Tools

### Locust (Python)

Best for: development, CI/CD quick tests, custom logic.

```bash
# Install
pip install locust

# Interactive mode (web UI at http://localhost:8089)
cd tests/load
locust -f locustfile.py --host=http://localhost:8200

# Headless mode (CI)
locust -f locustfile.py --headless \
  -u 50 -r 5 --run-time 300s \
  --host=http://localhost:8200 \
  --csv=results/locust
```

### k6 (Go)

Best for: production load tests, CI/CD, complex scenarios.

```bash
# Install (macOS)
brew install k6

# Run all scenarios
cd tests/load
k6 run k6_test.js

# Run with custom settings
k6 run --vus 100 --duration 5m k6_test.js

# Run specific scenario
k6 run --env BASE_URL=https://staging.milyfe.ai k6_test.js

# Export results
k6 run --out csv=results/k6.csv k6_test.js
```

## Scenarios

| Scenario | VUs | Duration | Purpose |
|----------|-----|----------|---------|
| Smoke | 1 | 30s | Verify system works |
| Load | 20-50 | 8min | Normal traffic |
| Stress | 100-200 | 3.5min | Beyond normal capacity |
| Spike | 300 | 50s | Sudden burst |

## Thresholds

| Metric | Target |
|--------|--------|
| p95 response time | < 2s |
| p99 response time | < 5s |
| Error rate | < 5% |
| Health check p95 | < 500ms |
| Chat response p95 | < 30s |

## CI Integration

Load tests run automatically in the staging CD pipeline after deployment:
- Locust: 10 users, 60s burst (quick validation)
- k6: Full scenario suite (on-demand or weekly)
