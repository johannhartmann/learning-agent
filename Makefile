.PHONY: help install install-dev test test-cov lint format typecheck check clean run dev docs serve-docs build pre-commit

# Variables
PYTHON := python
UV := uv
SRC_DIR := src/learning_agent
TEST_DIR := tests
COV_REPORT := htmlcov

# Default target
help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

install: ## Install production dependencies
	$(UV) sync

install-dev: ## Install all dependencies including dev
	$(UV) sync --all-extras

test: ## Run tests
	$(UV) run pytest $(TEST_DIR) -v

test-unit: ## Run only unit tests
	$(UV) run pytest $(TEST_DIR)/test_basic.py -v

test-integration: ## Run only integration tests
	$(UV) run pytest $(TEST_DIR)/test_integration.py -v

test-cov: ## Run tests with coverage report
	$(UV) run pytest $(TEST_DIR) \
		--cov=$(SRC_DIR) \
		--cov-report=term-missing \
		--cov-report=html:$(COV_REPORT) \
		--cov-report=xml \
		-v

test-fast: ## Run tests without slow integration tests
	$(UV) run pytest $(TEST_DIR) -v -m "not slow"

test-parallel: ## Run tests in parallel
	$(UV) run pytest $(TEST_DIR) -v -n auto

lint: ## Run ruff linter
	$(UV) run ruff check $(SRC_DIR) $(TEST_DIR)

format: ## Format code with ruff
	$(UV) run ruff format $(SRC_DIR) $(TEST_DIR)
	$(UV) run ruff check --fix $(SRC_DIR) $(TEST_DIR)

typecheck: ## Run mypy type checker
	$(UV) run mypy $(SRC_DIR)

deadcode: ## Find dead code with vulture
	$(UV) run vulture $(SRC_DIR) $(TEST_DIR) vulture-whitelist.py --config .vulture.ini || true

check: ## Run all checks (lint, typecheck, deadcode, tests)
	@echo "Running linter..."
	@$(MAKE) lint
	@echo "\nRunning type checker..."
	@$(MAKE) typecheck
	@echo "\nChecking for dead code..."
	@$(MAKE) deadcode
	@echo "\nRunning tests..."
	@$(MAKE) test

clean: ## Clean up generated files
	rm -rf $(COV_REPORT)
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	find . -type f -name ".coverage.*" -delete

run: ## Run the learning agent CLI
	$(UV) run learning-agent

dev: ## Run in development mode with auto-reload
	$(UV) run python -m learning_agent.cli --dev

docs: ## Build documentation
	$(UV) run mkdocs build

serve-docs: ## Serve documentation locally
	$(UV) run mkdocs serve

build: ## Build distribution packages
	$(UV) build

pre-commit: ## Run pre-commit on all files
	$(UV) run pre-commit run --all-files

pre-commit-install: ## Install pre-commit hooks
	$(UV) run pre-commit install
	$(UV) run pre-commit install --hook-type commit-msg

update-deps: ## Update all dependencies
	$(UV) sync --upgrade

tree: ## Show project structure
	@echo "Project structure:"
	@tree -I '__pycache__|*.pyc|.git|.venv|htmlcov|.mypy_cache|.ruff_cache|.pytest_cache|*.egg-info|dist|build' --dirsfirst

watch-test: ## Watch for changes and run tests
	$(UV) run pytest-watch $(TEST_DIR) -v

benchmark: ## Run performance benchmarks
	$(UV) run pytest $(TEST_DIR)/benchmarks -v --benchmark-only

security: ## Run security checks
	$(UV) run bandit -r $(SRC_DIR) -ll

deps-graph: ## Show dependency graph
	$(UV) run pipdeptree

version: ## Show package version
	@$(PYTHON) -c "from learning_agent import __version__; print(__version__)"

langsmith-test: ## Run LangSmith probabilistic tests
	$(UV) run python tests/langsmith_eval.py

langsmith-eval: ## Run full LangSmith evaluation suite
	@echo "Running LangSmith evaluation suite..."
	$(UV) run python -m pytest tests/langsmith_eval.py -v
	@echo "Check results at: https://smith.langchain.com"

langsmith-regression: ## Create regression tests from production
	$(UV) run python -c "import asyncio; from tests.langsmith_eval import regression_test_from_traces; asyncio.run(regression_test_from_traces())"

langsmith-anomaly: ## Detect anomalies in production traces
	$(UV) run python -c "import asyncio; from tests.langsmith_eval import detect_anomalies; import json; result = asyncio.run(detect_anomalies()); print(json.dumps(result, indent=2))"

langsmith-ab: ## Run A/B testing between configurations
	$(UV) run python -c "import asyncio; from tests.langsmith_eval import ab_test_configurations; import json; result = asyncio.run(ab_test_configurations()); print(json.dumps(result, indent=2))"

## UI and Server targets
docker-build: ## Build Docker images for server and UI
	docker-compose build

docker-up: ## Start server and UI with Docker Compose
	docker-compose up -d
	@echo "Server running at: http://localhost:2024"
	@echo "UI running at: http://localhost:10300"

docker-down: ## Stop Docker containers
	docker-compose down

docker-logs: ## View Docker container logs
	docker-compose logs -f

docker-restart: ## Restart Docker containers
	docker-compose restart

docker-clean: ## Stop and remove Docker containers and volumes
	docker-compose down -v

server-dev: ## Run LangGraph server in development mode (local)
	langgraph dev --port 2024

ui-dev: ## Run UI in development mode (requires npm install in ui/)
	cd ui && npm run dev

ui-install: ## Install UI dependencies locally
	cd ui && npm install

ui-build: ## Build UI for production
	cd ui && npm run build

test-all: ## Run all test suites (unit, integration, langsmith)
	@echo "Running complete test suite..."
	@$(MAKE) test-unit
	@echo "\n--- Integration Tests ---"
	@$(MAKE) test-integration
	@echo "\n--- LangSmith Evaluation ---"
	@$(MAKE) langsmith-test
	@echo "\nAll tests completed!"

test-ci: ## Run tests for CI/CD pipeline
	@$(MAKE) lint
	@$(MAKE) typecheck
	@$(MAKE) security
	@$(MAKE) test-cov
	@echo "CI tests passed!"

init: ## Initialize project (install deps, pre-commit, etc.)
	@echo "Initializing project..."
	@$(MAKE) install-dev
	@$(MAKE) pre-commit-install
	@echo "Project initialized successfully!"

ci: ## Run CI pipeline locally
	@echo "Running CI pipeline..."
	@$(MAKE) format
	@$(MAKE) check
	@echo "CI pipeline completed successfully!"

.DEFAULT_GOAL := help
