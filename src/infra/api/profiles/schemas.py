from typing import Annotated, Literal, Self

from pydantic import Field

from src.core.profiles.schemas import (
    PetAge,
    PetColor,
    PetTemperament,
    RegisteredPet,
    RegisterProfileParams,
    RegisterProfileResult,
)
from src.infra.api.boundary import BoundaryModel


class RegisteredPetRequest(BoundaryModel):
    name: Annotated[str, Field(min_length=1)]
    age: PetAge
    color: PetColor
    temperament: PetTemperament
    selected_look_id: Annotated[str, Field(min_length=1)]

    def to_domain(self) -> RegisteredPet:
        return RegisteredPet(
            name=self.name,
            age=self.age,
            color=self.color,
            temperament=self.temperament,
            selected_look_id=self.selected_look_id,
        )


class RegisterProfileRequest(BoundaryModel):
    device_id: Annotated[str, Field(min_length=1)]
    pet: RegisteredPetRequest
    schema_version: Literal[1] = 1

    def to_domain(self) -> RegisterProfileParams:
        return RegisterProfileParams(
            device_id=self.device_id,
            pet=self.pet.to_domain(),
            schema_version=self.schema_version,
        )


class RegisterProfileResponse(BoundaryModel):
    device_id: str

    @classmethod
    def from_domain(cls, *, result: RegisterProfileResult) -> Self:
        return cls(device_id=result.device_id)
