from dataclasses import dataclass

from behave.runner import Context

from src.core.pets.schemas import Pet
from src.tests.mocks.pets.storages import MockPetStorage


@dataclass(frozen=True, slots=True, kw_only=True)
class PetStorageHelper:
    context: Context
    storage: MockPetStorage

    def add_pet(self, *, pet: Pet) -> None:
        self.storage.add_pet(pet=pet)

    def get_pets(self) -> list[Pet]:
        return list(self.storage.pets.values())
