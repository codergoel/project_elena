# Infra — Docker / Compose

- **`compose.yaml`** (repo root: `infra/compose.yaml`) — Postgres, Redis, API, and optional services.
- **`docker/latex/`** — minimal TeX Live image (`texlive-latex-base`) for local PDF builds.

## LaTeX image (optional)

Not started by default. Build and run with the Compose profile:

```bash
docker compose -f infra/compose.yaml build latex
docker compose -f infra/compose.yaml --profile latex up latex
```

Check `pdflatex` inside the container:

```bash
docker compose -f infra/compose.yaml run --rm latex pdflatex --version
```

See [docs/TECH_STACK.md](../../docs/TECH_STACK.md).
