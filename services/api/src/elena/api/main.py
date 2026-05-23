"""FastAPI application wiring (health, OpenAPI, v1 routers, lifespan hooks)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from elena.api.middleware.access_metrics import AccessMetricsMiddleware
from elena.api.middleware.request_id import RequestIDMiddleware
from elena.api.routers import agent as agent_router
from elena.api.routers import bases as bases_router
from elena.api.routers import conversation as conversation_router
from elena.api.routers import downloads as downloads_router
from elena.api.routers import guided as guided_router
from elena.api.routers import import_routes as import_router
from elena.api.routers import pdf_routes as pdf_router
from elena.api.routers import resume_alias as resume_alias_router
from elena.api.routers import variants as variants_router
from elena.config import get_settings
from elena.db.session import configure_engine, dispose_db
from elena.redis_client import configure_redis, dispose_redis


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_engine(settings.database_url)
    configure_redis(settings.redis_url)
    settings.blob_storage_root.mkdir(parents=True, exist_ok=True)

    app.state.agent_checkpoint_pool = None
    app.state.agent_checkpointer = None
    app.state.agent_graph = None

    gemini_key = (settings.gemini_api_key or "").strip()
    if gemini_key:
        import logging

        log = logging.getLogger("elena.api")
        from psycopg_pool import AsyncConnectionPool as _PgPool

        pool: _PgPool | None = None
        try:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
            from psycopg.rows import dict_row

            from elena.agent.graph import compile_resume_editor_agent

            pool = _PgPool(
                conninfo=settings.psycopg_checkpoint_conninfo,
                kwargs={
                    "autocommit": True,
                    "prepare_threshold": 0,
                    "row_factory": dict_row,
                },
                min_size=1,
                max_size=12,
                open=True,
                timeout=60.0,
            )
            checkpointer = AsyncPostgresSaver(pool)  # type: ignore[arg-type]
            await checkpointer.setup()
            graph = compile_resume_editor_agent(
                settings=settings,
                checkpointer=checkpointer,
            )
            app.state.agent_checkpoint_pool = pool
            app.state.agent_checkpointer = checkpointer
            app.state.agent_graph = graph
            pool = None  # pooled connections closed at app shutdown
        except Exception:
            log.exception("Editor agent disabled: LangGraph Postgres checkpointer failed to initialise")
            if pool is not None:
                await pool.close()
            app.state.agent_checkpoint_pool = None
            app.state.agent_checkpointer = None
            app.state.agent_graph = None

    yield

    pool = getattr(app.state, "agent_checkpoint_pool", None)
    if pool is not None:
        await pool.close()

    await dispose_db()
    await dispose_redis()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Elena API", version="0.1.0", lifespan=lifespan)

    cors_origins = settings.cors_origins_list
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["X-Request-ID"],
        )

    app.add_middleware(AccessMetricsMiddleware)

    app.add_middleware(RequestIDMiddleware)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/")
    def root() -> dict[str, str]:
        return {"service": "elena-api", "docs": "/docs"}

    @app.get("/metrics", include_in_schema=False)
    def prometheus_metrics() -> Response:
        settings = get_settings()
        if not settings.expose_prometheus_metrics:
            raise HTTPException(status_code=404, detail="metrics disabled")
        payload = generate_latest()
        return Response(content=payload, media_type=CONTENT_TYPE_LATEST)

    v1_prefix = "/api/v1"

    app.include_router(bases_router.router, prefix=v1_prefix)
    app.include_router(variants_router.router, prefix=v1_prefix)
    app.include_router(pdf_router.router, prefix=v1_prefix)
    app.include_router(conversation_router.router, prefix=v1_prefix)
    app.include_router(agent_router.router, prefix=v1_prefix)
    app.include_router(resume_alias_router.router, prefix=v1_prefix)
    app.include_router(downloads_router.router, prefix=v1_prefix)
    app.include_router(guided_router.router, prefix=v1_prefix)
    app.include_router(import_router.router, prefix=v1_prefix)

    return app


app = create_app()
