# Repository Guidelines

## Project Structure & Modules
- Source: `src/learning_agent/` (CLI `cli.py`, HTTP `server.py`/`api_server.py`, learning modules under `learning/`, tools under `tools/`, providers under `providers/`).
- Tests: `tests/` (pytest is configured via `pyproject.toml`). Prefer placing new tests in this folder.
- Ops & assets: `Makefile`, `docker-compose.yml`, `Dockerfile.*`, `scripts/`, `.env.example`, `ui/`.

## Build, Test, and Development
- Install deps: `make install` (prod) or `make install-dev` (incl. dev tools). Uses `uv`.
- Run CLI: `make run` → launches `learning-agent` Typer CLI; dev mode: `make dev` (auto‑reload).
- Test (Docker): `make test` (recommended, hermetic). Local: `make test-local` or `make test-cov-local`.
- Lint/Format: `make lint` (ruff), `make format` (ruff format + fixes).
- Types/Security: `make typecheck` (mypy), `make security` (bandit).
- Docs/UI/Server: `make docs`, `make docker-build`, `make docker-up`, `make docker-down`.

## Coding Style & Naming
- Formatter/Linter: ruff (line length 100, double quotes). Run `make format` before pushing.
- Typing: Python 3.11+, add type hints where practical; mypy is configured but tolerant for complex providers.
- Naming: packages/modules `snake_case`, classes `CamelCase`, functions/vars `snake_case`, constants `UPPER_SNAKE`.
- Imports: prefer absolute imports within `learning_agent`; keep ordering via ruff (isort rules).

## Testing Guidelines
- Framework: pytest. Place files as `tests/test_<area>.py`; functions `test_*`.
- Markers: `@pytest.mark.integration`, `@pytest.mark.slow` as appropriate.
- Coverage: `make test-cov-local` (local) or `make test-cov` (Docker) → report in `htmlcov/`.
- Parallel/fast loops: `make test-parallel-local`, `make test-fast-local`.

## Commit & Pull Requests
- Conventional Commits enforced by commitlint (e.g., `feat: add vector storage`, `fix(server): handle 500s`).
- Keep subject ≤ 100 chars; write a concise body when needed.
- Before opening a PR: run `make pre-commit` and ensure CI green (lint, typecheck, tests).
- PRs should include: clear description, linked issues (e.g., `Closes #123`), screenshots for UI, and notes on breaking changes.

## Security & Configuration
- Never commit secrets. Copy `.env.example` to `.env` locally; document new vars in the example file.
- Sandbox: use `make install-sandbox` and `make verify-sandbox` to ensure the GitHub sandbox package is used.
- Containers: prefer Docker targets when tests rely on external services.

## Make & Docker: Build/Start/Stop
- Prerequisites:
  - Install Docker and Docker Compose.
  - Copy `.env.example` to `.env` and fill required keys:
    - `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `LANGSMITH_API_KEY` (optional), `LLM_PROVIDER`, `LLM_MODEL`.
  - Optional local tools: `uv` (installed by `make install`/`make install-dev`).

- Build images (server, UI, tests):
  - With Make: `make docker-build`
  - Directly: `docker-compose build`

- Start services (Postgres, server, UI):
  - With Make: `make docker-up`
  - Directly: `docker-compose up -d`
  - URLs: server `http://localhost:2024`, UI `http://localhost:10300`

- View logs (follow):
  - With Make: `make docker-logs`
  - Directly: `docker-compose logs -f`
  - Single service: `docker-compose logs -f server` (or `postgres`, `ui`, `test`).

- Stop services:
  - With Make: `make docker-down`
  - Directly: `docker-compose down`

- Restart services:
  - With Make: `make docker-restart`
  - Directly: `docker-compose restart`

- Clean up everything (containers + volumes):
  - With Make: `make docker-clean`
  - Directly: `docker-compose down -v`

- Rebuild after changes:
  - App code under `./src` is mounted into containers, so code edits reflect without rebuild.
  - After dependency or Dockerfile changes, rebuild: `make docker-build`.

- Start specific services only (direct Docker Compose):
  - Server + DB: `docker-compose up -d postgres server`
  - UI only (server must be up): `docker-compose up -d ui`

- Local (non-Docker) run options:
  - CLI: `make run` (Typer CLI `learning-agent`).
  - Dev mode: `make dev` (auto-reload), `make ui-dev` for UI, `make server-dev` for LangGraph server.

- Testing in Docker (optional):
  - Full suite: `make test`
  - Coverage: `make test-cov`

- Ports and env summary:
  - Server: `2024` (API) and `8001` (LangGraph UI/debug).
  - UI: `10300` → proxies to server at `http://localhost:2024`.
  - Postgres: host `5433` → container `5432`.
  - DB URL in containers: `postgresql://learning_agent:learning_agent_pass@postgres:5432/learning_memories`.

- Troubleshooting:
  - If server healthcheck fails, ensure `.env` keys are set and `postgres` is healthy.
  - Reset state: `make docker-clean` to remove volumes, then `make docker-up`.
  - Check service health: `docker ps`, `docker-compose ps`, and service logs.
