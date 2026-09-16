from decimal import Decimal
from uuid import UUID

import pytest

from src.infra.storages.postgres.pet_storage import PostgresPetStorage
from src.tests.fixtures import FactoryFixture, PostgresFixture


class TestPostgresPetCreateStorage(FactoryFixture, PostgresFixture):
    storage: PostgresPetStorage

    @pytest.fixture(autouse=True)
    async def setup(self, pet_storage: PostgresPetStorage) -> None:
        self.storage = pet_storage

    async def test_creates_pet(self) -> None:
        result = await self.storage.create_pet(
            pet=self.factory.pets.create_pet(
                pet_id=UUID("12345678-1234-5678-1234-567812345678"),
                name="Barsik",
                temper="playful",
                balance=Decimal(100),
            ),
        )

        model = await self.postgres_helper.get_pet(
            pet_id=UUID("12345678-1234-5678-1234-567812345678"),
        )

        assert result == self.factory.pets.create_pet(
            pet_id=UUID("12345678-1234-5678-1234-567812345678"),
            name="Barsik",
            temper="playful",
            balance=Decimal(100),
        )
        assert model is not None
        assert model.to_domain() == self.factory.pets.create_pet(
            pet_id=UUID("12345678-1234-5678-1234-567812345678"),
            name="Barsik",
            temper="playful",
            balance=Decimal(100),
        )
