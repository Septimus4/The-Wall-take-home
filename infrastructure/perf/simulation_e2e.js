import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Counter, Trend } from 'k6/metrics';
import { uuidv4 } from 'https://jslib.k6.io/k6-utils/1.4.0/index.js';

// Custom metrics
export let errorRate = new Rate('errors');
export let endToEndLatency = new Trend('end_to_end_latency');
export let simulationsCompleted = new Counter('simulations_completed');

export let options = {
  stages: [
    { duration: '30s', target: 5 },   // Start slowly
    { duration: '2m', target: 10 },   // Normal load
    { duration: '2m', target: 15 },   // Peak load
    { duration: '30s', target: 5 },   // Cool down
  ],
  thresholds: {
    end_to_end_latency: ['p95<5000'],     // 95% under 5 seconds
    http_req_failed: ['rate<0.01'],       // Error rate under 1%
    errors: ['rate<0.01'],
    simulations_completed: ['count>50'],   // At least 50 complete simulations
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const MAX_WAIT_TIME = 30000; // Maximum wait time for simulation (30 seconds)

export default function() {
  const profileId = uuidv4();
  const height = 10 + Math.random() * 20; // Height between 10-30 meters

  const startTime = Date.now();

  // Step 1: Create profile
  const profilePayload = JSON.stringify({
    profile_id: profileId,
    height: height.toFixed(2),
  });

  const createResponse = http.post(
    `${BASE_URL}/api/profiles/`,
    profilePayload,
    {
      headers: { 'Content-Type': 'application/json' },
      tags: { name: 'create_profile' },
    }
  );

  const createSuccess = check(createResponse, {
    'Profile created successfully': (r) => r.status === 201,
    'Profile has correct ID': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.profile_id === profileId;
      } catch (e) {
        return false;
      }
    }
  });

  if (!createSuccess) {
    errorRate.add(1);
    console.log(`Failed to create profile ${profileId}: ${createResponse.status}`);
    return;
  }

  // Step 2: Start simulation
  const startSimResponse = http.post(
    `${BASE_URL}/api/profiles/${profileId}/start-simulation/`,
    '',
    { tags: { name: 'start_simulation' } }
  );

  const startSuccess = check(startSimResponse, {
    'Simulation started successfully': (r) => r.status === 200,
  });

  if (!startSuccess) {
    errorRate.add(1);
    console.log(`Failed to start simulation for ${profileId}: ${startSimResponse.status}`);
    return;
  }

  // Step 3: Poll for completion (wait for cost calculation)
  let costCalculated = false;
  let attempts = 0;
  const maxAttempts = 30; // 30 attempts with 1 second intervals = 30 seconds max

  while (!costCalculated && attempts < maxAttempts) {
    sleep(1); // Wait 1 second between checks
    attempts++;

    const checkResponse = http.get(
      `${BASE_URL}/api/profiles/${profileId}/`,
      { tags: { name: 'check_progress' } }
    );

    if (checkResponse.status === 200) {
      try {
        const profile = JSON.parse(checkResponse.body);
        if (profile.total_cost !== null && profile.total_cost > 0) {
          costCalculated = true;
          const endTime = Date.now();
          const totalLatency = endTime - startTime;

          endToEndLatency.add(totalLatency);
          simulationsCompleted.add(1);

          const finalSuccess = check(null, {
            'Cost calculated within time limit': () => totalLatency < MAX_WAIT_TIME,
            'Cost is positive number': () => profile.total_cost > 0,
            'End-to-end latency acceptable': () => totalLatency < 5000,
          });

          if (!finalSuccess) {
            errorRate.add(1);
          }

          break;
        }
      } catch (e) {
        console.log(`Error parsing response for ${profileId}: ${e}`);
      }
    }
  }

  if (!costCalculated) {
    errorRate.add(1);
    console.log(`Simulation for ${profileId} did not complete within ${MAX_WAIT_TIME}ms`);
  }

  // Brief pause before next iteration
  sleep(0.5);
}

export function handleSummary(data) {
  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
    'benchmarks/results/simulation_e2e_summary.json': JSON.stringify(data),
    'benchmarks/results/simulation_e2e_summary.html': htmlReport(data),
  };
}

function textSummary(data, options = {}) {
  const indent = options.indent || '';

  return `
${indent}End-to-End Simulation Test Summary
${indent}==================================
${indent}
${indent}Virtual Users: ${data.metrics.vus.values.max}
${indent}Duration: ${Math.round(data.state.testRunDurationMs / 1000)}s
${indent}
${indent}HTTP Metrics:
${indent}  Total Requests: ${data.metrics.http_reqs.values.count}
${indent}  Requests/sec: ${data.metrics.http_reqs.values.rate.toFixed(2)}
${indent}  Failed Requests: ${data.metrics.http_req_failed.values.rate.toFixed(4)}%
${indent}
${indent}End-to-End Performance:
${indent}  Simulations Completed: ${data.metrics.simulations_completed.values.count}
${indent}  Average E2E Latency: ${data.metrics.end_to_end_latency.values.avg.toFixed(0)}ms
${indent}  p90 E2E Latency: ${data.metrics.end_to_end_latency.values['p(90)'].toFixed(0)}ms
${indent}  p95 E2E Latency: ${data.metrics.end_to_end_latency.values['p(95)'].toFixed(0)}ms
${indent}  p99 E2E Latency: ${data.metrics.end_to_end_latency.values['p(99)'].toFixed(0)}ms
${indent}
${indent}Thresholds:
${indent}  ✓ p95 E2E < 5s: ${data.metrics.end_to_end_latency.values['p(95)'] < 5000 ? 'PASS' : 'FAIL'}
${indent}  ✓ Error rate < 1%: ${data.metrics.http_req_failed.values.rate < 0.01 ? 'PASS' : 'FAIL'}
${indent}  ✓ Simulations > 50: ${data.metrics.simulations_completed.values.count > 50 ? 'PASS' : 'FAIL'}
`;
}

function htmlReport(data) {
  return `
<!DOCTYPE html>
<html>
<head>
    <title>End-to-End Simulation Test Report</title>
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
    <h1>End-to-End Simulation Test Report</h1>
    <p><strong>Generated:</strong> ${new Date().toISOString()}</p>

    <h2>Test Configuration</h2>
    <table>
        <tr><td>Virtual Users (max)</td><td>${data.metrics.vus.values.max}</td></tr>
        <tr><td>Duration</td><td>${Math.round(data.state.testRunDurationMs / 1000)}s</td></tr>
        <tr><td>Total Requests</td><td>${data.metrics.http_reqs.values.count}</td></tr>
        <tr><td>Simulations Completed</td><td>${data.metrics.simulations_completed.values.count}</td></tr>
    </table>

    <h2>End-to-End Performance</h2>
    <table>
        <tr><th>Metric</th><th>Value</th><th>Threshold</th><th>Status</th></tr>
        <tr>
            <td>Average E2E Latency</td>
            <td>${data.metrics.end_to_end_latency.values.avg.toFixed(0)}ms</td>
            <td>≤5000ms (avg)</td>
            <td class="${data.metrics.end_to_end_latency.values.avg <= 5000 ? 'pass' : 'fail'}">${data.metrics.end_to_end_latency.values.avg <= 5000 ? 'PASS' : 'FAIL'}</td>
        </tr>
        <tr>
            <td>p95 E2E Latency</td>
            <td>${data.metrics.end_to_end_latency.values['p(95)'].toFixed(0)}ms</td>
            <td>≤5000ms</td>
            <td class="${data.metrics.end_to_end_latency.values['p(95)'] <= 5000 ? 'pass' : 'fail'}">${data.metrics.end_to_end_latency.values['p(95)'] <= 5000 ? 'PASS' : 'FAIL'}</td>
        </tr>
        <tr>
            <td>Success Rate</td>
            <td>${((data.metrics.simulations_completed.values.count / (data.metrics.simulations_completed.values.count + data.metrics.errors.values.count)) * 100).toFixed(1)}%</td>
            <td>≥99%</td>
            <td class="${data.metrics.http_req_failed.values.rate <= 0.01 ? 'pass' : 'fail'}">${data.metrics.http_req_failed.values.rate <= 0.01 ? 'PASS' : 'FAIL'}</td>
        </tr>
        <tr>
            <td>Simulations Completed</td>
            <td>${data.metrics.simulations_completed.values.count}</td>
            <td>≥50</td>
            <td class="${data.metrics.simulations_completed.values.count >= 50 ? 'pass' : 'fail'}">${data.metrics.simulations_completed.values.count >= 50 ? 'PASS' : 'FAIL'}</td>
        </tr>
    </table>
</body>
</html>`;
}
