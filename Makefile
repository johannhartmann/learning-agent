.PHONY: help build up down restart logs reset check-imports

# Minimal Makefile for Docker Compose-based LangGraph standalone server

IMAGE ?= learning_agent_server:latest

help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

build: ## Build server image via LangGraph CLI (reads langgraph.json). Optionally: make build IMAGE=repo/name:tag
	@echo "Building LangGraph server image (tag: $(IMAGE))..."
	@if command -v langgraph >/dev/null 2>&1; then langgraph build -t $(IMAGE); else python -m langgraph_cli build -t $(IMAGE); fi
	@echo "✅ Built LangGraph server image: $(IMAGE)"

up: ## Start services with Compose using IMAGE
	LG_SERVER_IMAGE=$(IMAGE) docker-compose up -d
	@echo "Server running at: http://localhost:2024"
	@echo "UI running at: http://localhost:10300"

down: ## Stop Docker containers
	docker-compose down

restart: ## Restart Docker containers
	LG_SERVER_IMAGE=$(IMAGE) docker-compose restart

logs: ## View server logs
	LG_SERVER_IMAGE=$(IMAGE) docker-compose logs -f server

reset: ## Force recreate server (workaround compose 'ContainerConfig' errors)
	- docker-compose rm -fs server test
	LG_SERVER_IMAGE=$(IMAGE) docker-compose up -d
	@echo "Server running at: http://localhost:2024"
	@echo "UI running at: http://localhost:10300"

check-imports: ## Sanity-check that Postgres saver is importable inside the server image
	@docker run --rm -i $(IMAGE) python -c "import importlib; m=importlib.import_module('langgraph.checkpoint.postgres'); print('OK postgres:', [a for a in dir(m) if 'Saver' in a])" || true
	@docker run --rm -i $(IMAGE) python -c "import importlib; m=importlib.import_module('langgraph.checkpoint.postgres.aio'); print('OK aio:', [a for a in dir(m) if 'Saver' in a])" || true

.DEFAULT_GOAL := help
