from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.core.metrics import MetricsSink
from src.core.rewards.exceptions import (
    InvalidRewardCursorError,
    InvalidRewardError,
    InvalidRewardReceiptError,
    RewardIdempotencyConflictError,
    RewardReceiptConflictError,
    UnknownAccessoryError,
)
from src.core.rewards.schemas import (
    AccessoryReward,
    AckRewardsParams,
    AckRewardsResult,
    CoinReward,
    IssuedReward,
    Reward,
    RewardPayload,
    RewardRequestParams,
    RewardsPage,
)
from src.core.rewards.storages import RewardStorage
from src.core.use_case import UseCase


@dataclass(frozen=True, slots=True, kw_only=True)
class IssueRewardUseCase(UseCase):
    storage: RewardStorage
    metrics: MetricsSink | None = None
    permitted_accessory_ids: frozenset[str] = frozenset({
        "starter-bandana-v1",
        "starter-backpack-v1",
        "cosmetic-explorer-hat-v2",
        "figma-2164-2-explorer-cap-v1",
        "cosmetic-pilot-goggles-v1",
        "cosmetic-route-patch-v1",
        "cosmetic-compass-v1",
        "cosmetic-binoculars-v1",
        "cosmetic-cap-moscow-blue-v1",
        "cosmetic-cap-moscow-emerald-v1",
        "cosmetic-cap-moscow-burgundy-v1",
        "cosmetic-cap-lct2026-blue-v1",
        "cosmetic-cap-lct2026-emerald-v1",
        "cosmetic-cap-lct2026-burgundy-v1",
    })

    async def execute(
        self,
        *,
        profile_id: UUID,
        game_run_id: str,
        reward: RewardPayload,
        idempotency_key: str,
    ) -> IssuedReward:
        max_int64 = 2**63 - 1
        request = RewardRequestParams(game_run_id=game_run_id, idempotency_key=idempotency_key)
        request.validate()
        request.require_registered_run(
            await self.storage.get_registered_run_for_update(profile_id=profile_id)
        )
        previous = await self.storage.get_issue_by_key(
            profile_id=profile_id,
            idempotency_key=idempotency_key,
        )
        if previous is not None:
            if previous.game_run_id != game_run_id or previous.reward != reward:
                raise RewardIdempotencyConflictError
            return IssuedReward(reward=previous, created=False)
        if isinstance(reward, CoinReward):
            reward.validate()
        elif isinstance(reward, AccessoryReward):
            reward.validate()
            if reward.item_id not in self.permitted_accessory_ids:
                raise UnknownAccessoryError
        else:
            raise InvalidRewardError
        sequence = await self.storage.last_sequence(profile_id=profile_id, game_run_id=game_run_id)
        if sequence >= max_int64:
            raise InvalidRewardError
        issued = Reward(
            reward_id=uuid4(),
            profile_id=profile_id,
            game_run_id=game_run_id,
            sequence=sequence + 1,
            reward=reward,
            created_at=datetime.now(UTC),
        )
        issued = await self.storage.insert_reward(
            reward=issued,
            idempotency_key=idempotency_key,
        )
        if self.metrics is not None:
            self.metrics.observe_reward_issued(reward_type=reward.type, created=True)
        return IssuedReward(reward=issued, created=True)


@dataclass(frozen=True, slots=True, kw_only=True)
class ListRewardsUseCase(UseCase):
    storage: RewardStorage

    async def execute(
        self,
        *,
        profile_id: UUID,
        game_run_id: str,
        after_sequence: int = 0,
        limit: int = 50,
    ) -> RewardsPage:
        max_int64 = 2**63 - 1
        max_page_limit = 100
        request = RewardRequestParams(game_run_id=game_run_id)
        request.validate()
        if not 0 <= after_sequence <= max_int64 or not 1 <= limit <= max_page_limit:
            raise InvalidRewardCursorError
        request.require_registered_run(await self.storage.get_registered_run(profile_id=profile_id))
        last = await self.storage.last_sequence(profile_id=profile_id, game_run_id=game_run_id)
        if after_sequence > last:
            raise InvalidRewardCursorError
        rewards = tuple(
            await self.storage.list_after(
                profile_id=profile_id,
                game_run_id=game_run_id,
                after_sequence=after_sequence,
                limit=limit,
            )
        )
        if any(item.sequence != after_sequence + offset for offset, item in enumerate(rewards, 1)):
            raise RuntimeError
        next_after = rewards[-1].sequence if rewards else after_sequence
        return RewardsPage(
            profile_id=profile_id,
            game_run_id=game_run_id,
            rewards=rewards,
            next_after_sequence=next_after,
            has_more=bool(rewards) and next_after < last,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class AckRewardsUseCase(UseCase):
    storage: RewardStorage
    metrics: MetricsSink | None = None

    async def execute(
        self,
        *,
        profile_id: UUID,
        idempotency_key: str,
        params: AckRewardsParams,
    ) -> AckRewardsResult:
        request = RewardRequestParams(
            game_run_id=params.game_run_id, idempotency_key=idempotency_key
        )
        request.validate()
        params.validate()
        request.require_registered_run(
            await self.storage.get_registered_run_for_update(profile_id=profile_id)
        )
        digest = params.digest()
        previous = await self.storage.get_ack_by_key(
            profile_id=profile_id,
            idempotency_key=idempotency_key,
        )
        if previous is not None:
            if previous != digest:
                raise RewardReceiptConflictError
            return AckRewardsResult(
                game_run_id=params.game_run_id,
                accepted_application_ids=tuple(item.application_id for item in params.receipts),
            )
        application_ids = [item.application_id for item in params.receipts]
        existing = await self.storage.get_receipts_by_application_ids(
            application_ids=application_ids,
        )
        if any(
            item.application_id in existing
            and existing[item.application_id] != (item, profile_id, params.game_run_id)
            for item in params.receipts
        ):
            raise RewardReceiptConflictError
        rewards = await self.storage.get_rewards_by_ids(
            profile_id=profile_id,
            game_run_id=params.game_run_id,
            reward_ids=[item.reward_id for item in params.receipts],
        )
        if any(
            item.reward_id not in rewards
            or (
                item.outcome == "ALREADY_OWNED"
                and not isinstance(
                    rewards[item.reward_id].reward,
                    AccessoryReward,
                )
            )
            for item in params.receipts
        ):
            raise InvalidRewardReceiptError
        fresh = tuple(item for item in params.receipts if item.application_id not in existing)
        if fresh:
            inserted = await self.storage.insert_receipts(
                profile_id=profile_id,
                game_run_id=params.game_run_id,
                receipts=fresh,
            )
            if len(inserted) != len(fresh):
                current = await self.storage.get_receipts_by_application_ids(
                    application_ids=[item.application_id for item in fresh],
                )
                if any(
                    current.get(item.application_id) != (item, profile_id, params.game_run_id)
                    for item in fresh
                ):
                    raise RewardReceiptConflictError
        await self.storage.insert_ack(
            profile_id=profile_id,
            idempotency_key=idempotency_key,
            digest=digest,
        )
        if self.metrics is not None:
            self.metrics.observe_rewards_acknowledged(outcomes=[item.outcome for item in fresh])
        return AckRewardsResult(
            game_run_id=params.game_run_id,
            accepted_application_ids=tuple(application_ids),
        )
