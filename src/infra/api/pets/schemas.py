from typing import Self
from uuid import UUID

from src.core.pets.schemas import CreatePetParams, Pet
from src.infra.api.boundary import BoundaryModel


class CreatePetRequest(BoundaryModel):
    name: str
    temper: str

    def to_domain(self, *, pet_id: UUID) -> CreatePetParams:
        return CreatePetParams(
            id=pet_id,
            name=self.name,
            temper=self.temper,
        )


class CreatePetResponse(BoundaryModel):
    id: str

    @classmethod
    def from_domain(cls, *, pet: Pet) -> Self:
        return cls(id=pet.id.hex)
