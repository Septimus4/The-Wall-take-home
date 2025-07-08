.PHONY: help install dev test clean migrate runserver setup run-platform test-all benchmark-comprehensive benchmark-tool benchmark-tool-quick check-deps status stop-platform quick-start test-api test-watch test-core

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Main Commands:'
	@echo '  setup                  - Complete project setup (install dependencies, migrate DB)'
	@echo '  run-platform           - Start the complete platform (API, simulator, materializer)'
	@echo '  test-all               - Run all tests (unit, integration, API)'
	@echo '  benchmark-tool         - Run Python benchmark tool with full analysis'
	@echo '  benchmark-tool-quick   - Run quick Python benchmark'
	@echo ''
	@echo 'All Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-23s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies
	poetry install

setup: install ## Complete project setup (install dependencies and migrate database)
	@echo "🔧 Setting up The Wall project..."
	poetry install
	poetry run python thewall/manage.py migrate
	@echo "✅ Project setup complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  - Run 'make run-platform' to start the complete platform"
	@echo "  - Run 'make test-all' to run all tests"
	@echo "  - Run 'make benchmark-tool' to run benchmarks"

migrate: ## Run Django migrations
	poetry run python thewall/manage.py migrate

runserver: ## Run Django development server
	poetry run python thewall/manage.py runserver 0.0.0.0:8000

run-simulator: ## Run FastAPI simulation service
	poetry run python services/simulator/cli.py --reload

run-materializer: ## Run materializer Kafka consumer
	poetry run python thewall/manage.py run_materializer

run-all: ## Run both API gateway and simulator (requires tmux)
	@if command -v tmux >/dev/null 2>&1; then \
		tmux new-session -d -s wall-demo -n api 'make runserver'; \
		tmux new-window -n simulator 'make run-simulator'; \
		tmux new-window -n materializer 'make run-materializer'; \
		tmux attach-session -t wall-demo; \
	else \
		echo "tmux not found. Run 'make runserver', 'make run-simulator', and 'make run-materializer' in separate terminals."; \
	fi

run-platform: ## Start the complete platform (API gateway, simulator, and materializer)
	@echo "🚀 Starting The Wall platform..."
	@echo "This will start all services: API Gateway, Simulator, and Materializer"
	@if command -v tmux >/dev/null 2>&1; then \
		echo "Using tmux to manage multiple services..."; \
		tmux new-session -d -s wall-platform -n api 'echo "Starting API Gateway..."; make runserver'; \
		tmux new-window -t wall-platform -n simulator 'echo "Starting Simulator..."; make run-simulator'; \
		tmux new-window -t wall-platform -n materializer 'echo "Starting Materializer..."; make run-materializer'; \
		echo "✅ Platform started in tmux session 'wall-platform'"; \
		echo "Use 'tmux attach -t wall-platform' to view services"; \
		echo "Use 'tmux kill-session -t wall-platform' to stop all services"; \
		tmux attach-session -t wall-platform; \
	else \
		echo "❌ tmux not found. Please install tmux or run these commands in separate terminals:"; \
		echo "  Terminal 1: make runserver"; \
		echo "  Terminal 2: make run-simulator"; \
		echo "  Terminal 3: make run-materializer"; \
	fi

test: ## Run all tests (including Django API tests)
	@echo "🧪 Running all tests (unit + API)..."
	PYTHONPATH=thewall DJANGO_SETTINGS_MODULE=thewall.settings.test poetry run python -m pytest tests/ -v --cov=shared --cov=services --cov-report=term-missing

test-all: ## Run all tests (unit, integration, and API tests)
	@echo "🧪 Running complete test suite (unit + API + integration)..."
	PYTHONPATH=thewall DJANGO_SETTINGS_MODULE=thewall.settings.test poetry run python -m pytest tests/ -v --cov=shared --cov=services --cov-report=term-missing
	@echo "✅ All tests completed!"

test-unit: ## Run unit tests only (no database required)
	PYTHONPATH=. poetry run python -m pytest tests/ --ignore=tests/test_api_gateway.py -v

test-core: ## Run core tests (unit tests + stable API tests)
	@echo "🧪 Running core test suite (unit + stable API tests)..."
	@echo "Running unit tests..."
	PYTHONPATH=. poetry run python -m pytest tests/ --ignore=tests/test_api_gateway.py -v --cov=shared --cov=services --cov-report=term-missing
	@echo ""
	@echo "Running stable API tests..."
	cd thewall && PYTHONPATH=.. DJANGO_SETTINGS_MODULE=thewall.settings.test poetry run python -m pytest ../tests/test_api_gateway.py -v -k "not KafkaPublisher and not test_readiness_check_healthy and not test_list_profiles"
	@echo "✅ Core tests completed!"

test-api: ## Run API tests only (requires database)
	cd thewall && PYTHONPATH=.. DJANGO_SETTINGS_MODULE=thewall.settings.test poetry run python -m pytest ../tests/test_api_gateway.py -v -k "not KafkaPublisher and not test_readiness_check_healthy"

test-watch: ## Run tests in watch mode (reruns on file changes)
	@echo "📝 Running tests in watch mode..."
	@echo "Note: This requires pytest-watch to be installed (pip install pytest-watch)"
	PYTHONPATH=. poetry run python -m pytest tests/ -v --looponfail

lint: ## Run linting and formatting checks
	poetry run ruff check . --exclude benchmark_tool.py --exclude infrastructure/ --exclude benchmarks/
	poetry run black --check . --exclude benchmark_tool.py --exclude infrastructure/ --exclude benchmarks/
	poetry run mypy . --exclude benchmark_tool.py --exclude infrastructure/ --exclude benchmarks/

format: ## Format code
	poetry run black . --exclude benchmark_tool.py --exclude infrastructure/ --exclude benchmarks/
	poetry run ruff check --fix . --exclude benchmark_tool.py --exclude infrastructure/ --exclude benchmarks/

clean: ## Clean up build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -f db.sqlite3

# Docker commands
dev: ## Start the full stack with Docker Compose
	docker-compose up --build

dev-detached: ## Start the full stack in background
	docker-compose up --build -d

stop: ## Stop all Docker services
	docker-compose down

logs: ## Show logs from all services
	docker-compose logs -f

logs-api: ## Show API logs
	docker-compose logs -f api

logs-simulator: ## Show simulator logs
	docker-compose logs -f simulator

logs-materializer: ## Show materializer logs
	docker-compose logs -f materializer

clean-docker: ## Clean Docker containers and volumes
	docker-compose down -v
	docker system prune -f

# Environment variables for PostgreSQL
export-pg: ## Export PostgreSQL environment variables
	@echo "export USE_SQLITE=False"
	@echo "export DB_NAME=wall"
	@echo "export DB_USER=wall"
	@echo "export DB_PASSWORD=wall"
	@echo "export DB_HOST=localhost"
	@echo "export DB_PORT=5432"

# Environment variables for SQLite (default)
export-sqlite: ## Export SQLite environment variables
	@echo "export USE_SQLITE=True"

# Documentation commands
docs-serve: ## Serve documentation locally
	mkdocs serve

docs-build: ## Build documentation
	mkdocs build --clean

docs-deploy: ## Deploy documentation (if configured)
	mkdocs gh-deploy

# Benchmark commands
benchmark-comprehensive: ## Run comprehensive benchmark with profile creation and testing
	@echo "🏰 Starting comprehensive benchmark..."
	@./run_benchmark.sh

benchmark-tool: ## Run the Python benchmark tool
	@echo "🐍 Running Python benchmark tool..."
	@python3 benchmark_tool.py

benchmark-tool-quick: ## Run quick benchmark with the Python tool
	@echo "🚀 Running quick benchmark..."
	@python3 benchmark_tool.py --quick

# Additional utility commands
check-deps: ## Check if all required dependencies are installed
	@echo "🔍 Checking dependencies..."
	@command -v poetry >/dev/null 2>&1 || { echo "❌ Poetry not found. Please install Poetry first."; exit 1; }
	@command -v docker >/dev/null 2>&1 || { echo "❌ Docker not found. Please install Docker first."; exit 1; }
	@command -v docker-compose >/dev/null 2>&1 || { echo "❌ Docker Compose not found. Please install Docker Compose first."; exit 1; }
	@echo "✅ All required dependencies found!"

status: ## Show status of all services
	@echo "📊 Service Status:"
	@echo "==================="
	@if pgrep -f "manage.py runserver" > /dev/null 2>&1; then \
		echo "✅ API Gateway: Running (PID: $$(pgrep -f 'manage.py runserver'))"; \
	else \
		echo "❌ API Gateway: Not running"; \
	fi
	@if pgrep -f "services/simulator/cli.py" > /dev/null 2>&1; then \
		echo "✅ Simulator: Running (PID: $$(pgrep -f 'services/simulator/cli.py'))"; \
	else \
		echo "❌ Simulator: Not running"; \
	fi
	@if pgrep -f "manage.py run_materializer" > /dev/null 2>&1; then \
		echo "✅ Materializer: Running (PID: $$(pgrep -f 'manage.py run_materializer'))"; \
	else \
		echo "❌ Materializer: Not running"; \
	fi
	@echo ""
	@echo "Tmux sessions:"
	@tmux list-sessions 2>/dev/null | grep -E "(wall-platform|wall-demo)" || echo "No wall-related tmux sessions found"

stop-platform: ## Stop all platform services
	@echo "🛑 Stopping The Wall platform..."
	@pkill -f "manage.py runserver" 2>/dev/null || true
	@pkill -f "services/simulator/cli.py" 2>/dev/null || true
	@pkill -f "manage.py run_materializer" 2>/dev/null || true
	@tmux kill-session -t wall-platform 2>/dev/null || true
	@tmux kill-session -t wall-demo 2>/dev/null || true
	@echo "✅ Platform stopped!"

quick-start: setup run-platform ## Complete setup and start platform in one command
	@echo "🎉 The Wall platform is ready!"
