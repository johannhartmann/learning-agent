# Repository Guidelines

## Project Structure & Module Organization
- Core logic lives in `src/learning_agent/`; the Typer CLI entrypoint is `cli.py`, REST surfaces live in `server.py` and `api_server.py`, and subpackages implement learning flows, tool wiring, and provider adapters.
- Tests reside in `tests/` alongside pytest fixtures; add new suites under `tests/test_<feature>.py`.
- Operational assets include the `Makefile`, `docker-compose.yml`, `Dockerfile.*`, helper `scripts/`, and the React UI under `ui/`. Copy `.env.example` when configuring new environments.

## Build, Test, and Development Commands
- `make install` installs runtime dependencies via uv; use `make install-dev` for the full contributor toolchain.
- `make dev` runs the API with auto-reload; `make run` executes the CLI entrypoint locally.
- Containers: `make docker-up` launches Postgres, API, and UI; pair with `make docker-down` or `make docker-restart` when services drift.
- Quality gates: `make lint`, `make format`, `make typecheck`, and `make security` wrap ruff, formatting, mypy, and bandit. Run `make pre-commit` before opening a PR.
- Tests: `make test` executes the suite in Docker; `make test-local` and `make test-cov-local` run pytest locally with optional coverage HTML.

## Coding Style & Naming Conventions
Target Python 3.11+, stick to ≤100-character lines, and prefer explicit type hints. Use double quotes, snake_case modules, CamelCase classes, and UPPER_SNAKE constants. Format imports and code with `make format`; add brief comments only for non-obvious logic.

## Testing Guidelines
Name test files `tests/test_<area>.py` and functions `test_*`. Keep fixtures deterministic, mark integration or slow cases with `@pytest.mark.integration` / `@pytest.mark.slow`, and ensure coverage stays healthy via `make test-cov-local` or the Docker equivalent.

## Commit & Pull Request Guidelines
Follow Conventional Commits (e.g., `feat(server): add retry guard`) and keep subjects ≤100 characters. PRs should link issues (`Closes #123`), summarize intent, flag breaking changes, and attach relevant logs or screenshots. Confirm CI is green before requesting review.

## Security & Configuration Tips
Never commit secrets. Duplicate `.env.example` to `.env` for local credentials. Use `make install-sandbox` and `make verify-sandbox` when working in the GitHub sandbox, and rebuild containers with `make docker-build` after dependency or Dockerfile updates.
