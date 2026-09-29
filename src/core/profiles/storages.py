from abc import ABC, abstractmethod
from uuid import UUID

from src.core.profiles.schemas import RegisteredPet, RegisteredProfile, RegistrationReceipt


class ProfileStorage(ABC):
    @abstractmethod
    async def get_profile(self, *, profile_id: UUID) -> RegisteredProfile | None: ...

    @abstractmethod
    async def create_profile(self, *, profile: RegisteredProfile) -> RegisteredProfile | None: ...

    @abstractmethod
    async def update_pet(self, *, profile_id: UUID, pet: RegisteredPet) -> None: ...

    @abstractmethod
    async def get_registration(
        self,
        *,
        profile_id: UUID,
        idempotency_key: str,
    ) -> RegistrationReceipt | None: ...

    @abstractmethod
    async def insert_registration(self, *, receipt: RegistrationReceipt) -> RegistrationReceipt: ...
