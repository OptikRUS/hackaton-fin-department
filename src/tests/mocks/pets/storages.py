from dataclasses import dataclass, field
from uuid import UUID

from src.core.pets.schemas import Pet
from src.core.pets.storages import PetStorage


@dataclass(kw_only=True)
class MockPetStorage(PetStorage):
    pets: dict[UUID, Pet] = field(default_factory=dict)

    def add_pet(self, *, pet: Pet) -> None:
        self.pets[pet.id] = pet

    async def create_pet(self, *, pet: Pet) -> Pet:
        self.pets[pet.id] = pet
        return pet
