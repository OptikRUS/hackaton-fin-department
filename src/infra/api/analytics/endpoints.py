from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Header, status

from src.core.analytics.use_cases import GetSkillAssessmentsUseCase, UploadAnalyticsUseCase
from src.core.profiles.schemas import DeviceId
from src.infra.api.analytics.schemas import (
    AnalyticsError,
    AnalyticsUploadRequest,
    AnalyticsUploadResponse,
    SkillAssessmentsRequest,
    SkillAssessmentsResponse,
)

router = APIRouter(prefix="/v1/profiles", tags=["Analytics"], route_class=DishkaRoute)


@router.post(
    "/analytics",
    status_code=status.HTTP_200_OK,
    response_model=AnalyticsUploadResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": AnalyticsError},
        status.HTTP_403_FORBIDDEN: {"model": AnalyticsError},
        status.HTTP_409_CONFLICT: {"model": AnalyticsError},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": AnalyticsError},
    },
)
async def upload_analytics(
    body: AnalyticsUploadRequest,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1)],
    use_case: FromDishka[UploadAnalyticsUseCase],
) -> AnalyticsUploadResponse:
    result = await use_case.execute(
        params=body.to_domain(),
        idempotency_key=idempotency_key,
    )
    return AnalyticsUploadResponse.from_domain(result=result)


@router.post(
    "/skills/query",
    response_model=SkillAssessmentsResponse,
    responses={
        status.HTTP_403_FORBIDDEN: {"model": AnalyticsError},
        status.HTTP_409_CONFLICT: {"model": AnalyticsError},
    },
)
async def get_skill_assessments(
    body: SkillAssessmentsRequest,
    use_case: FromDishka[GetSkillAssessmentsUseCase],
) -> SkillAssessmentsResponse:
    assessment = await use_case.execute(
        profile_id=DeviceId(value=body.device_id).profile_id,
        game_run_id=body.game_run_id,
    )
    return SkillAssessmentsResponse.from_domain(assessment=assessment)
