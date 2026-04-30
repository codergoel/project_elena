"""FastAPI application entrypoint."""

from fastapi import FastAPI

app = FastAPI(title="Elena API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe for orchestration and local checks."""
    return {"status": "ok"}


@app.get("/")
def root() -> dict[str, str]:
    """Service metadata."""
    return {"service": "elena-api", "docs": "/docs"}
