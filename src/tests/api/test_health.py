from httpx2 import codes

from src.tests.fixtures import APIFixture


class TestHealthAPI(APIFixture):
    async def test_health_returns_ok(self) -> None:
        response = await self.api.get_health()

        assert response.is_success
        assert response.status_code == codes.OK
        assert response.content == b""
