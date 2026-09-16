from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from src.core.pets.schemas import CreatePetParams, Pet


class PetsFactory:
    @classmethod
    def create_pet_params(cls, *, pet_id: UUID, name: str, temper: str) -> CreatePetParams:
        return CreatePetParams(id=pet_id, name=name, temper=temper)

    @classmethod
    def create_pet(cls, *, pet_id: UUID, name: str, temper: str, balance: Decimal) -> Pet:
        return Pet(id=pet_id, name=name, temper=temper, balance=balance)


@dataclass(frozen=True, slots=True, kw_only=True)
class FactoryHelper:
    pets: type[PetsFactory] = PetsFactory
