import json
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from typing import Literal
from uuid import UUID

from src.core.rewards.exceptions import (
    GameRunConflictError,
    GameRunNotRegisteredError,
    InvalidRewardError,
    InvalidRewardReceiptError,
    InvalidRewardRequestError,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class CoinReward:
    amount: int
    type: Literal["COINS"] = "COINS"

    def validate(self) -> None:
        if type(self.amount) is not int or not 1 <= self.amount <= 2**63 - 1:
            raise InvalidRewardError


@dataclass(frozen=True, slots=True, kw_only=True)
class AccessoryReward:
    item_id: str
    type: Literal["ACCESSORY"] = "ACCESSORY"

    def validate(self) -> None:
        if not self.item_id or "\x00" in self.item_id:
            raise InvalidRewardRequestError
        try:
            self.item_id.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise InvalidRewardRequestError from exc


type RewardPayload = CoinReward | AccessoryReward


@dataclass(frozen=True, slots=True, kw_only=True)
class RewardRequestParams:
    game_run_id: str
    idempotency_key: str | None = None

    def validate(self) -> None:
        for value, max_bytes in ((self.game_run_id, None), (self.idempotency_key, 255)):
            if value is None:
                continue
            try:
                encoded = value.encode("utf-8")
            except UnicodeEncodeError as exc:
                raise InvalidRewardRequestError from exc
            if not value or "\x00" in value:
                raise InvalidRewardRequestError
            if max_bytes is not None and len(encoded) > max_bytes:
                raise InvalidRewardRequestError

    def require_registered_run(self, actual: str | None) -> None:
        if actual is None:
            raise GameRunNotRegisteredError
        if actual != self.game_run_id:
            raise GameRunConflictError


@dataclass(frozen=True, slots=True, kw_only=True)
class Reward:
    reward_id: UUID
    profile_id: UUID
    game_run_id: str
    sequence: int
    reward: RewardPayload
    created_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class IssuedReward:
    reward: Reward
    created: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class RewardsPage:
    profile_id: UUID
    game_run_id: str
    rewards: tuple[Reward, ...]
    next_after_sequence: int
    has_more: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class RewardReceipt:
    reward_id: UUID
    application_id: UUID
    history_entry_id: str
    history_sequence: int
    outcome: Literal["APPLIED", "ALREADY_OWNED"]


@dataclass(frozen=True, slots=True, kw_only=True)
class AckRewardsParams:
    game_run_id: str
    receipts: tuple[RewardReceipt, ...]

    def digest(self) -> str:
        document = {
            "gameRunId": self.game_run_id,
            "receipts": [
                {
                    "rewardId": str(receipt.reward_id),
                    "applicationId": str(receipt.application_id),
                    "historyEntryId": receipt.history_entry_id,
                    "historySequence": receipt.history_sequence,
                    "outcome": receipt.outcome,
                }
                for receipt in self.receipts
            ],
        }
        return sha256(
            json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    def validate(self) -> None:
        max_receipts = 100
        if not 1 <= len(self.receipts) <= max_receipts:
            raise InvalidRewardReceiptError
        ids = [item.application_id for item in self.receipts]
        if len(ids) != len(set(ids)):
            raise InvalidRewardReceiptError
        if any(
            not item.history_entry_id
            or "\x00" in item.history_entry_id
            or item.history_sequence < 1
            for item in self.receipts
        ):
            raise InvalidRewardReceiptError


@dataclass(frozen=True, slots=True, kw_only=True)
class AckRewardsResult:
    game_run_id: str
    accepted_application_ids: tuple[UUID, ...]
