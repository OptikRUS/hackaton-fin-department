from dataclasses import dataclass
from decimal import Decimal

from src.core.metrics import MetricsSink
from src.core.pets.schemas import CreatePetParams, Pet
from src.core.pets.storages import PetStorage
from src.core.use_case import UseCase


@dataclass(frozen=True, slots=True, kw_only=True)
class CreatePetUseCase(UseCase):
    pet_storage: PetStorage
    metrics: MetricsSink | None = None

    async def execute(self, *, params: CreatePetParams) -> Pet:
        pet = Pet(
            id=params.id,
            name=params.name,
            temper=params.temper,
            balance=Decimal(100),
        )
        created = await self.pet_storage.create_pet(pet=pet)
        if self.metrics is not None:
            self.metrics.observe_pet_created()
        return created
