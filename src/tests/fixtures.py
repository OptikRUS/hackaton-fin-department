import pytest_asyncio
from httpx2 import AsyncClient as HTTPAsyncClient

from src.tests.helpers.api import APIHelper


class APIFixture:
    api: APIHelper

    @pytest_asyncio.fixture(autouse=True)
    async def _api_setup(
        self,
        client: HTTPAsyncClient,
    ) -> None:
        self.api = APIHelper(client=client)
