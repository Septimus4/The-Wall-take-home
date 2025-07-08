#!/bin/bash

# The Wall Benchmark Runner
# A convenient wrapper script for the comprehensive benchmark tool

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BENCHMARK_TOOL="$SCRIPT_DIR/benchmark_tool.py"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🏰 The Wall Benchmark Suite${NC}"
echo "=================================="

# Check if Python script exists
if [ ! -f "$BENCHMARK_TOOL" ]; then
    echo -e "${RED}❌ Benchmark tool not found at: $BENCHMARK_TOOL${NC}"
    exit 1
fi

# Check if k6 is installed
if ! command -v k6 >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  k6 not found. Installing k6...${NC}"
    if command -v brew >/dev/null 2>&1; then
        brew install k6
    else
        echo "Installing k6 via GitHub releases..."
        curl -s https://api.github.com/repos/grafana/k6/releases/latest | \
        grep "browser_download_url.*linux-amd64.tar.gz" | \
        cut -d '"' -f 4 | \
        xargs curl -L -o /tmp/k6.tar.gz && \
        tar -xzf /tmp/k6.tar.gz -C /tmp && \
        sudo mv /tmp/k6-*/k6 /usr/local/bin/ && \
        rm -rf /tmp/k6* && \
        echo -e "${GREEN}✅ k6 installed successfully${NC}"
    fi
fi

# Check if services are running
echo -e "${BLUE}📊 Checking service status...${NC}"
if ! curl -s http://localhost:8000/health/ >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  API Gateway not responding. Starting services...${NC}"
    echo "Please ensure the following services are running:"
    echo "  - API Gateway (port 8000)"
    echo "  - Simulator (port 8001)"
    echo "  - Kafka (port 9092)"
    echo "  - PostgreSQL (port 5432)"
    echo ""
    echo "Start with: docker compose up -d"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Parse command line arguments
BENCHMARK_ARGS=()
SHOW_HELP=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            SHOW_HELP=true
            shift
            ;;
        --quick)
            echo -e "${YELLOW}🚀 Running QUICK benchmark mode${NC}"
            BENCHMARK_ARGS+=("--quick")
            shift
            ;;
        --task-only)
            echo -e "${YELLOW}📋 Running TASK-ONLY mode${NC}"
            BENCHMARK_ARGS+=("--task-only")
            shift
            ;;
        --verbose|-v)
            echo -e "${YELLOW}📝 Verbose mode enabled${NC}"
            BENCHMARK_ARGS+=("--verbose")
            shift
            ;;
        --profiles)
            BENCHMARK_ARGS+=("--profiles" "$2")
            shift 2
            ;;
        --skip-cleanup)
            echo -e "${YELLOW}🗑️  Skipping cleanup${NC}"
            BENCHMARK_ARGS+=("--skip-cleanup")
            shift
            ;;
        --base-url)
            BENCHMARK_ARGS+=("--base-url" "$2")
            shift 2
            ;;
        *)
            echo -e "${RED}❌ Unknown option: $1${NC}"
            SHOW_HELP=true
            shift
            ;;
    esac
done

if [ "$SHOW_HELP" = true ]; then
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -h, --help          Show this help message"
    echo "  --quick             Run quick benchmark suite only (30 seconds)"
    echo "  --task-only         Only test task-specific endpoints"
    echo "  --verbose, -v       Enable verbose logging"
    echo "  --profiles N        Number of test profiles to create (default: 50)"
    echo "  --skip-cleanup      Skip cleanup of created profiles"
    echo "  --base-url URL      Base URL for the API (default: http://localhost:8000)"
    echo ""
    echo "Examples:"
    echo "  $0                  # Run full benchmark suite"
    echo "  $0 --quick          # Quick 30-second test"
    echo "  $0 --task-only      # Test only the task requirements"
    echo "  $0 --profiles 100   # Create 100 test profiles"
    echo "  $0 --verbose        # Enable detailed logging"
    echo ""
    exit 0
fi

# Show configuration
echo -e "${BLUE}📋 Benchmark Configuration:${NC}"
echo "  Script: $BENCHMARK_TOOL"
echo "  Arguments: ${BENCHMARK_ARGS[*]}"
echo ""

# Run the benchmark
echo -e "${GREEN}🚀 Starting benchmark...${NC}"
echo ""

python3 "$BENCHMARK_TOOL" "${BENCHMARK_ARGS[@]}"

BENCHMARK_EXIT_CODE=$?

if [ $BENCHMARK_EXIT_CODE -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Benchmark completed successfully!${NC}"
    echo ""
    echo -e "${BLUE}📊 Results saved in: benchmarks/results/${NC}"
    echo ""
    echo "View results:"
    echo "  - JSON report: ls -la benchmarks/results/*.json"
    echo "  - Markdown report: ls -la benchmarks/results/*.md"
    echo "  - Grafana dashboard: http://localhost:3000"
    echo "  - Prometheus metrics: http://localhost:9090"
else
    echo ""
    echo -e "${RED}❌ Benchmark failed with exit code: $BENCHMARK_EXIT_CODE${NC}"
    exit $BENCHMARK_EXIT_CODE
fi
