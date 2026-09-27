from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Header, status

from src.core.profiles.schemas import DeviceId
from src.core.rewards.use_cases import AckRewardsUseCase, IssueRewardUseCase, ListRewardsUseCase
from src.infra.api.rewards.schemas import (
    AckParentRewardsRequest,
    AckParentRewardsResponse,
    CreateParentRewardRequest,
    ParentRewardDto,
    ParentRewardsResponse,
    PullParentRewardsRequest,
    RewardErrorBody,
)

parent_router = APIRouter(
    prefix="/v1/parent-profiles",
    tags=["Parent rewards"],
    route_class=DishkaRoute,
)
device_router = APIRouter(
    prefix="/v1/profiles",
    tags=["Parent rewards"],
    route_class=DishkaRoute,
)


@parent_router.post(
    "/rewards",
    status_code=status.HTTP_201_CREATED,
    response_model=ParentRewardDto,
    responses={
        403: {"model": RewardErrorBody},
        409: {"model": RewardErrorBody},
        422: {"model": RewardErrorBody},
    },
)
async def create_parent_reward(
    body: CreateParentRewardRequest,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1)],
    use_case: FromDishka[IssueRewardUseCase],
) -> ParentRewardDto:
    result = await use_case.execute(
        profile_id=DeviceId(value=body.device_id).profile_id,
        game_run_id=body.game_run_id,
        reward=body.to_domain(),
        idempotency_key=idempotency_key,
    )
    return ParentRewardDto.from_domain(result.reward, device_id=body.device_id)


@device_router.post(
    "/rewards/pull",
    response_model=ParentRewardsResponse,
    responses={
        403: {"model": RewardErrorBody},
        409: {"model": RewardErrorBody},
        422: {"model": RewardErrorBody},
    },
)
async def list_parent_rewards(
    body: PullParentRewardsRequest,
    use_case: FromDishka[ListRewardsUseCase],
) -> ParentRewardsResponse:
    page = await use_case.execute(
        profile_id=DeviceId(value=body.device_id).profile_id,
        game_run_id=body.game_run_id,
        after_sequence=body.after_sequence,
        limit=body.limit,
    )
    return ParentRewardsResponse.from_domain(page, device_id=body.device_id)


@device_router.post(
    "/rewards/ack",
    response_model=AckParentRewardsResponse,
    responses={
        403: {"model": RewardErrorBody},
        409: {"model": RewardErrorBody},
        422: {"model": RewardErrorBody},
    },
)
async def acknowledge_parent_rewards(
    body: AckParentRewardsRequest,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1)],
    use_case: FromDishka[AckRewardsUseCase],
) -> AckParentRewardsResponse:
    result = await use_case.execute(
        profile_id=DeviceId(value=body.device_id).profile_id,
        params=body.to_domain(),
        idempotency_key=idempotency_key,
    )
    return AckParentRewardsResponse.from_domain(result)
