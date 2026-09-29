from dataclasses import replace

import pytest

from src.core.profiles.schemas import DeviceId, RegistrationReceipt
from src.infra.storages.postgres.profile_storage import PostgresProfileStorage
from src.tests.fixtures import FactoryFixture, PostgresFixture


class TestPostgresProfileStorage(FactoryFixture, PostgresFixture):
    @pytest.fixture(autouse=True)
    async def setup(self, profile_storage: PostgresProfileStorage) -> None:
        self.storage = profile_storage

    async def test_create_and_read_profile(self) -> None:
        result = await self.storage.create_profile(
            profile=self.factory.profiles.registered_profile(
                profile_id=DeviceId(value="9f1c2d3e4a5b6078").profile_id,
                device_id="9f1c2d3e4a5b6078",
            )
        )

        assert result == self.factory.profiles.registered_profile(
            profile_id=DeviceId(value="9f1c2d3e4a5b6078").profile_id, device_id="9f1c2d3e4a5b6078"
        )
        result = await self.storage.get_profile(
            profile_id=DeviceId(value="9f1c2d3e4a5b6078").profile_id
        )

        assert result == self.factory.profiles.registered_profile(
            profile_id=DeviceId(value="9f1c2d3e4a5b6078").profile_id, device_id="9f1c2d3e4a5b6078"
        )

    async def test_duplicate_device_does_not_create_another_profile(self) -> None:
        await self.postgres_helper.insert_profile(
            profile=self.factory.profiles.registered_profile(
                profile_id=DeviceId(value="9f1c2d3e4a5b6078").profile_id,
                device_id="9f1c2d3e4a5b6078",
            )
        )

        result = await self.storage.create_profile(
            profile=self.factory.profiles.registered_profile(
                profile_id=DeviceId(value="9f1c2d3e4a5b6078").profile_id,
                device_id="9f1c2d3e4a5b6078",
            )
        )

        assert result is None

    async def test_update_pet_replaces_registration_fields(self) -> None:
        profile = self.factory.profiles.registered_profile(
            profile_id=DeviceId(value="9f1c2d3e4a5b6078").profile_id,
            device_id="9f1c2d3e4a5b6078",
        )
        await self.storage.create_profile(profile=profile)
        updated_pet = replace(
            profile.pet,
            name="Новый питомец",
            age="TEEN",
            color="SAND",
            temperament="Joyful",
            selected_look_id="HAT",
        )

        await self.storage.update_pet(profile_id=profile.profile_id, pet=updated_pet)

        assert await self.storage.get_profile(profile_id=profile.profile_id) == replace(
            profile, pet=updated_pet
        )

    async def test_insert_and_read_registration_receipt(self) -> None:
        await self.postgres_helper.insert_profile(
            profile=self.factory.profiles.registered_profile(
                profile_id=DeviceId(value="9f1c2d3e4a5b6078").profile_id,
                device_id="9f1c2d3e4a5b6078",
            )
        )

        result = await self.storage.insert_registration(
            receipt=RegistrationReceipt(
                profile_id=DeviceId(value="9f1c2d3e4a5b6078").profile_id,
                idempotency_key="registration-1",
                request_digest="a" * 64,
                result=self.factory.profiles.register_result(device_id="9f1c2d3e4a5b6078"),
            )
        )

        assert result == RegistrationReceipt(
            profile_id=DeviceId(value="9f1c2d3e4a5b6078").profile_id,
            idempotency_key="registration-1",
            request_digest="a" * 64,
            result=self.factory.profiles.register_result(device_id="9f1c2d3e4a5b6078"),
        )
        result = await self.storage.get_registration(
            profile_id=DeviceId(value="9f1c2d3e4a5b6078").profile_id,
            idempotency_key="registration-1",
        )

        assert result == RegistrationReceipt(
            profile_id=DeviceId(value="9f1c2d3e4a5b6078").profile_id,
            idempotency_key="registration-1",
            request_digest="a" * 64,
            result=self.factory.profiles.register_result(device_id="9f1c2d3e4a5b6078"),
        )
