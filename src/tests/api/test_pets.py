from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from httpx2 import codes

from src.core.pets.use_cases import CreatePetUseCase
from src.tests.fixtures import APIFixture, ContainerFixture, FactoryFixture


class TestCreatePetAPI(APIFixture, ContainerFixture, FactoryFixture):
    use_case: AsyncMock

    @pytest.fixture(autouse=True)
    async def _setup(self) -> None:
        self.use_case = await self.container_helper.override_use_case(CreatePetUseCase)

    async def test_create_pet_returns_generated_hex_id(self) -> None:
        self.use_case.execute.return_value = self.factory.pets.create_pet(
            pet_id=UUID("12345678-1234-5678-1234-567812345678"),
            name="Barsik",
            temper="playful",
            balance=Decimal(100),
        )

        response = await self.api.create_pet(name="Barsik", temper="playful")

        assert response.status_code == codes.CREATED
        assert response.json() == {"id": "12345678123456781234567812345678"}
        self.use_case.execute.assert_awaited_once_with(
            params=self.factory.pets.create_pet_params(
                pet_id=UUID("12345678-1234-5678-1234-567812345678"),
                name="Barsik",
                temper="playful",
            ),
        )

    @pytest.mark.parametrize(
        ("name", "temper"),
        [
            ("Barsik", None),
            (None, "playful"),
        ],
    )
    async def test_create_pet_rejects_missing_fields(
        self,
        name: str | None,
        temper: str | None,
    ) -> None:
        response = await self.api.create_pet(name=name, temper=temper)

        assert response.status_code == codes.UNPROCESSABLE_CONTENT
        self.use_case.execute.assert_not_awaited()
