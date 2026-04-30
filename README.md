# Project Elena

AI LaTeX resume editor (product in early definition). See `docs/`.

- **Stack decision:** [docs/TECH_STACK.md](docs/TECH_STACK.md) (BYOK, deployable web platform)
- **First push to GitHub:** [docs/GITHUB_SETUP.md](docs/GITHUB_SETUP.md)

## Monorepo layout (checkpoint 1.1)

| Path | Purpose |
|------|--------|
| [apps/web/](apps/web/) | Next.js frontend (placeholder; scaffold in checkpoint 1.2) |
| [services/api/](services/api/) | Python package `elena` — FastAPI + Deep Agents (HTTP in later checkpoints) |
| [skills/](skills/) | [Agent Skills](https://agentskills.io/specification) for the harness |
| [infra/](infra/) | Docker / Compose stubs; Postgres + Redis in `compose.yaml` |
| [docs/](docs/) | Product specs, template contract, LaTeX source |
| [scripts/](scripts/) | Helper scripts |

**Prerequisites:** Node **20+**, **pnpm 9**, **Python 3.12+**, [**uv**](https://docs.astral.sh/uv/).

**Local dependencies (optional):**

```bash
docker compose -f infra/compose.yaml up -d
```

## Git branching

- **`develop`** — integration branch; open PRs from feature branches **into `develop`**.
- **`main`** — stable releases; merge **`develop` → `main`** when cutting a release, not for every feature.

Example: feature branch `checkpoint/1.1-monorepo-layout` → PR into **`develop`**.
