# Repository Guidelines

## Project Structure & Module Organization
Source code lives in `src/learning_agent/`, including the Typer CLI in `cli.py`, HTTP entry points in `server.py` and `api_server.py`, and subpackages for learning flows, tools, and providers. Tests belong in `tests/` and use pytest by default. Operational assets such as `Makefile`, `docker-compose.yml`, `Dockerfile.*`, `scripts/`, `.env.example`, and the frontend under `ui/` support local and container workflows.

## Build, Test, and Development Commands
- `make install` / `make install-dev` install runtime or full dev dependencies through uv.
- `make run` starts the `learning-agent` CLI; `make dev` launches auto-reload for iterative work.
- `make docker-up` brings up Postgres, API, and UI; pair with `make docker-down` or `make docker-restart` to manage services.
- `make test` executes the pytest suite in Docker; `make test-local` and `make test-cov-local` run locally with optional coverage HTML.
- `make lint`, `make format`, `make typecheck`, and `make security` run ruff, formatting, mypy, and bandit respectively.

## Coding Style & Naming Conventions
Target Python 3.11+, prefer explicit type hints where practical, and keep line length ≤100 characters. Use double quotes, snake_case modules, CamelCase classes, and UPPER_SNAKE constants. Ruff enforces import ordering and formatting (`make format`). Keep comments focused on complex blocks rather than obvious assignments.

## Testing Guidelines
Write pytest tests in files named `tests/test_<area>.py` with functions `test_*`. Use markers such as `@pytest.mark.integration` or `@pytest.mark.slow` when applicable. Aim to keep coverage healthy via `make test-cov-local` or `make test-cov`; inspect `htmlcov/` for gaps. Prefer fast, deterministic fixtures and reset state between tests.

## Commit & Pull Request Guidelines
Follow Conventional Commits (e.g., `feat(server): add retry guard`) with ≤100 character subjects. Before pushing, run `make pre-commit` to cover lint, typing, and tests. Pull requests should link relevant issues (`Closes #123`), summarize intent, call out breaking changes, and include screenshots or logs for UX/API shifts. Ensure CI remains green before requesting review.

## Security & Configuration Tips
Never commit secrets; copy `.env.example` to `.env` and populate required API keys locally. Use `make install-sandbox` and `make verify-sandbox` when working with the GitHub sandbox. Rebuild containers (`make docker-build`) after dependency or Dockerfile updates, and use `make docker-clean` to reset volumes when services drift.
