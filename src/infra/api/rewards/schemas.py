from datetime import UTC
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import ConfigDict, Field

from src.core.rewards.schemas import (
    AccessoryReward,
    AckRewardsParams,
    AckRewardsResult,
    CoinReward,
    Reward,
    RewardPayload,
    RewardReceipt,
    RewardsPage,
)
from src.infra.api.boundary import BoundaryModel


class CoinRewardBody(BoundaryModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["COINS"]
    amount: Annotated[int, Field(strict=True, ge=1, le=2**63 - 1)]


class AccessoryRewardBody(BoundaryModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["ACCESSORY"]
    item_id: Annotated[str, Field(min_length=1)]


type RewardBody = Annotated[CoinRewardBody | AccessoryRewardBody, Field(discriminator="type")]


class CreateParentRewardRequest(BoundaryModel):
    model_config = ConfigDict(extra="forbid")
    device_id: Annotated[str, Field(min_length=1)]
    game_run_id: Annotated[str, Field(min_length=1)]
    reward: RewardBody
    schema_version: Literal[1] = 1

    def to_domain(self) -> RewardPayload:
        if isinstance(self.reward, CoinRewardBody):
            return CoinReward(amount=self.reward.amount)
        return AccessoryReward(item_id=self.reward.item_id)


class ParentRewardDto(BoundaryModel):
    reward_id: UUID
    profile_id: str
    game_run_id: str
    sequence: int
    reward: RewardBody
    created_at: str

    @classmethod
    def from_domain(cls, reward: Reward, *, device_id: str) -> Self:
        body = (
            CoinRewardBody(type="COINS", amount=reward.reward.amount)
            if isinstance(reward.reward, CoinReward)
            else AccessoryRewardBody(type="ACCESSORY", item_id=reward.reward.item_id)
        )
        return cls(
            reward_id=reward.reward_id,
            profile_id=device_id,
            game_run_id=reward.game_run_id,
            sequence=reward.sequence,
            reward=body,
            created_at=reward.created_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        )


class ParentRewardsResponse(BoundaryModel):
    schema_version: Literal[1] = 1
    profile_id: str
    game_run_id: str
    rewards: list[ParentRewardDto]
    next_after_sequence: int
    has_more: bool

    @classmethod
    def from_domain(cls, page: RewardsPage, *, device_id: str) -> Self:
        return cls(
            profile_id=device_id,
            game_run_id=page.game_run_id,
            rewards=[
                ParentRewardDto.from_domain(item, device_id=device_id) for item in page.rewards
            ],
            next_after_sequence=page.next_after_sequence,
            has_more=page.has_more,
        )


class ParentRewardReceiptDto(BoundaryModel):
    model_config = ConfigDict(extra="forbid")
    reward_id: UUID
    application_id: Annotated[str, Field(min_length=1)]
    history_entry_id: Annotated[str, Field(min_length=1)]
    history_sequence: Annotated[int, Field(strict=True, ge=1, le=2**63 - 1)]
    outcome: Literal["APPLIED", "ALREADY_OWNED"]

    def to_domain(self) -> RewardReceipt:
        return RewardReceipt(
            reward_id=self.reward_id,
            application_id=self.application_id,
            history_entry_id=self.history_entry_id,
            history_sequence=self.history_sequence,
            outcome=self.outcome,
        )


class AckParentRewardsRequest(BoundaryModel):
    model_config = ConfigDict(extra="forbid")
    device_id: Annotated[str, Field(min_length=1)]
    schema_version: Literal[1] = 1
    game_run_id: Annotated[str, Field(min_length=1)]
    receipts: Annotated[list[ParentRewardReceiptDto], Field(min_length=1, max_length=100)]

    def to_domain(self) -> AckRewardsParams:
        return AckRewardsParams(
            game_run_id=self.game_run_id,
            receipts=tuple(item.to_domain() for item in self.receipts),
        )


class AckParentRewardsResponse(BoundaryModel):
    schema_version: Literal[1] = 1
    game_run_id: str
    accepted_application_ids: list[str]

    @classmethod
    def from_domain(cls, result: AckRewardsResult) -> Self:
        return cls(
            game_run_id=result.game_run_id,
            accepted_application_ids=list(result.accepted_application_ids),
        )


class PullParentRewardsRequest(BoundaryModel):
    model_config = ConfigDict(extra="forbid")
    device_id: Annotated[str, Field(min_length=1)]
    game_run_id: Annotated[str, Field(min_length=1)]
    after_sequence: Annotated[int, Field(ge=0)]
    limit: Annotated[int, Field(ge=1, le=100)] = 50
    schema_version: Literal[1] = 1


class RewardErrorBody(BoundaryModel):
    code: str
    message: str | None = None
    request_id: str | None = None
