# Project Elena

AI LaTeX resume editor (product in early definition). See `docs/`.

- **Stack decision:** [docs/TECH_STACK.md](docs/TECH_STACK.md) (BYOK, deployable web platform)
- **First push to GitHub:** [docs/GITHUB_SETUP.md](docs/GITHUB_SETUP.md)
- **Local dev (clone → running app):** [docs/LOCAL_DEV.md](docs/LOCAL_DEV.md)

## Quickstart

**Prerequisites:** Docker, **Node 20+**, **pnpm 9**, **Python 3.12+**, [**uv**](https://docs.astral.sh/uv/).

```bash
cp .env.example .env
docker compose -f infra/compose.yaml --env-file .env up --build
curl -s http://localhost:8000/health
pnpm install
pnpm dev:web
```

The UI runs on the host; Postgres, Redis, and the FastAPI service run in Compose. Optional LaTeX image: `docker compose -f infra/compose.yaml --profile latex up latex` (see [infra/docker/README.md](infra/docker/README.md)).

## Monorepo layout (checkpoint 1.2)

| Path | Purpose |
|------|--------|
| [apps/web/](apps/web/) | Next.js (App Router, TypeScript, Tailwind) |
| [services/api/](services/api/) | Python package `elena` — FastAPI API surface (health for 1.2) |
| [skills/](skills/) | [Agent Skills](https://agentskills.io/specification) for the harness |
| [infra/](infra/) | Docker / Compose — Postgres, Redis, API; optional LaTeX profile |
| [docs/](docs/) | Product specs, template contract, LaTeX source |
| [scripts/](scripts/) | Helper scripts |

## Git branching

- **`develop`** — integration branch; open PRs from feature branches **into `develop`**.
- **`main`** — stable releases; merge **`develop` → `main`** when cutting a release, not for every feature.

Example: feature branch `checkpoint/1.2-local-dev` → PR into **`develop`**.
