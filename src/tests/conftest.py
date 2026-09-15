from collections.abc import AsyncGenerator, Callable

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx2 import ASGITransport, AsyncClient

from src.infra.api.app import create_app
from src.main import lifespan


@pytest_asyncio.fixture
async def app() -> AsyncGenerator[FastAPI]:
    app = create_app(lifespan=lifespan)
    async with app.router.lifespan_context(app):
        yield app


@pytest.fixture
def api_client_factory(
    app: FastAPI,
) -> Callable[..., AsyncClient]:
    def create_client(*, headers: dict[str, str] | None = None) -> AsyncClient:
        return AsyncClient(
            transport=ASGITransport(app=app, client=("testclient", 50000)),
            base_url="http://testserver",
            headers={"accept-encoding": "gzip, deflate", **(headers or {})},
        )

    return create_client


@pytest_asyncio.fixture
async def client(
    api_client_factory: Callable[..., AsyncClient],
) -> AsyncGenerator[AsyncClient]:
    async with api_client_factory() as client:
        yield client
