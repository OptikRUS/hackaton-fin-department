from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from src.config.settings import settings
from src.infra.api.app import create_app


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    container = app.state.dishka_container
    yield
    await container.close()


def start_service() -> None:
    uvicorn.run(
        app=create_app(lifespan=lifespan),
        host=settings.APP.ADDRESS,
        port=settings.APP.PORT,
        access_log=True,
    )


if __name__ == "__main__":
    start_service()
