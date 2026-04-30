# services/api

FastAPI + **Deep Agents** / LangGraph API for Project Elena.

- Python package import path: `elena`, `elena.agent`, `elena.api`
- Managed with [**uv**](https://docs.astral.sh/uv/)

## Local (host)

Dependencies and Postgres/Redis via Compose at repo root:

```bash
cd services/api
uv sync
uv run uvicorn elena.api.main:app --reload --host 0.0.0.0 --port 8000
```

Open [http://localhost:8000/health](http://localhost:8000/health) and [http://localhost:8000/docs](http://localhost:8000/docs).

## Tests and lint (dev)

```bash
cd services/api
uv sync --all-groups
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy
uv run pytest
```

Same checks run in CI (see repo `.github/workflows/ci.yaml`).

## Docker

From repository root (with Compose wiring in checkpoint 1.2):

```bash
docker build -t elena-api -f services/api/Dockerfile services/api
docker run --rm -p 8000:8000 elena-api
```

Or use `infra/compose.yaml` after the `api` service is enabled.
