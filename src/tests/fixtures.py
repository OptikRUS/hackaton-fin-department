import pytest
import pytest_asyncio
from dishka import AsyncContainer
from httpx2 import AsyncClient as HTTPAsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.tests.helpers.api import APIHelper
from src.tests.helpers.container import ContainerHelper
from src.tests.helpers.factory import FactoryHelper
from src.tests.helpers.postgres import PostgresHelper


class FactoryFixture:
    factory: FactoryHelper

    @pytest.fixture(autouse=True)
    def _factory_setup(self) -> None:
        self.factory = FactoryHelper()


class APIFixture:
    api: APIHelper

    @pytest_asyncio.fixture(autouse=True)
    async def _api_setup(self, client: HTTPAsyncClient) -> None:
        self.api = APIHelper(client=client)


class ContainerFixture:
    container_helper: ContainerHelper

    @pytest.fixture(autouse=True)
    def _container_setup(self, container: AsyncContainer) -> None:
        self.container_helper = ContainerHelper(container=container)


class PostgresFixture:
    postgres_helper: PostgresHelper

    @pytest.fixture(autouse=True)
    def _postgres_setup(self, session: AsyncSession) -> None:
        self.postgres_helper = PostgresHelper(session=session)
