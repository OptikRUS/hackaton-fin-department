import pytest
from httpx2 import codes

from src.core.profiles.use_cases import RegisterProfileUseCase
from src.tests.fixtures import APIFixture, ContainerFixture, FactoryFixture


class TestRegisterProfileAPI(APIFixture, ContainerFixture, FactoryFixture):
    @pytest.fixture(autouse=True)
    async def setup(self) -> None:
        self.use_case = await self.container_helper.override_use_case(
            use_case_type=RegisterProfileUseCase,
        )

    async def test_registration_returns_created_profile(self) -> None:
        self.use_case.execute.return_value = self.factory.profiles.register_result(
            device_id="9f1c2d3e4a5b6078",
        )

        response = await self.api.register_profile(
            device_id="9f1c2d3e4a5b6078",
            idempotency_key="registration-1",
        )

        assert response.status_code == codes.CREATED
        assert response.json() == {"deviceId": "9f1c2d3e4a5b6078"}
        self.use_case.execute.assert_awaited_once_with(
            params=self.factory.profiles.register_params(device_id="9f1c2d3e4a5b6078"),
            idempotency_key="registration-1",
        )

    async def test_registration_rejects_missing_device_id(self) -> None:
        response = await self.api.register_profile(
            device_id=None,
            idempotency_key="registration-1",
        )

        assert response.status_code == codes.BAD_REQUEST
        assert response.json() == {"code": "INVALID_REQUEST"}
        self.use_case.execute.assert_not_awaited()

    async def test_registration_replay_returns_existing_profile(self) -> None:
        self.use_case.execute.return_value = self.factory.profiles.register_result(
            device_id="9f1c2d3e4a5b6078", created=False
        )

        response = await self.api.register_profile(
            device_id="9f1c2d3e4a5b6078",
            idempotency_key="registration-1",
        )

        assert response.status_code == codes.CREATED
        assert response.json() == {"deviceId": "9f1c2d3e4a5b6078"}
        self.use_case.execute.assert_awaited_once_with(
            params=self.factory.profiles.register_params(device_id="9f1c2d3e4a5b6078"),
            idempotency_key="registration-1",
        )
