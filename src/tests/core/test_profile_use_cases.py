from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from src.core.profiles.exceptions import (
    InvalidRegistrationError,
    ProfileConflictError,
    RegistrationIdempotencyConflictError,
)
from src.core.profiles.schemas import DeviceId
from src.core.profiles.storages import ProfileStorage
from src.core.profiles.use_cases import RegisterProfileUseCase
from src.tests.fixtures import FactoryFixture


class TestRegisterProfileUseCase(FactoryFixture):
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.storage = AsyncMock(spec=ProfileStorage)
        self.storage.create_profile.return_value = None
        self.storage.get_profile.return_value = None
        self.storage.get_registration.return_value = None
        self.use_case = RegisterProfileUseCase(storage=self.storage)

    async def test_creates_profile_and_registration_receipt(self) -> None:
        self.storage.create_profile.return_value = self.factory.profiles.registered_profile(
            profile_id=DeviceId(value="9f1c2d3e4a5b6078").profile_id,
            device_id="9f1c2d3e4a5b6078",
        )
        self.storage.get_profile.return_value = self.factory.profiles.registered_profile(
            profile_id=DeviceId(value="9f1c2d3e4a5b6078").profile_id,
            device_id="9f1c2d3e4a5b6078",
        )

        result = await self.use_case.execute(
            params=self.factory.profiles.register_params(device_id="9f1c2d3e4a5b6078"),
            idempotency_key="registration-1",
        )

        assert result == self.factory.profiles.register_result(device_id="9f1c2d3e4a5b6078")
        self.storage.create_profile.assert_awaited_once_with(
            profile=self.factory.profiles.registered_profile(
                profile_id=UUID("5f8a6037-daad-5f48-aa97-cd7720536fd0"),
                device_id="9f1c2d3e4a5b6078",
            )
        )
        self.storage.get_profile.assert_awaited_once_with(
            profile_id=DeviceId(value="9f1c2d3e4a5b6078").profile_id
        )
        self.storage.insert_registration.assert_awaited_once_with(
            receipt=self.factory.profiles.registration_receipt(
                profile_id=DeviceId(value="9f1c2d3e4a5b6078").profile_id,
                device_id="9f1c2d3e4a5b6078",
                request_digest=self.factory.profiles.register_params(
                    device_id="9f1c2d3e4a5b6078"
                ).request_digest(),
            )
        )

    async def test_registration_preserves_legacy_uuid_profile_key(self) -> None:
        self.storage.create_profile.return_value = self.factory.profiles.registered_profile(
            profile_id=UUID("344b0765-7318-450f-9576-e3f50e393f38"),
            device_id="344b0765-7318-450f-9576-e3f50e393f38",
        )
        self.storage.get_profile.return_value = self.factory.profiles.registered_profile(
            profile_id=UUID("344b0765-7318-450f-9576-e3f50e393f38"),
            device_id="344b0765-7318-450f-9576-e3f50e393f38",
        )

        result = await self.use_case.execute(
            params=self.factory.profiles.register_params(
                device_id="344b0765-7318-450f-9576-e3f50e393f38"
            ),
            idempotency_key="registration-1",
        )

        assert result == self.factory.profiles.register_result(
            device_id="344b0765-7318-450f-9576-e3f50e393f38"
        )
        self.storage.create_profile.assert_awaited_once_with(
            profile=self.factory.profiles.registered_profile(
                profile_id=UUID("344b0765-7318-450f-9576-e3f50e393f38"),
                device_id="344b0765-7318-450f-9576-e3f50e393f38",
            )
        )

    async def test_replays_same_key_without_new_receipt(self) -> None:
        self.storage.get_profile.return_value = self.factory.profiles.registered_profile(
            profile_id=DeviceId(value="9f1c2d3e4a5b6078").profile_id,
            device_id="9f1c2d3e4a5b6078",
        )
        self.storage.get_registration.return_value = self.factory.profiles.registration_receipt(
            profile_id=DeviceId(value="9f1c2d3e4a5b6078").profile_id,
            device_id="9f1c2d3e4a5b6078",
            request_digest=self.factory.profiles.register_params(
                device_id="9f1c2d3e4a5b6078"
            ).request_digest(),
        )

        result = await self.use_case.execute(
            params=self.factory.profiles.register_params(device_id="9f1c2d3e4a5b6078"),
            idempotency_key="registration-1",
        )

        assert result == self.factory.profiles.register_result(device_id="9f1c2d3e4a5b6078")
        self.storage.insert_registration.assert_not_awaited()

    async def test_new_key_for_same_pet_returns_existing_profile(self) -> None:
        self.storage.get_profile.return_value = self.factory.profiles.registered_profile(
            profile_id=DeviceId(value="9f1c2d3e4a5b6078").profile_id,
            device_id="9f1c2d3e4a5b6078",
        )

        result = await self.use_case.execute(
            params=self.factory.profiles.register_params(device_id="9f1c2d3e4a5b6078"),
            idempotency_key="registration-2",
        )

        assert result == self.factory.profiles.register_result(
            device_id="9f1c2d3e4a5b6078", created=False
        )
        self.storage.insert_registration.assert_awaited_once()

    async def test_changed_body_with_reused_key_conflicts(self) -> None:
        self.storage.get_profile.return_value = self.factory.profiles.registered_profile(
            profile_id=DeviceId(value="9f1c2d3e4a5b6078").profile_id,
            device_id="9f1c2d3e4a5b6078",
        )
        self.storage.get_registration.return_value = self.factory.profiles.registration_receipt(
            profile_id=DeviceId(value="9f1c2d3e4a5b6078").profile_id,
            device_id="9f1c2d3e4a5b6078",
            request_digest="f" * 64,
        )

        with pytest.raises(RegistrationIdempotencyConflictError):
            await self.use_case.execute(
                params=self.factory.profiles.register_params(device_id="9f1c2d3e4a5b6078"),
                idempotency_key="registration-1",
            )
        self.storage.insert_registration.assert_not_awaited()

    async def test_changed_pet_for_existing_profile_conflicts(self) -> None:
        self.storage.get_profile.return_value = self.factory.profiles.registered_profile(
            profile_id=DeviceId(value="9f1c2d3e4a5b6078").profile_id,
            device_id="9f1c2d3e4a5b6078",
            pet_name="Старое имя",
        )

        with pytest.raises(ProfileConflictError):
            await self.use_case.execute(
                params=self.factory.profiles.register_params(device_id="9f1c2d3e4a5b6078"),
                idempotency_key="registration-2",
            )
        self.storage.insert_registration.assert_not_awaited()

    async def test_invalid_device_id_does_not_call_storage(self) -> None:
        with pytest.raises(InvalidRegistrationError):
            await self.use_case.execute(
                params=self.factory.profiles.register_params(device_id=" "),
                idempotency_key="registration-1",
            )
        self.storage.create_profile.assert_not_awaited()
