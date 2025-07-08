import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Counter, Trend } from 'k6/metrics';
import { uuidv4 } from 'https://jslib.k6.io/k6-utils/1.4.0/index.js';

// Custom metrics
export let errorRate = new Rate('errors');
export let profilesCreated = new Counter('profiles_created');
export let responseTimeBreakdown = new Trend('response_time_breakdown');

export let options = {
  stages: [
    { duration: '30s', target: 10 },  // Warm up
    { duration: '1m', target: 25 },   // Normal load
    { duration: '30s', target: 50 },  // Peak load
    { duration: '30s', target: 25 },  // Back to normal
    { duration: '30s', target: 0 },   // Cool down
  ],
  thresholds: {
    http_req_duration: ['p95<250'],   // 95% of requests under 250ms
    http_req_failed: ['rate<0.01'],   // Error rate under 1%
    errors: ['rate<0.01'],            // Custom error rate under 1%
    profiles_created: ['count>1000'], // At least 1000 profiles created
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export default function() {
  // Generate random profile data
  const profileId = uuidv4();
  const height = Math.random() * 30; // Random height between 0-30 meters

  const payload = JSON.stringify({
    profile_id: profileId,
    height: height.toFixed(2),
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
    tags: { name: 'create_profile' },
  };

  // Create profile
  const startTime = Date.now();
  const response = http.post(`${BASE_URL}/api/profiles/`, payload, params);
  const endTime = Date.now();

  responseTimeBreakdown.add(endTime - startTime);

  const success = check(response, {
    'Profile creation successful': (r) => r.status === 201,
    'Response has profile_id': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.profile_id === profileId;
      } catch (e) {
        return false;
      }
    },
    'Response time acceptable': (r) => r.timings.duration < 500,
    'No server errors': (r) => r.status < 500,
  });

  if (success) {
    profilesCreated.add(1);
  } else {
    errorRate.add(1);
    console.log(`Failed to create profile ${profileId}: ${response.status} ${response.body}`);
  }

  // Wait between requests (simulates real user behavior)
  sleep(Math.random() * 2 + 0.5); // Random sleep between 0.5-2.5 seconds
}

export function handleSummary(data) {
  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
    'benchmarks/results/create_profiles_summary.json': JSON.stringify(data),
    'benchmarks/results/create_profiles_summary.html': htmlReport(data),
  };
}

function textSummary(data, options = {}) {
  const indent = options.indent || '';
  const colors = options.enableColors || false;

  return `
${indent}Profile Creation Load Test Summary
${indent}=====================================
${indent}
${indent}Virtual Users: ${data.metrics.vus.values.max}
${indent}Duration: ${Math.round(data.state.testRunDurationMs / 1000)}s
${indent}
${indent}HTTP Metrics:
${indent}  Total Requests: ${data.metrics.http_reqs.values.count}
${indent}  Requests/sec: ${data.metrics.http_reqs.values.rate.toFixed(2)}
${indent}  Failed Requests: ${data.metrics.http_req_failed.values.rate.toFixed(4)}%
${indent}
${indent}Response Times:
${indent}  Average: ${data.metrics.http_req_duration.values.avg.toFixed(2)}ms
${indent}  p90: ${data.metrics.http_req_duration.values['p(90)'].toFixed(2)}ms
${indent}  p95: ${data.metrics.http_req_duration.values['p(95)'].toFixed(2)}ms
${indent}  p99: ${data.metrics.http_req_duration.values['p(99)'].toFixed(2)}ms
${indent}
${indent}Custom Metrics:
${indent}  Profiles Created: ${data.metrics.profiles_created.values.count}
${indent}  Error Rate: ${(data.metrics.errors.values.rate * 100).toFixed(2)}%
${indent}
${indent}Thresholds:
${indent}  ✓ p95 < 250ms: ${data.metrics.http_req_duration.values['p(95)'] < 250 ? 'PASS' : 'FAIL'}
${indent}  ✓ Error rate < 1%: ${data.metrics.http_req_failed.values.rate < 0.01 ? 'PASS' : 'FAIL'}
${indent}  ✓ Profiles > 1000: ${data.metrics.profiles_created.values.count > 1000 ? 'PASS' : 'FAIL'}
`;
}

function htmlReport(data) {
  return `
<!DOCTYPE html>
<html>
<head>
    <title>Profile Creation Load Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .metric { margin: 10px 0; }
        .pass { color: green; }
        .fail { color: red; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <h1>Profile Creation Load Test Report</h1>
    <p><strong>Generated:</strong> ${new Date().toISOString()}</p>

    <h2>Test Configuration</h2>
    <table>
        <tr><td>Virtual Users (max)</td><td>${data.metrics.vus.values.max}</td></tr>
        <tr><td>Duration</td><td>${Math.round(data.state.testRunDurationMs / 1000)}s</td></tr>
        <tr><td>Total Requests</td><td>${data.metrics.http_reqs.values.count}</td></tr>
    </table>

    <h2>Performance Metrics</h2>
    <table>
        <tr><th>Metric</th><th>Value</th><th>Threshold</th><th>Status</th></tr>
        <tr>
            <td>Requests per second</td>
            <td>${data.metrics.http_reqs.values.rate.toFixed(2)}</td>
            <td>≥50</td>
            <td class="${data.metrics.http_reqs.values.rate >= 50 ? 'pass' : 'fail'}">${data.metrics.http_reqs.values.rate >= 50 ? 'PASS' : 'FAIL'}</td>
        </tr>
        <tr>
            <td>Response time p95</td>
            <td>${data.metrics.http_req_duration.values['p(95)'].toFixed(2)}ms</td>
            <td>≤250ms</td>
            <td class="${data.metrics.http_req_duration.values['p(95)'] <= 250 ? 'pass' : 'fail'}">${data.metrics.http_req_duration.values['p(95)'] <= 250 ? 'PASS' : 'FAIL'}</td>
        </tr>
        <tr>
            <td>Error rate</td>
            <td>${(data.metrics.http_req_failed.values.rate * 100).toFixed(2)}%</td>
            <td>≤1%</td>
            <td class="${data.metrics.http_req_failed.values.rate <= 0.01 ? 'pass' : 'fail'}">${data.metrics.http_req_failed.values.rate <= 0.01 ? 'PASS' : 'FAIL'}</td>
        </tr>
    </table>
</body>
</html>`;
}
