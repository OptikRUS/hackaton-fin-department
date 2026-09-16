from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, status

from src.core.pets.use_cases import CreatePetUseCase
from src.infra.api.pets.schemas import CreatePetRequest, CreatePetResponse

router = APIRouter(prefix="/api/pets", tags=["pets"], route_class=DishkaRoute)


@router.post(path="", status_code=status.HTTP_201_CREATED)
async def create_pet(
    body: CreatePetRequest,
    pet_id: FromDishka[UUID],
    use_case: FromDishka[CreatePetUseCase],
) -> CreatePetResponse:
    pet = await use_case.execute(params=body.to_domain(pet_id=pet_id))
    return CreatePetResponse.from_domain(pet=pet)
