# The Wall Benchmark Tool

A comprehensive benchmark tool for testing The Wall construction management system. This tool creates realistic test profiles based on the task requirements and runs various performance tests to measure system capabilities.

## 🚀 Quick Start

### Prerequisites

1. **System Running**: Ensure The Wall system is running:
   ```bash
   docker compose up -d
   ```

2. **k6 Installed**: The tool uses k6 for load testing:
   ```bash
   # Install k6 automatically
   make setup-k6

   # Or install manually
   brew install k6  # macOS
   # or visit https://k6.io/docs/getting-started/installation/
   ```

### Run Benchmarks

```bash
# Quick benchmark (30 seconds)
./run_benchmark.sh --quick

# Full comprehensive benchmark
./run_benchmark.sh

# Only test task-specific endpoints
./run_benchmark.sh --task-only

# Verbose output
./run_benchmark.sh --verbose

# Custom profile count
./run_benchmark.sh --profiles 100
```

## 🔧 Available Tools

### 1. Shell Wrapper Script (`run_benchmark.sh`)
The easiest way to run benchmarks with automatic service checking and colored output.

**Usage:**
```bash
./run_benchmark.sh [options]

Options:
  --quick             Run quick benchmark (30 seconds)
  --task-only         Only test task-specific endpoints
  --verbose           Enable detailed logging
  --profiles N        Number of test profiles to create
  --skip-cleanup      Don't delete test profiles after
  --base-url URL      Override API base URL
```

**Examples:**
```bash
./run_benchmark.sh                    # Full benchmark
./run_benchmark.sh --quick            # Quick test
./run_benchmark.sh --profiles 200     # Create 200 test profiles
./run_benchmark.sh --verbose          # Detailed output
```

### 2. Python Benchmark Tool (`benchmark_tool.py`)
Advanced Python tool with detailed analysis and reporting.

**Usage:**
```bash
python3 benchmark_tool.py [options]

Options:
  --base-url URL           API base URL (default: http://localhost:8000)
  --profiles N             Number of profiles to create (default: 50)
  --skip-health-check      Skip service health verification
  --skip-cleanup           Keep test profiles after benchmark
  --quick                  Run quick benchmark only
  --task-only              Test task endpoints only
  --verbose                Enable verbose logging
```

**Examples:**
```bash
python3 benchmark_tool.py                               # Full benchmark
python3 benchmark_tool.py --quick                       # Quick benchmark
python3 benchmark_tool.py --task-only                   # Task tests only
python3 benchmark_tool.py --profiles 100 --verbose      # 100 profiles, verbose
python3 benchmark_tool.py --skip-cleanup                # Keep test data
```

### 3. k6 Scripts
Direct k6 performance testing scripts.

**Individual Scripts:**
```bash
# Profile creation load test
k6 run infrastructure/perf/create_profiles.js

# End-to-end simulation test
k6 run infrastructure/perf/simulation_e2e.js

# Mixed workload test
k6 run infrastructure/perf/mixed_workload.js

# Comprehensive multi-scenario test
k6 run infrastructure/perf/comprehensive_benchmark.js
```

**With Parameters:**
```bash
# High load test
k6 run -u 50 -d 5m infrastructure/perf/create_profiles.js

# Quick test
k6 run -u 10 -d 30s infrastructure/perf/mixed_workload.js

# Custom base URL
BASE_URL=http://production.example.com k6 run infrastructure/perf/create_profiles.js
```

### 4. Makefile Targets
Convenient make targets for common benchmark scenarios.

```bash
# Full benchmark suite (existing)
make benchmark

# Comprehensive benchmark with profile creation
make benchmark-comprehensive

# Python benchmark tool
make benchmark-tool

# Quick Python benchmark
make benchmark-tool-quick

# Comprehensive k6 benchmark
make benchmark-k6-comprehensive

# Individual benchmark types
make benchmark-quick
make benchmark-load
make benchmark-endurance
```

## 📊 Test Scenarios

### 1. Profile Creation Load Test
- **Purpose**: Test API performance under profile creation load
- **Metrics**: Requests/second, response times, error rates
- **Load Pattern**: Ramp up from 5 to 50 users over 3 minutes
- **Validation**: Profile creation success, response format

### 2. Task Endpoint Validation
- **Purpose**: Verify task-specific requirements are met
- **Endpoints Tested**:
  - `GET /profiles/{id}/days/{day}/` - Daily ice calculations
  - `GET /profiles/{id}/overview/{day}/` - Cost overview by day
  - `GET /profiles/overview/{day}/` - All profiles overview
  - `GET /profiles/overview/` - Final completion overview
- **Validation**: Correct calculations per task requirements

### 3. End-to-End Simulation Test
- **Purpose**: Test complete profile → simulation → cost calculation flow
- **Flow**: Create profile → Start simulation → Wait for completion → Verify cost
- **Metrics**: End-to-end latency, simulation throughput
- **Timeout**: 30 seconds maximum wait for cost calculation

### 4. Mixed Workload Test
- **Purpose**: Simulate realistic API usage patterns
- **Operations**:
  - 60% Read operations (GET requests)
  - 30% Write operations (profile creation)
  - 10% Simulation operations (start/stop)
- **Duration**: 10 minutes sustained load

### 5. Comprehensive Multi-Scenario Test
- **Purpose**: Run multiple scenarios simultaneously
- **Scenarios**:
  - Profile creation (ramping load)
  - Task validation (iterations)
  - Mixed operations (constant load)
- **Advanced Metrics**: Custom business metrics, scenario-specific thresholds

## 📈 Generated Reports

### Report Locations
- **JSON Reports**: `benchmarks/results/benchmark_report_YYYYMMDD_HHMMSS.json`
- **Markdown Reports**: `benchmarks/results/benchmark_report_YYYYMMDD_HHMMSS.md`
- **k6 JSON**: `benchmarks/results/comprehensive_benchmark_YYYY-MM-DD-*.json`

### Report Contents

**Python Tool Reports:**
- System configuration and test parameters
- Benchmark results with detailed metrics
- Task endpoint validation results
- Performance summary and recommendations
- Pass/fail status for all tests

**k6 Reports:**
- HTTP performance metrics (RPS, response times, error rates)
- Custom business metrics (profiles created, simulations started)
- Scenario-specific breakdowns
- Threshold compliance status

### Sample Report Structure
```json
{
  "timestamp": "2025-01-09T10:30:00Z",
  "system_info": {
    "base_url": "http://localhost:8000",
    "profiles_created": 50,
    "task_profiles": [...]
  },
  "benchmark_results": [
    {
      "scenario": "Profile Creation Load Test",
      "requests_per_second": 45.2,
      "avg_response_time_ms": 187.3,
      "p95_response_time_ms": 245.1,
      "error_rate_percent": 0.08,
      "success": true
    }
  ],
  "task_endpoint_results": {
    "Profile 1 Day 1": {
      "success": true,
      "response_time_ms": 123.4,
      "expectations_met": true
    }
  },
  "summary": {
    "overall_success": true,
    "avg_requests_per_second": 42.1,
    "task_endpoint_success_rate": 1.0
  }
}
```

## 🎯 Task-Specific Testing

The benchmark tool automatically creates and tests the exact profiles mentioned in the task requirements:

### Task Profiles Created
1. **Profile 1**: Sections with heights [21, 25, 28] (needs 9, 5, 2 more feet)
2. **Profile 2**: Section with height [17] (needs 13 more feet)
3. **Profile 3**: Sections with heights [17, 22, 17, 19, 17] (needs 13, 8, 13, 11, 13 more feet)

### Expected Results Validated
- **Day 1 Ice Usage**: 1,755 cubic yards total (585 + 195 + 975)
- **Day 1 Cost**: 3,334,500 Gold Dragons (1,755 × 1,900)
- **Daily Progress**: 1 foot per section per day
- **Crew Management**: Sections complete at 30 feet, crews are relieved

### Task Endpoint Tests
- Daily ice calculations for specific profiles and days
- Cost overviews for individual profiles
- System-wide cost calculations
- Final completion totals

## 🔧 Configuration

### Environment Variables
```bash
# Service URLs
BASE_URL=http://localhost:8000
SIMULATOR_URL=http://localhost:8001

# Test Configuration
DEFAULT_PROFILES=50
MAX_RESPONSE_TIME_MS=500
MAX_ERROR_RATE_PERCENT=1.0

# Load from .benchmark.env
source .benchmark.env
```

### Custom Configuration
Copy and modify `.benchmark.env` for custom settings:
```bash
cp .benchmark.env .benchmark.local.env
# Edit .benchmark.local.env
source .benchmark.local.env
./run_benchmark.sh
```

## 🚨 Troubleshooting

### Common Issues

**"Services not responding"**
```bash
# Check service status
docker compose ps

# View logs
docker compose logs api
docker compose logs simulator

# Restart services
docker compose restart
```

**"k6 not found"**
```bash
# Install k6
make setup-k6

# Or manually
brew install k6  # macOS
```

**"Benchmark fails with high error rate"**
```bash
# Check if services are under load
docker stats

# Reduce concurrent users
./run_benchmark.sh --profiles 25

# Check service health
curl http://localhost:8000/health/
```

**"Python dependencies missing"**
```bash
# Install dependencies
poetry install

# Or with pip
pip install requests
```

### Performance Tuning

**Increase Database Connections:**
```yaml
# docker-compose.yml
environment:
  - DB_POOL_SIZE=50  # Default: 20
```

**Adjust Memory Limits:**
```yaml
# docker-compose.yml
services:
  api:
    deploy:
      resources:
        limits:
          memory: 1G
```

**Scale Services:**
```bash
# Run multiple simulator instances
docker compose up --scale simulator=3
```

## 📋 Example Usage Scenarios

### Development Testing
```bash
# Quick health check
./run_benchmark.sh --quick --task-only

# Verify changes don't break performance
./run_benchmark.sh --profiles 20
```

### CI/CD Integration
```bash
# Automated testing in pipeline
python3 benchmark_tool.py --quick --skip-cleanup --base-url $TEST_URL
```

### Load Testing
```bash
# High-load scenario
k6 run -u 100 -d 10m infrastructure/perf/comprehensive_benchmark.js

# Endurance testing
make benchmark-endurance
```

### Performance Regression Testing
```bash
# Before changes
./run_benchmark.sh > before_results.txt

# After changes
./run_benchmark.sh > after_results.txt

# Compare results
diff before_results.txt after_results.txt
```

## 🔍 Monitoring Integration

### Grafana Dashboards
View real-time metrics during benchmarks:
- **URL**: http://localhost:3000
- **Dashboard**: "Wall System Performance"
- **Metrics**: Response times, error rates, resource usage

### Prometheus Metrics
Query performance metrics:
- **URL**: http://localhost:9090
- **Queries**:
  - `http_requests_total` - Request count
  - `http_request_duration_seconds` - Response times
  - `process_resident_memory_bytes` - Memory usage

### Alerts
Set up alerts for performance degradation:
```yaml
# prometheus/alerts.yml
- alert: HighLatency
  expr: http_request_duration_seconds{quantile="0.95"} > 0.5
  for: 5m
```

---

## 🏰 Summary

The Wall Benchmark Tool provides comprehensive testing capabilities for the construction management system:

✅ **Automated Profile Creation** - Creates realistic test profiles including task-specific ones
✅ **Multi-Scenario Testing** - Profile creation, simulations, mixed workloads
✅ **Task Requirement Validation** - Tests exact endpoints from requirements
✅ **Detailed Reporting** - JSON and Markdown reports with analysis
✅ **Performance Monitoring** - Integration with Grafana and Prometheus
✅ **Easy Usage** - Multiple interfaces from simple shell scripts to advanced Python tools

Start with `./run_benchmark.sh --quick` for a fast overview, then use `./run_benchmark.sh` for comprehensive testing!
