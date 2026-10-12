# Repository Guidelines

## Project Structure & Module Organization

This repository contains a Python 3.12 package for resolving Atera alert-generated tickets after the related alerts are resolved.

- `src/atera_sync/` contains the application code.
- `src/atera_sync/cli.py` defines the Typer CLI entry points.
- `src/atera_sync/api.py` handles Atera API access and retry behavior.
- `src/atera_sync/sync.py` contains the main alert-to-ticket resolution workflow.
- `src/atera_sync/extract.py` contains payload extraction helpers.
- `tests/` contains pytest tests.
- `fixtures/` is created by runtime/test commands and stores sampled Atera payloads.
- `Dockerfile` and `docker-compose.yml` package and run the CLI in a container.

## Build, Test, and Development Commands

Create a local environment and install the package:

```bash
uv venv
uv pip install -e .
```

Without `uv`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Run tests:

```bash
pytest
```

Run the required Atera connectivity test:

```bash
atera-sync test
docker compose run --rm atera-sync test
```

Run the sync locally or in Docker:

```bash
atera-sync run 100 14
docker compose run --rm atera-sync run 100 14
```

## Coding Style & Naming Conventions

Use standard Python formatting with 4-space indentation, type hints for public functions, and `from __future__ import annotations` where helpful. Use `snake_case` for functions, variables, and modules. Keep CLI command names short and kebab-style when exposed through Typer, such as `alert-sample` and `alerts-export`.

Prefer explicit status checks, structured log fields, and small helper functions for parsing Atera payloads. Do not add broad refactors when changing a targeted sync rule.

## Testing Guidelines

Tests use `pytest` with quiet output configured in `pyproject.toml`. Name tests `test_<behavior>.py` or `test_<specific_behavior>` and keep fake clients deterministic. Add or update tests when changing ticket filtering, alert severity rules, terminal status handling, comments, or API pagination behavior.

Live Atera commands require `.env` values and may write JSON under `fixtures/`; do not depend on live API calls for normal unit tests. The `test` command reads tickets, while `run` can add comments and resolve tickets.

## Commit & Pull Request Guidelines

Recent history uses concise Conventional Commit-style prefixes, for example `docs:`, `feat:`, and `fix:`. Keep commits focused and describe the observable behavior changed.

Pull requests should include a short summary, test results, configuration impact, and any operational change to scheduling, `.env` requirements, Docker commands, or Atera ticket behavior.

## Security & Configuration Tips

Do not commit `.env`, API tokens, technician IDs tied to sensitive environments, or raw customer data. Redact fixture payloads before sharing. Required runtime settings are `ATERA_API_TOKEN` and `ATERA_TECHNICIAN_ID`; `ATERA_TECHNICIAN_EMAIL` is optional. The client sends `ATERA_API_TOKEN` in the `Authorization: Bearer <token>` header. The legacy `ATERA_API_KEY` setting is not used.
