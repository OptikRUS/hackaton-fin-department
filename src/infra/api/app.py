from dishka.integrations.fastapi import setup_dishka as setup_dishka_fastapi
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.types import Lifespan

from src.config.settings import settings
from src.di.container import create_container
from src.infra.api.exceptions import exception_handlers
from src.infra.api.routers import root_router


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
    return app
