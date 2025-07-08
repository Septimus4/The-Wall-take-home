import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Counter, Trend, Gauge } from 'k6/metrics';
import { uuidv4 } from 'https://jslib.k6.io/k6-utils/1.4.0/index.js';

// Custom metrics for comprehensive analysis
export let errorRate = new Rate('errors');
export let profilesCreated = new Counter('profiles_created');
export let simulationsStarted = new Counter('simulations_started');
export let taskEndpointsCalled = new Counter('task_endpoints_called');
export let responseTimeBreakdown = new Trend('response_time_breakdown');
export let databaseConnections = new Gauge('database_connections');
export let memoryUsage = new Gauge('memory_usage_mb');

export let options = {
  scenarios: {
    // Scenario 1: Profile creation load test
    profile_creation: {
      executor: 'ramping-vus',
      startVUs: 5,
      stages: [
        { duration: '30s', target: 15 },  // Warm up
        { duration: '1m', target: 30 },   // Normal load
        { duration: '30s', target: 50 },  // Peak load
        { duration: '1m', target: 30 },   // Back to normal
        { duration: '30s', target: 0 },   // Cool down
      ],
      exec: 'createProfiles',
      tags: { scenario: 'profile_creation' },
    },

    // Scenario 2: Task endpoint validation
    task_validation: {
      executor: 'shared-iterations',
      vus: 5,
      iterations: 50,
      maxDuration: '5m',
      exec: 'validateTaskEndpoints',
      tags: { scenario: 'task_validation' },
      startTime: '3m', // Start after profiles are created
    },

    // Scenario 3: Mixed operations
    mixed_operations: {
      executor: 'constant-vus',
      vus: 10,
      duration: '2m',
      exec: 'mixedOperations',
      tags: { scenario: 'mixed_operations' },
      startTime: '1m', // Start after some profiles exist
    },
  },

  thresholds: {
    // Overall performance thresholds
    'http_req_duration': ['p95<500'],
    'http_req_failed': ['rate<0.01'],
    'errors': ['rate<0.01'],

    // Scenario-specific thresholds
    'http_req_duration{scenario:profile_creation}': ['p95<300'],
    'http_req_duration{scenario:task_validation}': ['p95<200'],
    'http_req_duration{scenario:mixed_operations}': ['p95<400'],

    // Business logic thresholds
    'profiles_created': ['count>100'],
    'task_endpoints_called': ['count>40'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const API_URL = `${BASE_URL}/api/v1`;

// Store created profiles for reuse
let createdProfiles = [];

// Task-specific profiles based on the requirements
const taskProfiles = [
  {
    profile_id: 'task-profile-1-k6',
    name: 'Task Profile 1 - [21, 25, 28]',
    height: 21.0,
    sections: [21, 25, 28]
  },
  {
    profile_id: 'task-profile-2-k6',
    name: 'Task Profile 2 - [17]',
    height: 17.0,
    sections: [17]
  },
  {
    profile_id: 'task-profile-3-k6',
    name: 'Task Profile 3 - [17, 22, 17, 19, 17]',
    height: 17.0,
    sections: [17, 22, 17, 19, 17]
  }
];

export function createProfiles() {
  const profileId = uuidv4();

  // 20% chance to create a task-specific profile
  let profileData;
  if (Math.random() < 0.2 && taskProfiles.length > 0) {
    const taskProfile = taskProfiles[Math.floor(Math.random() * taskProfiles.length)];
    profileData = {
      profile_id: `${taskProfile.profile_id}-${__VU}-${__ITER}`,
      name: `${taskProfile.name} (VU${__VU})`,
      height: taskProfile.height,
      length: 50.0 + Math.random() * 200,
      width: 2.0 + Math.random() * 8,
      ice_thickness: 0.2 + Math.random() * 0.3
    };
  } else {
    // Create random profile
    const heights = [5.0, 10.0, 15.0, 20.0, 25.0, 30.0];
    profileData = {
      profile_id: profileId,
      name: `Benchmark Wall ${__VU}-${__ITER}`,
      height: heights[Math.floor(Math.random() * heights.length)],
      length: 50.0 + Math.random() * 200,
      width: 2.0 + Math.random() * 8,
      ice_thickness: 0.2 + Math.random() * 0.3
    };
  }

  const payload = JSON.stringify(profileData);
  const params = {
    headers: { 'Content-Type': 'application/json' },
    tags: {
      name: 'create_profile',
      profile_type: profileData.name.includes('Task') ? 'task' : 'random'
    },
  };

  const startTime = Date.now();
  const response = http.post(`${API_URL}/profiles/`, payload, params);
  const endTime = Date.now();

  responseTimeBreakdown.add(endTime - startTime);

  const success = check(response, {
    'Profile creation successful': (r) => r.status === 201 || r.status === 409, // 409 = already exists
    'Response has profile data': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.profile_id === profileData.profile_id || r.status === 409;
      } catch (e) {
        return false;
      }
    },
    'Response time acceptable': (r) => r.timings.duration < 1000,
    'No server errors': (r) => r.status < 500,
  });

  if (success && response.status === 201) {
    profilesCreated.add(1);
    createdProfiles.push(profileData.profile_id);

    // Keep array manageable
    if (createdProfiles.length > 200) {
      createdProfiles = createdProfiles.slice(-100);
    }
  } else if (!success) {
    errorRate.add(1);
    console.log(`Failed to create profile ${profileData.profile_id}: ${response.status}`);
  }

  // Simulate realistic user behavior
  sleep(Math.random() * 2 + 0.5);
}

export function validateTaskEndpoints() {
  const taskTests = [
    // Test the task-specific endpoints as per requirements
    { endpoint: '/profiles/overview/', expectedFields: ['total_cost', 'profiles'] },
    { endpoint: '/profiles/overview/1/', expectedFields: ['total_cost', 'profiles'] },
  ];

  // If we have created profiles, test specific profile endpoints
  if (createdProfiles.length > 0) {
    const profileId = createdProfiles[Math.floor(Math.random() * createdProfiles.length)];
    taskTests.push(
      { endpoint: `/profiles/${profileId}/days/1/`, expectedFields: ['ice_amount', 'cost'] },
      { endpoint: `/profiles/${profileId}/overview/1/`, expectedFields: ['cost', 'day'] }
    );
  }

  for (const test of taskTests) {
    const response = http.get(`${API_URL}${test.endpoint}`, {
      tags: {
        name: 'validate_task_endpoint',
        endpoint: test.endpoint
      }
    });

    const success = check(response, {
      'Task endpoint responds': (r) => r.status === 200,
      'Response time under 300ms': (r) => r.timings.duration < 300,
      'Response has expected fields': (r) => {
        if (r.status !== 200) return false;
        try {
          const data = JSON.parse(r.body);
          return test.expectedFields.every(field =>
            data.hasOwnProperty(field) ||
            (Array.isArray(data) && data.length > 0 && data[0].hasOwnProperty(field))
          );
        } catch (e) {
          return false;
        }
      },
      'Response contains valid data': (r) => {
        if (r.status !== 200) return false;
        try {
          const data = JSON.parse(r.body);
          return data !== null && typeof data === 'object';
        } catch (e) {
          return false;
        }
      }
    });

    taskEndpointsCalled.add(1);

    if (!success) {
      errorRate.add(1);
      console.log(`Task endpoint validation failed: ${test.endpoint} - ${response.status}`);
    }

    sleep(0.5); // Brief pause between endpoint tests
  }
}

export function mixedOperations() {
  const operation = Math.random();

  if (operation < 0.4) {
    // 40% - Read operations
    performReadOperation();
  } else if (operation < 0.7) {
    // 30% - Profile creation
    createProfiles();
  } else if (operation < 0.9) {
    // 20% - Simulation operations
    performSimulationOperation();
  } else {
    // 10% - Health checks and system endpoints
    performSystemOperation();
  }
}

function performReadOperation() {
  let endpoint;
  let tags = { name: 'read_operation' };

  const readType = Math.random();

  if (readType < 0.3 || createdProfiles.length === 0) {
    // List all profiles
    endpoint = `${API_URL}/profiles/`;
    tags.endpoint = 'list_profiles';
  } else if (readType < 0.6) {
    // Get specific profile
    const profileId = createdProfiles[Math.floor(Math.random() * createdProfiles.length)];
    endpoint = `${API_URL}/profiles/${profileId}/`;
    tags.endpoint = 'get_profile';
  } else if (readType < 0.8) {
    // Get day calculation
    const profileId = createdProfiles[Math.floor(Math.random() * createdProfiles.length)];
    const day = Math.floor(Math.random() * 10) + 1;
    endpoint = `${API_URL}/profiles/${profileId}/days/${day}/`;
    tags.endpoint = 'get_day_calculation';
  } else {
    // Get overview
    endpoint = `${API_URL}/profiles/overview/`;
    tags.endpoint = 'get_overview';
  }

  const response = http.get(endpoint, { tags });

  check(response, {
    'Read operation successful': (r) => r.status === 200 || r.status === 404,
    'Read response time acceptable': (r) => r.timings.duration < 300,
    'Valid JSON response': (r) => {
      try {
        JSON.parse(r.body);
        return true;
      } catch (e) {
        return false;
      }
    },
  });
}

function performSimulationOperation() {
  if (createdProfiles.length === 0) {
    // No profiles to simulate, create one instead
    createProfiles();
    return;
  }

  const profileId = createdProfiles[Math.floor(Math.random() * createdProfiles.length)];
  const action = Math.random() < 0.8 ? 'start' : 'stop';
  const endpoint = `${API_URL}/profiles/${profileId}/${action}-simulation/`;

  const response = http.post(endpoint, '', {
    tags: {
      name: 'simulation_operation',
      action: action
    }
  });

  const success = check(response, {
    'Simulation operation completed': (r) => r.status === 200 || r.status === 400,
    'Simulation response time acceptable': (r) => r.timings.duration < 500,
  });

  if (success && action === 'start') {
    simulationsStarted.add(1);
  }
}

function performSystemOperation() {
  const operations = [
    { url: `${BASE_URL}/health/`, name: 'health_check' },
    { url: `${API_URL}/profiles/overview/`, name: 'system_overview' },
  ];

  const operation = operations[Math.floor(Math.random() * operations.length)];

  const response = http.get(operation.url, {
    tags: {
      name: 'system_operation',
      operation: operation.name
    }
  });

  check(response, {
    'System operation successful': (r) => r.status === 200,
    'System response time acceptable': (r) => r.timings.duration < 200,
  });
}

export function handleSummary(data) {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');

  // Generate detailed JSON report
  const report = {
    timestamp: new Date().toISOString(),
    test_configuration: {
      base_url: BASE_URL,
      scenarios: Object.keys(options.scenarios),
      thresholds: options.thresholds
    },
    metrics: {
      http_requests: {
        count: data.metrics.http_reqs.values.count,
        rate: data.metrics.http_reqs.values.rate
      },
      response_times: {
        avg: data.metrics.http_req_duration.values.avg,
        p95: data.metrics.http_req_duration.values['p(95)'],
        p99: data.metrics.http_req_duration.values['p(99)']
      },
      error_rate: data.metrics.http_req_failed.values.rate,
      custom_metrics: {
        profiles_created: data.metrics.profiles_created?.values.count || 0,
        simulations_started: data.metrics.simulations_started?.values.count || 0,
        task_endpoints_called: data.metrics.task_endpoints_called?.values.count || 0
      }
    },
    scenarios: {}
  };

  // Add scenario-specific metrics
  for (const scenario of Object.keys(options.scenarios)) {
    const scenarioMetrics = {};
    for (const [key, metric] of Object.entries(data.metrics)) {
      if (metric.values && metric.tags && metric.tags.scenario === scenario) {
        scenarioMetrics[key] = metric.values;
      }
    }
    report.scenarios[scenario] = scenarioMetrics;
  }

  return {
    'benchmarks/results/comprehensive_benchmark_' + timestamp + '.json': JSON.stringify(report, null, 2),
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
  };
}

function textSummary(data, options = {}) {
  const indent = options.indent || '';

  return `
${indent}The Wall Comprehensive Benchmark Report
${indent}=====================================
${indent}
${indent}Test Configuration:
${indent}  Base URL: ${BASE_URL}
${indent}  Scenarios: ${Object.keys(options.scenarios || {}).join(', ')}
${indent}  Duration: ${Math.round(data.state.testRunDurationMs / 1000)}s
${indent}
${indent}Overall Performance:
${indent}  Total Requests: ${data.metrics.http_reqs.values.count}
${indent}  Requests/sec: ${data.metrics.http_reqs.values.rate.toFixed(2)}
${indent}  Failed Requests: ${(data.metrics.http_req_failed.values.rate * 100).toFixed(2)}%
${indent}
${indent}Response Times:
${indent}  Average: ${data.metrics.http_req_duration.values.avg.toFixed(2)}ms
${indent}  90th percentile: ${data.metrics.http_req_duration.values['p(90)'].toFixed(2)}ms
${indent}  95th percentile: ${data.metrics.http_req_duration.values['p(95)'].toFixed(2)}ms
${indent}  99th percentile: ${data.metrics.http_req_duration.values['p(99)'].toFixed(2)}ms
${indent}
${indent}Business Metrics:
${indent}  Profiles Created: ${data.metrics.profiles_created?.values.count || 0}
${indent}  Simulations Started: ${data.metrics.simulations_started?.values.count || 0}
${indent}  Task Endpoints Called: ${data.metrics.task_endpoints_called?.values.count || 0}
${indent}
${indent}Threshold Status:
${Object.entries(data.metrics).map(([name, metric]) => {
  if (metric.thresholds) {
    return Object.entries(metric.thresholds).map(([threshold, result]) =>
      `${indent}  ${name} ${threshold}: ${result.ok ? '✅ PASS' : '❌ FAIL'}`
    ).join('\n');
  }
  return '';
}).filter(Boolean).join('\n')}
`;
}
