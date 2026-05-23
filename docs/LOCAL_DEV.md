# Local development

## Prerequisites

- **Docker** and Docker Compose v2
- **Node.js 20+** and **pnpm 9** (see root `package.json` `packageManager`)
- **Python 3.12+** and [**uv**](https://docs.astral.sh/uv/) (for the API outside Docker)

## Environment

From the repo root:

```bash
cp .env.example .env
```

Edit `.env` if you need to change ports or credentials. Default values match `infra/compose.yaml`.

**Compose loads variable substitution from your shell or from `--env-file`.** The repo root is not always the Compose “project directory” when using `-f infra/compose.yaml`, so passing the file explicitly avoids surprises:

```bash
docker compose -f infra/compose.yaml --env-file .env up --build
```

If you omit `--env-file`, the `api` service still gets sensible defaults for `DATABASE_URL` and `REDIS_URL` defined in the Compose file.

## Backend stack (Postgres, Redis, API)

```bash
docker compose -f infra/compose.yaml --env-file .env up --build
```

Health check:

```bash
curl -s http://localhost:8000/health
```

Expect `{"status":"ok"}` (or similar JSON).

### Port clashes

Postgres, Redis, and the API publish **5432**, **6379**, and **8000** on the host. If another project uses those ports, change host mappings in `infra/compose.yaml` or stop the conflicting services.

### API on the host (optional)

You can run Postgres and Redis in Compose and start the API with uv:

```bash
cd services/api
uv sync
DATABASE_URL=postgresql+asyncpg://elena:elena_dev@localhost:5432/elena \
REDIS_URL=redis://localhost:6379/0 \
uv run alembic upgrade head
AUTH_MODE=development \
FILE_DOWNLOAD_SIGNING_SECRET=dev-insecure-download-secret-change-me \
PUBLIC_API_BASE_URL=http://localhost:8000 \
DATABASE_URL=postgresql+asyncpg://elena:elena_dev@localhost:5432/elena \
REDIS_URL=redis://localhost:6379/0 \
uv run uvicorn elena.api.main:app --reload --host 0.0.0.0 --port 8000
```

REST routes live under **`/api/v1`** (e.g. `/api/v1/bases`). Health remains at **`/health`** on the ASGI root.

## Frontend (Next.js)

From the repo root:

```bash
pnpm install
pnpm dev:web
```

Set `NEXT_PUBLIC_API_URL` in `.env` (see `.env.example`) so the browser can reach the API.

## CI (GitHub Actions)

Workflow: [`.github/workflows/ci.yaml`](../.github/workflows/ci.yaml). It runs on **push** and **pull_request** targeting **`develop`** and **`main`**.

| Area | What runs |
|------|-----------|
| **Web** | `pnpm install --frozen-lockfile`, `pnpm lint`, `pnpm typecheck`, `pnpm build:web` |
| **API** | `uv sync --frozen --all-groups`, `alembic upgrade head`, Ruff (lint + format check), mypy, pytest defaults, `-m integration`, `-m latex` (against service Postgres/Redis); host job installs TeX tools for PDF golden tier |
| **Docker** | Build API image (`services/api/Dockerfile`) and LaTeX image (`infra/docker/latex/Dockerfile`) without pushing |

**Mirror locally (approximate):**

```bash
# repo root
pnpm install --frozen-lockfile && pnpm lint && pnpm typecheck && pnpm build:web

cd services/api
uv sync --all-groups
uv run alembic upgrade head   # optional: only if Postgres matches .env DATABASE_URL
uv run ruff check src tests && uv run ruff format --check src tests
uv run mypy && uv run pytest
uv run pytest -o addopts= -m integration
uv run pytest -o addopts= -m latex   # optional: needs pdflatex on PATH unless TeX-less
```

## Optional LaTeX container

```bash
docker compose -f infra/compose.yaml --profile latex up latex
```

See [infra/docker/README.md](../infra/docker/README.md).
