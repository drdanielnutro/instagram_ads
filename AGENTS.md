# Repository Guidelines

## Project Structure & Module Organization
- `app/` — Python backend (FastAPI + Google ADK): `server.py` (API), `agent.py` (multi‑agent pipeline), `config.py`, `utils/`.
- `frontend/` — React + Vite (TypeScript). Also includes a Streamlit prototype (`streamlit_app.py`).
- `tests/` — `unit/`, `integration/`, and `load_test/` (Locust).
- `deployment/` — Terraform for dev infra. Supporting files: `Makefile`, `Dockerfile`, `pyproject.toml`.

## Build, Test, and Development Commands
- Install: `make install` (uses `uv sync` and `npm --prefix frontend install`).
- Run full stack (dev): `make dev` (backend + frontend) or `make dev-backend-all` and `npm --prefix frontend run dev`.
- Local API only: `make local-backend` (Uvicorn FastAPI reload).
- Lint & type-check: `make lint` (codespell, ruff check/format --check, mypy).
- Tests: `make test` (unit + integration). Example: `uv run pytest tests/unit -q`.

## Coding Style & Naming Conventions
- Python (3.10–3.12): 4‑space indent, type hints required; follow Ruff and MyPy configs in `pyproject.toml` (line length 88; `E501` ignored). Names: `snake_case` for functions/vars, `PascalCase` for classes, module/file names `snake_case.py`.
- TypeScript/React: follow ESLint and TS configs; `PascalCase` for components, `camelCase` for vars/functions, files `PascalCase.tsx` or `kebab-case.ts` as appropriate.
- Formatting: prefer tool defaults; do not commit auto‑formatted diffs that fight `ruff`/ESLint.

## Testing Guidelines
- Frameworks: `pytest`, `pytest-asyncio`. Put unit tests in `tests/unit`, integration/E2E in `tests/integration`. Name files `test_*.py`.
- Async tests: mark with `pytest.mark.asyncio` and keep event‑loop scope at function level (see `pyproject.toml`).
- Load tests: see `tests/load_test/README.md` and run Locust separately from app env.

## Commit & Pull Request Guidelines
- History is mixed; use Conventional Commits going forward: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`.
- PRs must include: concise description, rationale, linked issue, test coverage notes, screenshots for UI changes, and `make lint && make test` passing. Keep PRs focused and small.

## Security & Configuration Tips
- Never commit secrets. Use environment variables (see `app/.env.txt` as a reference) or GCP Application Default Credentials.
- Validate all external inputs at API boundaries; prefer Pydantic models.
- Cloud deployment uses `gcloud`/Cloud Run; ensure `PROJECT_ID` is set and avoid leaking logs with sensitive content.

## Agent‑Specific Notes
- Extend or modify the pipeline in `app/agent.py` and expose endpoints via `app/server.py`. Keep utilities in `app/utils/` with unit tests alongside behavior changes.

