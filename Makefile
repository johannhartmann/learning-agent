.PHONY: help build build-update up down restart logs reset check-imports

# Minimal Makefile for Docker Compose-based standalone server

help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

build: ## Build server and UI images (installs upstream deepagents)
	docker compose build server ui

build-update: ## Force rebuild server without cache (skip uv wheel cache)
	docker compose build --no-cache --build-arg UV_NO_CACHE=1 server
	docker compose build ui


up: ## Start services with Compose
	docker compose up -d
	@echo "Server running at: http://localhost:2024"
	@echo "UI running at: http://localhost:10300"

down: ## Stop Docker containers
	docker compose down

restart: ## Restart Docker containers
	docker compose restart

logs: ## View server logs
	docker compose logs -f server

ui-e2e: ## Run UI Playwright E2E tests (uses ui-test container)
	OPENAI_API_KEY=$${OPENAI_API_KEY} docker compose run --rm ui-test


reset: ## Force recreate server (clean bring-up)
	- docker compose rm -fs server test || true
	docker compose up -d
	@echo "Server running at: http://localhost:2024"
	@echo "UI running at: http://localhost:10300"

check-imports: ## Sanity-check that Postgres saver is importable inside the server container
	@docker compose run --rm server python -c "import importlib; m=importlib.import_module('langgraph.checkpoint.postgres'); print('OK postgres:', [a for a in dir(m) if 'Saver' in a])" || true
	@docker compose run --rm server python -c "import importlib; m=importlib.import_module('langgraph.checkpoint.postgres.aio'); print('OK aio:', [a for a in dir(m) if 'Saver' in a])" || true

.DEFAULT_GOAL := help
