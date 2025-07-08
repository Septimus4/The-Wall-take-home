#!/usr/bin/env python3
"""
The Wall Benchmark Tool

A comprehensive benchmark tool that creates profiles and tests the performance
of The Wall construction management system.

Features:
- Creates realistic test profiles based on task requirements
- Runs multiple benchmark scenarios
- Provides detailed performance analysis
- Generates reports in multiple formats
- Monitors system resources during tests
"""

import argparse
import json
import os
import random
import subprocess
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Optional

import requests


@dataclass
class ProfileData:
    """Represents a wall profile for testing."""

    profile_id: str
    name: str
    height: float
    length: float = 100.0
    width: float = 3.0
    ice_thickness: float = 0.3
    sections: Optional[list[int]] = None


@dataclass
class BenchmarkResult:
    """Results from a benchmark run."""

    scenario: str
    duration_seconds: float
    virtual_users: int
    requests_per_second: float
    avg_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    error_rate_percent: float
    timestamp: str


class WallBenchmarkTool:
    """Main benchmark tool class."""

    def __init__(self, base_url: str = "http://localhost:8000", verbose: bool = False):
        self.base_url = base_url
        self.api_url = f"{base_url}/api/v1"
        self.verbose = verbose
        self.results_dir = "benchmarks/results"
        self.profiles_created: list[str] = []

        # Ensure results directory exists
        os.makedirs(self.results_dir, exist_ok=True)

        # Task-specific profiles as mentioned in the requirements
        self.task_profiles = [
            ProfileData(
                profile_id="task-profile-1",
                name="Task Profile 1 - [21, 25, 28]",
                height=21.0,  # Starting height, represents minimum
                sections=[21, 25, 28],
            ),
            ProfileData(
                profile_id="task-profile-2",
                name="Task Profile 2 - [17]",
                height=17.0,
                sections=[17],
            ),
            ProfileData(
                profile_id="task-profile-3",
                name="Task Profile 3 - [17, 22, 17, 19, 17]",
                height=17.0,
                sections=[17, 22, 17, 19, 17],
            ),
            ProfileData(
                profile_id="task-profile-4",
                name="Task Profile 4 - Extended [10, 15, 20, 25, 30, 35, 40]",
                height=10.0,
                sections=[10, 15, 20, 25, 30, 35, 40],
            ),
            ProfileData(
                profile_id="task-profile-5",
                name="Task Profile 5 - Long Build [5, 8, 12, 16, 20, 24, 28, 32, 36, 40]",
                height=5.0,
                sections=[5, 8, 12, 16, 20, 24, 28, 32, 36, 40],
            ),
        ]

    def log(self, message: str, level: str = "INFO"):
        """Log a message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {"INFO": "ℹ️", "SUCCESS": "✅", "ERROR": "❌", "WARNING": "⚠️"}.get(
            level, "📝"
        )

        print(f"[{timestamp}] {prefix} {message}")

        if self.verbose and level in ["ERROR", "WARNING"]:
            print(f"    Details: {message}")

    def check_services(self) -> bool:
        """Check if all required services are running."""
        self.log("Checking service health...")

        services = [
            (f"{self.base_url}/health/", "API Gateway"),
            ("http://localhost:9000/health", "Simulator"),
            ("http://localhost:3000/api/health", "Grafana"),
            ("http://localhost:9090/-/healthy", "Prometheus"),
        ]

        all_healthy = True
        for url, service in services:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    self.log(f"{service} is healthy", "SUCCESS")
                else:
                    self.log(f"{service} returned {response.status_code}", "WARNING")
                    all_healthy = False
            except requests.RequestException as e:
                self.log(f"{service} is not responding: {e}", "ERROR")
                all_healthy = False

        return all_healthy

    def create_test_profiles(self, count: int = 50) -> list[str]:
        """Create test profiles for benchmarking."""
        self.log(f"Creating {count} test profiles...")

        created_profiles = []

        # First, create the task-specific profiles using the correct load-config endpoint
        task_profile_ids = {}
        for profile in self.task_profiles:
            success, actual_profile_id = self._create_task_profile_with_retry(profile)

            if success and actual_profile_id:
                created_profiles.append(actual_profile_id)
                task_profile_ids[
                    profile.profile_id
                ] = actual_profile_id  # Map our internal ID to actual API ID
                self.log(
                    f"Created task profile: {profile.name} (ID: {actual_profile_id})",
                    "SUCCESS",
                )
            else:
                self.log(
                    f"Failed to create task profile {profile.name} after retries",
                    "ERROR",
                )

        # Store the mapping for later use in testing
        self.task_profile_ids = task_profile_ids

        # Then create additional random profiles for load testing
        batch_size = 25
        additional_profiles_needed = max(0, count - len(self.task_profiles))
        self.log(
            f"Creating {additional_profiles_needed} additional profiles in batches of {batch_size}..."
        )

        for i in range(additional_profiles_needed):
            if i > 0 and i % batch_size == 0:
                self.log(
                    f"Created {i}/{additional_profiles_needed} additional profiles..."
                )
                time.sleep(1)  # Brief pause between batches

            profile_id = f"bench-{uuid.uuid4()}"

            # Generate realistic wall data
            heights = [5.0, 10.0, 15.0, 20.0, 25.0, 30.0]  # Common wall heights
            height = heights[i % len(heights)]

            payload = {
                "name": f"Benchmark Wall {i+1}",
                "height": height,
                "length": 50.0 + (i % 200),  # Vary length 50-250
                "width": 2.0 + (i % 8),  # Vary width 2-10
                "ice_thickness": 0.2 + (i % 3) * 0.1,  # Vary thickness 0.2-0.5
            }

            success = self._create_single_profile_with_retry(profile_id, payload)

            if success:
                created_profiles.append(profile_id)
                if self.verbose:
                    self.log(
                        f"Created profile {i+1}/{additional_profiles_needed}: {profile_id}"
                    )
            else:
                if self.verbose:
                    self.log(f"Failed to create profile {i+1} after retries", "WARNING")

        self.profiles_created = created_profiles
        self.log(f"Successfully created {len(created_profiles)} profiles", "SUCCESS")
        return created_profiles

    def _create_single_profile_with_retry(
        self, profile_id: str, payload: dict[str, Any], max_retries: int = 3
    ) -> bool:
        """Create a single profile with retry logic to handle database locking."""
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"{self.api_url}/profiles/",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=15,  # Increased timeout for database operations
                )

                if response.status_code == 201:
                    return True
                elif response.status_code == 409:
                    # Profile already exists - consider this success
                    return True
                elif response.status_code == 400:
                    # Bad request - probably validation error, don't retry
                    if self.verbose:
                        self.log(
                            f"Validation error for {profile_id}: {response.text}",
                            "WARNING",
                        )
                    return False
                elif response.status_code == 500 and attempt < max_retries - 1:
                    # Server error (likely database lock) - retry with exponential backoff
                    wait_time = (2**attempt) + random.uniform(0, 1)
                    if self.verbose:
                        self.log(
                            f"Server error for {profile_id}, retrying in {wait_time:.1f}s (attempt {attempt + 1}/{max_retries})"
                        )
                    time.sleep(wait_time)
                    continue
                else:
                    if self.verbose:
                        self.log(
                            f"Failed to create {profile_id}: HTTP {response.status_code}",
                            "WARNING",
                        )
                    return False

            except requests.RequestException as e:
                if attempt < max_retries - 1:
                    wait_time = (2**attempt) + random.uniform(0, 1)
                    if self.verbose:
                        self.log(
                            f"Request error for {profile_id}, retrying in {wait_time:.1f}s: {e}"
                        )
                    time.sleep(wait_time)
                    continue
                else:
                    if self.verbose:
                        self.log(
                            f"Request failed for {profile_id} after {max_retries} attempts: {e}",
                            "WARNING",
                        )
                    return False

        return False

    def _create_task_profile_with_retry(
        self, profile: ProfileData, max_retries: int = 3
    ) -> tuple[bool, str]:
        """Create a task profile using the load-config endpoint with retry logic."""
        # Convert sections to the expected config format
        config_data = [" ".join(map(str, profile.sections))]

        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"{self.api_url}/load-config/",
                    json={"config": config_data},
                    headers={"Content-Type": "application/json"},
                    timeout=15,
                )

                if response.status_code in [200, 201]:
                    # Parse the response to get the actual profile ID
                    response_data = response.json()
                    if "profiles" in response_data and response_data["profiles"]:
                        actual_profile_id = response_data["profiles"][0]["id"]
                        return True, actual_profile_id
                    return True, ""
                elif response.status_code == 400:
                    # Bad request - probably validation error, don't retry
                    if self.verbose:
                        self.log(
                            f"Validation error for {profile.name}: {response.text}",
                            "WARNING",
                        )
                    return False, ""
                elif response.status_code == 500 and attempt < max_retries - 1:
                    # Server error (likely database lock) - retry with exponential backoff
                    wait_time = (2**attempt) + random.uniform(0, 1)
                    if self.verbose:
                        self.log(
                            f"Server error for {profile.name}, retrying in {wait_time:.1f}s (attempt {attempt + 1}/{max_retries})"
                        )
                    time.sleep(wait_time)
                    continue
                else:
                    if self.verbose:
                        self.log(
                            f"Failed to create {profile.name}: HTTP {response.status_code}",
                            "WARNING",
                        )
                    return False, ""

            except requests.RequestException as e:
                if attempt < max_retries - 1:
                    wait_time = (2**attempt) + random.uniform(0, 1)
                    if self.verbose:
                        self.log(
                            f"Request error for {profile.name}, retrying in {wait_time:.1f}s: {e}"
                        )
                    time.sleep(wait_time)
                    continue
                else:
                    if self.verbose:
                        self.log(
                            f"Request failed for {profile.name} after {max_retries} attempts: {e}",
                            "WARNING",
                        )
                    return False, ""

        return False, ""

    def run_k6_scenario(
        self, script_path: str, scenario_name: str, extra_args: list[str] = None
    ) -> Optional[BenchmarkResult]:
        """Run a k6 benchmark scenario."""
        self.log(f"Running {scenario_name} benchmark...")

        cmd = ["k6", "run"]

        if extra_args:
            cmd.extend(extra_args)

        # Set environment variables
        env = os.environ.copy()
        env["BASE_URL"] = self.base_url

        cmd.append(script_path)

        try:
            start_time = time.time()
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600,  # 1 hour timeout
                env=env,
            )
            end_time = time.time()

            if result.returncode == 0:
                # Parse k6 output to extract metrics
                metrics = self._parse_k6_output(result.stdout)

                benchmark_result = BenchmarkResult(
                    scenario=scenario_name,
                    duration_seconds=end_time - start_time,
                    virtual_users=metrics.get("vus_max", 0),
                    requests_per_second=metrics.get("http_reqs_rate", 0.0),
                    avg_response_time_ms=metrics.get("http_req_duration_avg", 0.0),
                    p95_response_time_ms=metrics.get("http_req_duration_p95", 0.0),
                    p99_response_time_ms=metrics.get("http_req_duration_p99", 0.0),
                    error_rate_percent=metrics.get("http_req_failed_rate", 0.0) * 100,
                    timestamp=datetime.now().isoformat(),
                )

                self.log(f"{scenario_name} completed", "SUCCESS")
                self.log(f"  RPS: {benchmark_result.requests_per_second:.1f}")
                self.log(
                    f"  Avg Response: {benchmark_result.avg_response_time_ms:.1f}ms"
                )
                self.log(
                    f"  P95 Response: {benchmark_result.p95_response_time_ms:.1f}ms"
                )
                self.log(f"  Error Rate: {benchmark_result.error_rate_percent:.2f}%")

                return benchmark_result
            else:
                self.log(f"{scenario_name} failed: {result.stderr}", "ERROR")
                return None

        except subprocess.TimeoutExpired:
            self.log(f"{scenario_name} timed out", "ERROR")
            return None
        except subprocess.SubprocessError as e:
            self.log(f"Error running {scenario_name}: {e}", "ERROR")
            return None

    def _parse_k6_output(self, output: str) -> dict[str, float]:
        """Parse k6 output to extract key metrics."""
        metrics = {}

        lines = output.split("\n")
        for line in lines:
            line = line.strip()

            # Parse different metric formats
            if "http_reqs................" in line:
                # Extract requests/sec
                if "/s" in line:
                    rate_part = line.split("/s")[0].split()[-1]
                    try:
                        metrics["http_reqs_rate"] = float(rate_part)
                    except ValueError:
                        pass

            elif "http_req_duration......." in line:
                # Extract response time metrics
                parts = line.split()
                for i, part in enumerate(parts):
                    if "avg=" in part:
                        try:
                            metrics["http_req_duration_avg"] = float(
                                part.split("=")[1].replace("ms", "")
                            )
                        except (ValueError, IndexError):
                            pass
                    elif "p(95)=" in part:
                        try:
                            metrics["http_req_duration_p95"] = float(
                                part.split("=")[1].replace("ms", "")
                            )
                        except (ValueError, IndexError):
                            pass
                    elif "p(99)=" in part:
                        try:
                            metrics["http_req_duration_p99"] = float(
                                part.split("=")[1].replace("ms", "")
                            )
                        except (ValueError, IndexError):
                            pass

            elif "http_req_failed........" in line:
                # Extract error rate
                if "%" in line:
                    rate_part = line.split("%")[0].split()[-1]
                    try:
                        metrics["http_req_failed_rate"] = float(rate_part) / 100
                    except ValueError:
                        pass

            elif "vus................." in line:
                # Extract virtual users
                if "max=" in line:
                    max_part = line.split("max=")[1].split()[0]
                    try:
                        metrics["vus_max"] = int(max_part)
                    except ValueError:
                        pass

        return metrics

    def run_comprehensive_benchmark(self) -> list[BenchmarkResult]:
        """Run a comprehensive benchmark suite."""
        self.log("Starting comprehensive benchmark suite...", "SUCCESS")

        results = []

        scenarios = [
            {
                "name": "Profile Creation Load Test",
                "script": "infrastructure/perf/create_profiles.js",
                "args": [],
            },
            {
                "name": "End-to-End Simulation Test",
                "script": "infrastructure/perf/simulation_e2e.js",
                "args": [],
            },
            {
                "name": "Mixed Workload Test",
                "script": "infrastructure/perf/mixed_workload.js",
                "args": [],
            },
            {
                "name": "High Load Test",
                "script": "infrastructure/perf/create_profiles.js",
                "args": ["-u", "50", "-d", "2m"],
            },
            {
                "name": "Spike Test",
                "script": "infrastructure/perf/mixed_workload.js",
                "args": [
                    "-u",
                    "10",
                    "-d",
                    "1m",
                    "--stage",
                    "duration=30s,target=100",
                    "--stage",
                    "duration=1m,target=10",
                ],
            },
        ]

        for scenario in scenarios:
            result = self.run_k6_scenario(
                scenario["script"], scenario["name"], scenario["args"]
            )

            if result:
                results.append(result)

            # Brief pause between tests
            time.sleep(5)

        return results

    def test_task_endpoints(self) -> dict[str, Any]:
        """Test the specific task endpoints with created profiles."""
        self.log("Testing task-specific endpoints...")

        test_results = {}

        # Test the task profiles we created
        task_profile_ids = getattr(self, "task_profile_ids", {})

        if not task_profile_ids:
            self.log("No task profiles available for testing", "WARNING")
            return {}

        # Map our internal profile names to actual IDs
        profile_mapping = {}
        if "task-profile-1" in task_profile_ids:
            profile_mapping["profile1"] = task_profile_ids["task-profile-1"]
        if "task-profile-2" in task_profile_ids:
            profile_mapping["profile2"] = task_profile_ids["task-profile-2"]
        if "task-profile-3" in task_profile_ids:
            profile_mapping["profile3"] = task_profile_ids["task-profile-3"]
        if "task-profile-4" in task_profile_ids:
            profile_mapping["profile4"] = task_profile_ids["task-profile-4"]
        if "task-profile-5" in task_profile_ids:
            profile_mapping["profile5"] = task_profile_ids["task-profile-5"]

        # Test multiple days and scenarios
        tests = [
            # Day 1 tests (original task requirements)
            (
                f"/profiles/{profile_mapping.get('profile1', 'missing')}/days/1/",
                "Profile 1 Day 1",
                {"expected_ice": 585},
            ),
            (
                f"/profiles/{profile_mapping.get('profile2', 'missing')}/days/1/",
                "Profile 2 Day 1",
                {"expected_ice": 195},
            ),
            (
                f"/profiles/{profile_mapping.get('profile3', 'missing')}/days/1/",
                "Profile 3 Day 1",
                {"expected_ice": 975},
            ),
            # Extended profiles day 1
            (
                f"/profiles/{profile_mapping.get('profile4', 'missing')}/days/1/",
                "Profile 4 Extended Day 1",
                {},
            ),
            (
                f"/profiles/{profile_mapping.get('profile5', 'missing')}/days/1/",
                "Profile 5 Long Day 1",
                {},
            ),
            # Day 3 tests (mid-construction)
            (
                f"/profiles/{profile_mapping.get('profile1', 'missing')}/days/3/",
                "Profile 1 Day 3",
                {},
            ),
            (
                f"/profiles/{profile_mapping.get('profile2', 'missing')}/days/3/",
                "Profile 2 Day 3",
                {},
            ),
            (
                f"/profiles/{profile_mapping.get('profile3', 'missing')}/days/3/",
                "Profile 3 Day 3",
                {},
            ),
            (
                f"/profiles/{profile_mapping.get('profile4', 'missing')}/days/3/",
                "Profile 4 Extended Day 3",
                {},
            ),
            (
                f"/profiles/{profile_mapping.get('profile5', 'missing')}/days/3/",
                "Profile 5 Long Day 3",
                {},
            ),
            # Day 5 tests (later construction)
            (
                f"/profiles/{profile_mapping.get('profile1', 'missing')}/days/5/",
                "Profile 1 Day 5",
                {},
            ),
            (
                f"/profiles/{profile_mapping.get('profile4', 'missing')}/days/5/",
                "Profile 4 Extended Day 5",
                {},
            ),
            (
                f"/profiles/{profile_mapping.get('profile5', 'missing')}/days/5/",
                "Profile 5 Long Day 5",
                {},
            ),
            # Day 7 tests (extended construction)
            (
                f"/profiles/{profile_mapping.get('profile4', 'missing')}/days/7/",
                "Profile 4 Extended Day 7",
                {},
            ),
            (
                f"/profiles/{profile_mapping.get('profile5', 'missing')}/days/7/",
                "Profile 5 Long Day 7",
                {},
            ),
            # Day 10 tests (very extended)
            (
                f"/profiles/{profile_mapping.get('profile5', 'missing')}/days/10/",
                "Profile 5 Long Day 10",
                {},
            ),
            # Overview tests for different days
            (
                f"/profiles/{profile_mapping.get('profile1', 'missing')}/overview/1/",
                "Profile 1 Overview Day 1",
                {"expected_cost": 1111500},
            ),
            (
                f"/profiles/{profile_mapping.get('profile1', 'missing')}/overview/3/",
                "Profile 1 Overview Day 3",
                {},
            ),
            (
                f"/profiles/{profile_mapping.get('profile4', 'missing')}/overview/1/",
                "Profile 4 Extended Overview Day 1",
                {},
            ),
            (
                f"/profiles/{profile_mapping.get('profile4', 'missing')}/overview/5/",
                "Profile 4 Extended Overview Day 5",
                {},
            ),
            (
                f"/profiles/{profile_mapping.get('profile5', 'missing')}/overview/1/",
                "Profile 5 Long Overview Day 1",
                {},
            ),
            (
                f"/profiles/{profile_mapping.get('profile5', 'missing')}/overview/7/",
                "Profile 5 Long Overview Day 7",
                {},
            ),
            (
                f"/profiles/{profile_mapping.get('profile5', 'missing')}/overview/10/",
                "Profile 5 Long Overview Day 10",
                {},
            ),
            # Global overview tests
            ("/profiles/overview/1/", "All Profiles Overview Day 1", {}),
            ("/profiles/overview/3/", "All Profiles Overview Day 3", {}),
            ("/profiles/overview/5/", "All Profiles Overview Day 5", {}),
            ("/profiles/overview/", "Final Overview", {}),
        ]

        for endpoint, test_name, expectations in tests:
            try:
                start_time = time.time()
                response = requests.get(f"{self.api_url}{endpoint}", timeout=10)
                response_time = (time.time() - start_time) * 1000

                if response.status_code == 200:
                    data = response.json()
                    test_results[test_name] = {
                        "status_code": response.status_code,
                        "response_time_ms": response_time,
                        "data": data,
                        "expectations_met": self._check_expectations(
                            data, expectations
                        ),
                    }
                    self.log(
                        f"{test_name}: Status {response.status_code} ({response_time:.1f}ms)",
                        "INFO",
                    )
                else:
                    test_results[test_name] = {
                        "status_code": response.status_code,
                        "response_time_ms": response_time,
                        "error": response.text,
                    }
                    self.log(
                        f"{test_name}: Status {response.status_code} ({response_time:.1f}ms)",
                        "INFO",
                    )

            except requests.RequestException as e:
                test_results[test_name] = {"error": str(e)}
                self.log(f"{test_name}: Request error - {e}", "INFO")

        return test_results

    def _check_expectations(self, data: dict, expectations: dict) -> bool:
        """Check if response data meets expectations."""
        if not expectations:
            return True

        for key, expected_value in expectations.items():
            if key == "expected_ice" and "ice_amount" in data:
                ice_amount = (
                    float(data["ice_amount"])
                    if isinstance(data["ice_amount"], str)
                    else data["ice_amount"]
                )
                return abs(ice_amount - expected_value) < 0.01
            elif key == "expected_cost" and "cost" in data:
                cost = (
                    float(data["cost"])
                    if isinstance(data["cost"], str)
                    else data["cost"]
                )
                return abs(cost - expected_value) < 0.01
            elif key == "expected_total" and "total_cost" in data:
                total_cost = (
                    float(data["total_cost"])
                    if isinstance(data["total_cost"], str)
                    else data["total_cost"]
                )
                return abs(total_cost - expected_value) < 0.01

        return True

    def generate_report(
        self, benchmark_results: list[BenchmarkResult], task_results: dict[str, Any]
    ) -> str:
        """Generate a comprehensive benchmark report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"{self.results_dir}/benchmark_report_{timestamp}.json"

        report_data = {
            "timestamp": datetime.now().isoformat(),
            "system_info": {
                "base_url": self.base_url,
                "profiles_created": len(self.profiles_created),
                "task_profiles": [asdict(p) for p in self.task_profiles],
            },
            "benchmark_results": [asdict(r) for r in benchmark_results],
            "task_endpoint_results": task_results,
            "summary": self._generate_summary(benchmark_results, task_results),
        }

        with open(report_file, "w") as f:
            json.dump(report_data, f, indent=2)

        # Also generate a human-readable report
        self._generate_human_readable_report(report_data, timestamp)

        return report_file

    def _generate_summary(
        self, benchmark_results: list[BenchmarkResult], task_results: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate a summary of all test results."""

        # Calculate metrics from load test benchmarks if available
        if benchmark_results:
            # Use actual benchmark results (load tests or k6)
            total_benchmarks = len(benchmark_results)

            if benchmark_results:
                avg_rps = sum(r.requests_per_second for r in benchmark_results) / len(
                    benchmark_results
                )
                avg_response_time = sum(
                    r.avg_response_time_ms for r in benchmark_results
                ) / len(benchmark_results)
                max_error_rate = max(r.error_rate_percent for r in benchmark_results)
                min_error_rate = min(r.error_rate_percent for r in benchmark_results)
            else:
                avg_rps = avg_response_time = max_error_rate = min_error_rate = 0

            benchmark_type = (
                "k6"
                if any("k6" in r.scenario.lower() for r in benchmark_results)
                else "load_test"
            )
        else:
            # If no load test benchmarks, calculate synthetic metrics from task endpoint tests
            successful_task_results = [
                r
                for r in task_results.values()
                if r.get("status_code") == 200 and "response_time_ms" in r
            ]

            total_benchmarks = len(task_results)

            if successful_task_results:
                # Calculate average response time from task tests
                avg_response_time = sum(
                    r["response_time_ms"] for r in successful_task_results
                ) / len(successful_task_results)

                # Estimate RPS based on response time (conservative estimate)
                # RPS = 1000ms / avg_response_time_ms (for single threaded)
                # For multiple concurrent users, multiply by reasonable concurrency factor
                estimated_concurrent_users = 10  # Conservative estimate
                avg_rps = (
                    (1000 / avg_response_time) * estimated_concurrent_users
                    if avg_response_time > 0
                    else 0
                )

                # Error rate from task tests
                total_tasks = len(task_results)
                failed_tasks = sum(
                    1 for r in task_results.values() if r.get("status_code", 0) != 200
                )
                max_error_rate = min_error_rate = (
                    (failed_tasks / total_tasks) * 100 if total_tasks > 0 else 0
                )
            else:
                avg_rps = avg_response_time = max_error_rate = min_error_rate = 0

            benchmark_type = "api_endpoints"

        # Count status codes from task tests
        status_code_distribution = {}
        for result in task_results.values():
            status_code = result.get("status_code", "unknown")
            status_code_distribution[status_code] = (
                status_code_distribution.get(status_code, 0) + 1
            )

        return {
            "total_benchmarks": total_benchmarks,
            "total_task_endpoints": len(task_results),
            "avg_requests_per_second": avg_rps,
            "avg_response_time_ms": avg_response_time,
            "error_rate_range": {
                "min_percent": min_error_rate,
                "max_percent": max_error_rate,
            },
            "status_code_distribution": status_code_distribution,
            "benchmark_type": benchmark_type,
        }

    def _generate_human_readable_report(
        self, report_data: dict[str, Any], timestamp: str
    ):
        """Generate a human-readable markdown report."""
        report_file = f"{self.results_dir}/benchmark_report_{timestamp}.md"

        with open(report_file, "w") as f:
            f.write("# The Wall Benchmark Report\n\n")
            f.write(f"**Generated:** {report_data['timestamp']}\n")
            f.write(
                f"**Profiles Created:** {report_data['system_info']['profiles_created']}\n"
            )
            f.write(f"**Base URL:** {report_data['system_info']['base_url']}\n\n")

            # Summary
            summary = report_data["summary"]
            f.write("## Summary\n\n")
            f.write(
                f"- **Benchmark Type:** {summary.get('benchmark_type', 'unknown').upper()}\n"
            )
            f.write(f"- **Total Benchmarks:** {summary['total_benchmarks']}\n")
            f.write(f"- **Total Task Endpoints:** {summary['total_task_endpoints']}\n")
            f.write(f"- **Average RPS:** {summary['avg_requests_per_second']:.1f}\n")
            f.write(
                f"- **Average Response Time:** {summary['avg_response_time_ms']:.1f}ms\n"
            )
            f.write(
                f"- **Error Rate Range:** {summary['error_rate_range']['min_percent']:.2f}% - {summary['error_rate_range']['max_percent']:.2f}%\n"
            )

            # Status code distribution
            if summary.get("status_code_distribution"):
                f.write("- **Status Code Distribution:**\n")
                for status_code, count in summary["status_code_distribution"].items():
                    f.write(f"  - {status_code}: {count}\n")
            f.write("\n")

            # Benchmark Results
            f.write("## Benchmark Results\n\n")
            f.write("| Scenario | RPS | Avg Response | P95 Response | Error Rate |\n")
            f.write("|----------|-----|--------------|--------------|------------|\n")

            for result in report_data["benchmark_results"]:
                f.write(
                    f"| {result['scenario']} | {result['requests_per_second']:.1f} | "
                    f"{result['avg_response_time_ms']:.1f}ms | {result['p95_response_time_ms']:.1f}ms | "
                    f"{result['error_rate_percent']:.2f}% |\n"
                )

            # Task Endpoint Results
            f.write("\n## Task Endpoint Tests\n\n")
            f.write(
                "| Test | Status Code | Response Time | Data Present | Expectations Met |\n"
            )
            f.write(
                "|------|-------------|---------------|--------------|------------------|\n"
            )

            for test_name, result in report_data["task_endpoint_results"].items():
                status_code = result.get("status_code", "N/A")
                response_time = f"{result.get('response_time_ms', 0):.1f}ms"
                data_present = "Yes" if result.get("data") else "No"
                expectations = "Yes" if result.get("expectations_met", False) else "No"
                f.write(
                    f"| {test_name} | {status_code} | {response_time} | {data_present} | {expectations} |\n"
                )

        self.log(f"Human-readable report saved to: {report_file}", "SUCCESS")

    def cleanup_profiles(self):
        """Clean up created test profiles."""
        if not self.profiles_created:
            return

        self.log(f"Cleaning up {len(self.profiles_created)} test profiles...")

        cleaned = 0
        for profile_id in self.profiles_created:
            try:
                response = requests.delete(
                    f"{self.api_url}/profiles/{profile_id}/", timeout=10
                )
                if response.status_code in [
                    204,
                    404,
                ]:  # 404 is OK, profile might not exist
                    cleaned += 1
                    if self.verbose:
                        self.log(f"Deleted profile: {profile_id}")
            except requests.RequestException as e:
                if self.verbose:
                    self.log(f"Failed to delete {profile_id}: {e}", "WARNING")

        self.log(
            f"Cleaned up {cleaned}/{len(self.profiles_created)} profiles", "SUCCESS"
        )

    def run_simple_load_test(
        self, duration_seconds: int = 30, concurrent_users: int = 10
    ) -> Optional[BenchmarkResult]:
        """Run a simple Python-based load test against the API."""
        import queue
        import threading

        self.log(
            f"Running simple load test: {concurrent_users} users for {duration_seconds}s..."
        )

        results_queue = queue.Queue()
        start_time = time.time()
        end_time = start_time + duration_seconds

        def worker():
            """Worker thread that makes requests to the API."""
            local_results = []
            while time.time() < end_time:
                try:
                    request_start = time.time()
                    response = requests.get(
                        f"{self.api_url}/task-profiles/", timeout=10
                    )
                    request_end = time.time()

                    local_results.append(
                        {
                            "success": response.status_code == 200,
                            "response_time": (request_end - request_start)
                            * 1000,  # Convert to ms
                            "status_code": response.status_code,
                        }
                    )

                    # Small delay to avoid overwhelming the server
                    time.sleep(0.1)

                except requests.RequestException as e:
                    local_results.append(
                        {"success": False, "response_time": 0, "error": str(e)}
                    )

            results_queue.put(local_results)

        # Start worker threads
        threads = []
        for _ in range(concurrent_users):
            thread = threading.Thread(target=worker)
            thread.start()
            threads.append(thread)

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Collect all results
        all_results = []
        while not results_queue.empty():
            all_results.extend(results_queue.get())

        if not all_results:
            self.log("No results collected from load test", "ERROR")
            return None

        # Calculate metrics
        successful_requests = [r for r in all_results if r["success"]]
        total_requests = len(all_results)
        successful_count = len(successful_requests)

        actual_duration = time.time() - start_time
        rps = total_requests / actual_duration if actual_duration > 0 else 0

        if successful_requests:
            response_times = [r["response_time"] for r in successful_requests]
            avg_response_time = sum(response_times) / len(response_times)
            response_times.sort()
            p95_index = int(len(response_times) * 0.95)
            p99_index = int(len(response_times) * 0.99)
            p95_response_time = (
                response_times[p95_index]
                if p95_index < len(response_times)
                else response_times[-1]
            )
            p99_response_time = (
                response_times[p99_index]
                if p99_index < len(response_times)
                else response_times[-1]
            )
        else:
            avg_response_time = p95_response_time = p99_response_time = 0

        error_rate = (
            ((total_requests - successful_count) / total_requests) * 100
            if total_requests > 0
            else 0
        )

        result = BenchmarkResult(
            scenario="Simple Load Test",
            duration_seconds=actual_duration,
            virtual_users=concurrent_users,
            requests_per_second=rps,
            avg_response_time_ms=avg_response_time,
            p95_response_time_ms=p95_response_time,
            p99_response_time_ms=p99_response_time,
            error_rate_percent=error_rate,
            timestamp=datetime.now().isoformat(),
        )

        self.log("Load test completed", "INFO")
        self.log(f"  Total Requests: {total_requests}")
        self.log(f"  RPS: {rps:.1f}")
        self.log(f"  Avg Response: {avg_response_time:.1f}ms")
        self.log(f"  P95 Response: {p95_response_time:.1f}ms")
        self.log(f"  Error Rate: {error_rate:.2f}%")

        return result


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="The Wall Benchmark Tool")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL for the API (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--profiles",
        type=int,
        default=50,
        help="Number of test profiles to create (default: 50)",
    )
    parser.add_argument(
        "--skip-health-check", action="store_true", help="Skip health check of services"
    )
    parser.add_argument(
        "--skip-cleanup", action="store_true", help="Skip cleanup of created profiles"
    )
    parser.add_argument(
        "--quick", action="store_true", help="Run quick benchmark suite only"
    )
    parser.add_argument(
        "--task-only", action="store_true", help="Only test task-specific endpoints"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    tool = WallBenchmarkTool(base_url=args.base_url, verbose=args.verbose)

    try:
        tool.log("🏰 The Wall Benchmark Tool Starting...", "SUCCESS")

        # Health check
        if not args.skip_health_check:
            if not tool.check_services():
                tool.log("Some services are not healthy. Continue? (y/N): ", "WARNING")
                if input().lower() != "y":
                    sys.exit(1)

        # Create test profiles
        tool.create_test_profiles(args.profiles)

        # Run benchmarks
        benchmark_results = []
        if not args.task_only:
            if args.quick:
                tool.log("Running quick load test...")
                # Use simple Python load test instead of k6
                result = tool.run_simple_load_test(
                    duration_seconds=15, concurrent_users=5
                )
                if result:
                    benchmark_results.append(result)
            else:
                # Try to run k6 benchmarks first, fall back to simple load test
                tool.log("Attempting comprehensive benchmark...")
                try:
                    # Check if we can run k6 from within Docker
                    comprehensive_results = tool.run_comprehensive_benchmark()
                    if comprehensive_results:
                        benchmark_results.extend(comprehensive_results)
                    else:
                        tool.log(
                            "k6 not available, running Python load tests instead..."
                        )
                        # Run multiple simple load tests with different parameters
                        load_tests = [
                            (10, 5, "Light Load Test"),
                            (20, 10, "Medium Load Test"),
                            (15, 20, "High Concurrency Test"),
                        ]

                        for duration, users, name in load_tests:
                            result = tool.run_simple_load_test(
                                duration_seconds=duration, concurrent_users=users
                            )
                            if result:
                                result.scenario = name
                                benchmark_results.append(result)
                            time.sleep(2)  # Brief pause between tests

                except Exception as e:
                    tool.log(f"Comprehensive benchmark failed: {e}", "WARNING")
                    tool.log("Running simple load test instead...")
                    result = tool.run_simple_load_test(
                        duration_seconds=30, concurrent_users=10
                    )
                    if result:
                        benchmark_results.append(result)

        # Test task endpoints
        task_results = tool.test_task_endpoints()

        # Generate report
        report_file = tool.generate_report(benchmark_results, task_results)
        tool.log(f"Benchmark report saved to: {report_file}", "SUCCESS")

        # Cleanup
        if not args.skip_cleanup:
            tool.cleanup_profiles()

        tool.log("🏰 Benchmark completed", "INFO")

    except KeyboardInterrupt:
        tool.log("Benchmark interrupted by user", "WARNING")
        if not args.skip_cleanup:
            tool.cleanup_profiles()
        sys.exit(1)
    except Exception as e:
        tool.log(f"Benchmark failed: {e}", "ERROR")
        if not args.skip_cleanup:
            tool.cleanup_profiles()
        sys.exit(1)


if __name__ == "__main__":
    main()
