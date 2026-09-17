from dishka.integrations.fastapi import setup_dishka as setup_dishka_fastapi
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from starlette.types import Lifespan

from src.config.settings import settings
from src.di.container import create_container
from src.infra.api.exceptions import exception_handlers
from src.infra.api.routers import root_router
from src.infra.observability.metrics import EXCLUDED_URLS, create_metrics_asgi_app
from src.infra.observability.tracing import setup_tracing
from src.infra.storages.postgres.config import async_engine

_observability_configured = False


def setup_observability(app: FastAPI) -> None:
    global _observability_configured  # noqa: PLW0603
    app.mount(path="/metrics", app=create_metrics_asgi_app())
    if not _observability_configured:
        setup_tracing()
        FastAPIInstrumentor().instrument_app(app, excluded_urls=EXCLUDED_URLS)
        SQLAlchemyInstrumentor().instrument(engine=async_engine.sync_engine)
        _observability_configured = True


def create_app(lifespan: Lifespan | None = None) -> FastAPI:
    app = FastAPI(
        title=settings.APP.NAME,
        version=settings.APP.VERSION,
        exception_handlers=exception_handlers,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS.ALLOW_ORIGINS,
        allow_methods=settings.CORS.ALLOW_METHODS,
        allow_headers=settings.CORS.ALLOW_HEADERS,
    )
    app.include_router(router=root_router)
    container = create_container()
    setup_dishka_fastapi(container=container, app=app)
    setup_observability(app)
    return app
