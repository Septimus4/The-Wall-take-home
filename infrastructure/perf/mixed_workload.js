import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Counter, Trend } from 'k6/metrics';
import { uuidv4 } from 'https://jslib.k6.io/k6-utils/1.4.0/index.js';

// Custom metrics
export let errorRate = new Rate('errors');
export let readRequests = new Counter('read_requests');
export let writeRequests = new Counter('write_requests');
export let simulationRequests = new Counter('simulation_requests');

export let options = {
  stages: [
    { duration: '1m', target: 10 },   // Ramp up
    { duration: '5m', target: 20 },   // Normal mixed load
    { duration: '2m', target: 30 },   // Peak mixed load
    { duration: '1m', target: 20 },   // Back to normal
    { duration: '1m', target: 0 },    // Cool down
  ],
  thresholds: {
    http_req_duration: ['p95<300'],   // 95% under 300ms (mixed workload)
    http_req_failed: ['rate<0.01'],   // Error rate under 1%
    errors: ['rate<0.01'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

// Store created profile IDs for read operations
let createdProfiles = [];

export default function() {
  // Weighted random selection of operations
  const random = Math.random();

  if (random < 0.6) {
    // 60% - Read operations (GET requests)
    performReadOperation();
  } else if (random < 0.9) {
    // 30% - Write operations (POST requests)
    performWriteOperation();
  } else {
    // 10% - Simulation operations
    performSimulationOperation();
  }

  // Random pause between operations
  sleep(Math.random() * 2 + 0.5);
}

function performReadOperation() {
  let endpoint;
  let tags = { name: 'read_operation' };

  // Choose read endpoint randomly
  const readType = Math.random();

  if (readType < 0.4 || createdProfiles.length === 0) {
    // List all profiles
    endpoint = `${BASE_URL}/api/profiles/`;
    tags.endpoint = 'list_profiles';
  } else if (readType < 0.7) {
    // Get specific profile
    const profileId = createdProfiles[Math.floor(Math.random() * createdProfiles.length)];
    endpoint = `${BASE_URL}/api/profiles/${profileId}/`;
    tags.endpoint = 'get_profile';
  } else if (readType < 0.9) {
    // Get simulation runs
    const profileId = createdProfiles[Math.floor(Math.random() * createdProfiles.length)];
    endpoint = `${BASE_URL}/api/profiles/${profileId}/simulations/`;
    tags.endpoint = 'get_simulations';
  } else {
    // Get overview
    endpoint = `${BASE_URL}/api/overview/`;
    tags.endpoint = 'get_overview';
  }

  const response = http.get(endpoint, { tags });

  const success = check(response, {
    'Read request successful': (r) => r.status === 200 || r.status === 404,
    'Response time acceptable': (r) => r.timings.duration < 200,
    'Has valid JSON response': (r) => {
      try {
        JSON.parse(r.body);
        return true;
      } catch (e) {
        return false;
      }
    },
  });

  readRequests.add(1);

  if (!success) {
    errorRate.add(1);
    console.log(`Read operation failed: ${response.status} ${endpoint}`);
  }
}

function performWriteOperation() {
  const profileId = uuidv4();
  const height = Math.random() * 30;

  const payload = JSON.stringify({
    profile_id: profileId,
    height: height.toFixed(2),
  });

  const response = http.post(
    `${BASE_URL}/api/profiles/`,
    payload,
    {
      headers: { 'Content-Type': 'application/json' },
      tags: { name: 'write_operation', endpoint: 'create_profile' },
    }
  );

  const success = check(response, {
    'Write request successful': (r) => r.status === 201,
    'Response has profile data': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.profile_id === profileId;
      } catch (e) {
        return false;
      }
    },
    'Response time acceptable': (r) => r.timings.duration < 500,
  });

  writeRequests.add(1);

  if (success) {
    // Store profile ID for future read operations
    createdProfiles.push(profileId);
    // Keep array size manageable
    if (createdProfiles.length > 100) {
      createdProfiles = createdProfiles.slice(-50);
    }
  } else {
    errorRate.add(1);
    console.log(`Write operation failed: ${response.status} ${response.body}`);
  }
}

function performSimulationOperation() {
  if (createdProfiles.length === 0) {
    // Can't perform simulation without profiles, do a write instead
    performWriteOperation();
    return;
  }

  const profileId = createdProfiles[Math.floor(Math.random() * createdProfiles.length)];

  // Randomly choose start or stop simulation
  const action = Math.random() < 0.8 ? 'start' : 'stop';
  const endpoint = `${BASE_URL}/api/profiles/${profileId}/${action}-simulation/`;

  const response = http.post(endpoint, '', {
    tags: { name: 'simulation_operation', endpoint: `${action}_simulation` },
  });

  const success = check(response, {
    'Simulation request successful': (r) => r.status === 200 || r.status === 400, // 400 might be valid (already running/stopped)
    'Response time acceptable': (r) => r.timings.duration < 300,
    'Has valid response': (r) => {
      try {
        JSON.parse(r.body);
        return true;
      } catch (e) {
        return false;
      }
    },
  });

  simulationRequests.add(1);

  if (!success && response.status >= 500) {
    errorRate.add(1);
    console.log(`Simulation operation failed: ${response.status} ${endpoint}`);
  }
}

export function handleSummary(data) {
  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
    'benchmarks/results/mixed_workload_summary.json': JSON.stringify(data),
    'benchmarks/results/mixed_workload_summary.html': htmlReport(data),
  };
}

function textSummary(data, options = {}) {
  const indent = options.indent || '';

  const totalRequests = data.metrics.read_requests.values.count +
                       data.metrics.write_requests.values.count +
                       data.metrics.simulation_requests.values.count;

  return `
${indent}Mixed Workload Test Summary
${indent}==========================
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
${indent}Operation Breakdown:
${indent}  Read Operations: ${data.metrics.read_requests.values.count} (${((data.metrics.read_requests.values.count / totalRequests) * 100).toFixed(1)}%)
${indent}  Write Operations: ${data.metrics.write_requests.values.count} (${((data.metrics.write_requests.values.count / totalRequests) * 100).toFixed(1)}%)
${indent}  Simulation Operations: ${data.metrics.simulation_requests.values.count} (${((data.metrics.simulation_requests.values.count / totalRequests) * 100).toFixed(1)}%)
${indent}
${indent}Thresholds:
${indent}  ✓ p95 < 300ms: ${data.metrics.http_req_duration.values['p(95)'] < 300 ? 'PASS' : 'FAIL'}
${indent}  ✓ Error rate < 1%: ${data.metrics.http_req_failed.values.rate < 0.01 ? 'PASS' : 'FAIL'}
`;
}

function htmlReport(data) {
  const totalRequests = data.metrics.read_requests.values.count +
                       data.metrics.write_requests.values.count +
                       data.metrics.simulation_requests.values.count;

  return `
<!DOCTYPE html>
<html>
<head>
    <title>Mixed Workload Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .metric { margin: 10px 0; }
        .pass { color: green; }
        .fail { color: red; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .chart-container { margin: 20px 0; }
    </style>
</head>
<body>
    <h1>Mixed Workload Test Report</h1>
    <p><strong>Generated:</strong> ${new Date().toISOString()}</p>

    <h2>Test Configuration</h2>
    <table>
        <tr><td>Virtual Users (max)</td><td>${data.metrics.vus.values.max}</td></tr>
        <tr><td>Duration</td><td>${Math.round(data.state.testRunDurationMs / 1000)}s</td></tr>
        <tr><td>Total Requests</td><td>${data.metrics.http_reqs.values.count}</td></tr>
        <tr><td>Requests per second</td><td>${data.metrics.http_reqs.values.rate.toFixed(2)}</td></tr>
    </table>

    <h2>Performance Metrics</h2>
    <table>
        <tr><th>Metric</th><th>Value</th><th>Threshold</th><th>Status</th></tr>
        <tr>
            <td>Average Response Time</td>
            <td>${data.metrics.http_req_duration.values.avg.toFixed(2)}ms</td>
            <td>≤200ms (target)</td>
            <td class="${data.metrics.http_req_duration.values.avg <= 200 ? 'pass' : 'fail'}">${data.metrics.http_req_duration.values.avg <= 200 ? 'PASS' : 'WARN'}</td>
        </tr>
        <tr>
            <td>p95 Response Time</td>
            <td>${data.metrics.http_req_duration.values['p(95)'].toFixed(2)}ms</td>
            <td>≤300ms</td>
            <td class="${data.metrics.http_req_duration.values['p(95)'] <= 300 ? 'pass' : 'fail'}">${data.metrics.http_req_duration.values['p(95)'] <= 300 ? 'PASS' : 'FAIL'}</td>
        </tr>
        <tr>
            <td>Error Rate</td>
            <td>${(data.metrics.http_req_failed.values.rate * 100).toFixed(2)}%</td>
            <td>≤1%</td>
            <td class="${data.metrics.http_req_failed.values.rate <= 0.01 ? 'pass' : 'fail'}">${data.metrics.http_req_failed.values.rate <= 0.01 ? 'PASS' : 'FAIL'}</td>
        </tr>
    </table>

    <h2>Operation Breakdown</h2>
    <table>
        <tr><th>Operation Type</th><th>Count</th><th>Percentage</th><th>Target</th></tr>
        <tr>
            <td>Read Operations</td>
            <td>${data.metrics.read_requests.values.count}</td>
            <td>${((data.metrics.read_requests.values.count / totalRequests) * 100).toFixed(1)}%</td>
            <td>~60%</td>
        </tr>
        <tr>
            <td>Write Operations</td>
            <td>${data.metrics.write_requests.values.count}</td>
            <td>${((data.metrics.write_requests.values.count / totalRequests) * 100).toFixed(1)}%</td>
            <td>~30%</td>
        </tr>
        <tr>
            <td>Simulation Operations</td>
            <td>${data.metrics.simulation_requests.values.count}</td>
            <td>${((data.metrics.simulation_requests.values.count / totalRequests) * 100).toFixed(1)}%</td>
            <td>~10%</td>
        </tr>
    </table>
</body>
</html>`;
}
