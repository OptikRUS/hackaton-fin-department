from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from dishka import AsyncContainer, make_async_container
from dishka.integrations.fastapi import FastapiProvider, setup_dishka
from fastapi import FastAPI
from httpx2 import ASGITransport, AsyncClient
from sqlalchemy import NullPool, delete
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from src.config.settings import settings
from src.infra.api.app import create_app
from src.infra.migrations.commands import downgrade, migrate
from src.infra.storages.postgres.config import async_session
from src.infra.storages.postgres.models import PetModel, SnapshotHeadModel, SnapshotUploadModel
from src.infra.storages.postgres.pet_storage import PostgresPetStorage
from src.infra.storages.postgres.snapshot_storage import PostgresSnapshotStorage
from src.tests.di.providers.general import MockGeneralProvider
from src.tests.di.providers.pets import MockPetsUseCaseProvider
from src.tests.di.providers.snapshots import MockSnapshotsUseCaseProvider


@pytest.fixture(scope="session", autouse=True)
def setup_postgres_migrations() -> Generator[None]:
    migrate("heads", settings.POSTGRES.DSN.get_secret_value())
    yield
    downgrade("base", settings.POSTGRES.DSN.get_secret_value())


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def engine() -> AsyncGenerator[AsyncEngine]:
    engine = create_async_engine(settings.POSTGRES.DSN.get_secret_value(), poolclass=NullPool)
    yield engine
    await engine.dispose()


@pytest.fixture
async def clear_tables(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.execute(delete(SnapshotUploadModel))
        await connection.execute(delete(SnapshotHeadModel))
        await connection.execute(delete(PetModel))


@pytest.fixture
async def session(engine: AsyncEngine, clear_tables: None) -> AsyncGenerator[AsyncSession]:
    _ = clear_tables
    async with async_session(bind=engine) as db_session:
        yield db_session
        await db_session.commit()


@pytest.fixture
def pet_storage(session: AsyncSession) -> PostgresPetStorage:
    return PostgresPetStorage(session=session)


@pytest.fixture
def snapshot_storage(session: AsyncSession) -> PostgresSnapshotStorage:
    return PostgresSnapshotStorage(session=session)


@pytest.fixture
async def container() -> AsyncGenerator[AsyncContainer]:
    container = make_async_container(
        FastapiProvider(),
        MockPetsUseCaseProvider(),
        MockSnapshotsUseCaseProvider(),
        MockGeneralProvider(),
    )
    yield container
    await container.close()


@pytest.fixture
def app() -> FastAPI:
    return create_app()


@pytest_asyncio.fixture
async def client(app: FastAPI, container: AsyncContainer) -> AsyncGenerator[AsyncClient]:
    setup_dishka(container=container, app=app)
    async with AsyncClient(
        transport=ASGITransport(app=app, client=("testclient", 50000)),
        base_url="http://testserver",
        headers={"accept-encoding": "gzip, deflate"},
    ) as client:
        yield client
