from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Header, status

from src.core.profiles.use_cases import RegisterProfileUseCase
from src.infra.api.profiles.schemas import RegisterProfileRequest, RegisterProfileResponse

router = APIRouter(prefix="/api/pets", tags=["Profiles"], route_class=DishkaRoute)


@router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=RegisterProfileResponse,
)
async def register_profile(
    body: RegisterProfileRequest,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1)],
    use_case: FromDishka[RegisterProfileUseCase],
) -> RegisterProfileResponse:
    result = await use_case.execute(
        params=body.to_domain(),
        idempotency_key=idempotency_key,
    )
    return RegisterProfileResponse.from_domain(result=result)
