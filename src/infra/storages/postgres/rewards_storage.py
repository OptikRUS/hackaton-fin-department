from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.rewards.schemas import Reward, RewardReceipt
from src.core.rewards.storages import RewardStorage
from src.infra.storages.postgres.models import (
    RewardAckModel,
    RewardModel,
    RewardReceiptModel,
    SnapshotHeadModel,
)


@dataclass(kw_only=True, slots=True)
class PostgresRewardStorage(RewardStorage):
    session: AsyncSession

    async def get_registered_run_for_update(self, *, profile_id: UUID) -> str | None:
        model = await self.session.scalar(
            select(SnapshotHeadModel)
            .where(SnapshotHeadModel.profile_id == profile_id)
            .with_for_update(),
        )
        return model.game_run_id if model is not None and model.server_revision > 0 else None

    async def get_registered_run(self, *, profile_id: UUID) -> str | None:
        model = await self.session.scalar(
            select(SnapshotHeadModel).where(SnapshotHeadModel.profile_id == profile_id),
        )
        return model.game_run_id if model is not None and model.server_revision > 0 else None

    async def get_issue_by_key(
        self,
        *,
        profile_id: UUID,
        idempotency_key: str,
    ) -> Reward | None:
        model = await self.session.scalar(
            select(RewardModel).where(
                RewardModel.profile_id == profile_id,
                RewardModel.idempotency_key == idempotency_key,
            ),
        )
        return model.to_domain() if model is not None else None

    async def last_sequence(self, *, profile_id: UUID, game_run_id: str) -> int:
        value = await self.session.scalar(
            select(func.coalesce(func.max(RewardModel.sequence), 0)).where(
                RewardModel.profile_id == profile_id,
                RewardModel.game_run_id == game_run_id,
            ),
        )
        return int(value or 0)

    async def insert_reward(
        self,
        *,
        reward: Reward,
        idempotency_key: str,
    ) -> Reward:
        coin = reward.reward if reward.reward.type == "COINS" else None
        accessory = reward.reward if reward.reward.type == "ACCESSORY" else None
        model = await self.session.scalar(
            insert(RewardModel)
            .values(
                reward_id=reward.reward_id,
                profile_id=reward.profile_id,
                game_run_id=reward.game_run_id,
                sequence=reward.sequence,
                idempotency_key=idempotency_key,
                reward_type=reward.reward.type,
                amount=coin.amount if coin is not None else None,
                item_id=accessory.item_id if accessory is not None else None,
                created_at=reward.created_at,
            )
            .returning(RewardModel),
        )
        if model is None:
            raise RuntimeError
        return model.to_domain()

    async def list_after(
        self,
        *,
        profile_id: UUID,
        game_run_id: str,
        after_sequence: int,
        limit: int,
    ) -> list[Reward]:
        rows = await self.session.scalars(
            select(RewardModel)
            .where(
                RewardModel.profile_id == profile_id,
                RewardModel.game_run_id == game_run_id,
                RewardModel.sequence > after_sequence,
            )
            .order_by(RewardModel.sequence)
            .limit(limit),
        )
        return [model.to_domain() for model in rows]

    async def get_ack_by_key(self, *, profile_id: UUID, idempotency_key: str) -> str | None:
        return await self.session.scalar(
            select(RewardAckModel.digest).where(
                RewardAckModel.profile_id == profile_id,
                RewardAckModel.idempotency_key == idempotency_key,
            ),
        )

    async def get_receipts_by_application_ids(
        self,
        *,
        application_ids: Sequence[UUID],
    ) -> dict[UUID, tuple[RewardReceipt, UUID, str]]:
        rows = await self.session.scalars(
            select(RewardReceiptModel).where(
                RewardReceiptModel.application_id.in_(application_ids),
            ),
        )
        return {
            model.application_id: (model.to_domain(), model.profile_id, model.game_run_id)
            for model in rows
        }

    async def get_rewards_by_ids(
        self,
        *,
        profile_id: UUID,
        game_run_id: str,
        reward_ids: Sequence[UUID],
    ) -> dict[UUID, Reward]:
        rows = await self.session.scalars(
            select(RewardModel).where(
                RewardModel.profile_id == profile_id,
                RewardModel.game_run_id == game_run_id,
                RewardModel.reward_id.in_(reward_ids),
            ),
        )
        return {model.reward_id: model.to_domain() for model in rows}

    async def insert_receipts(
        self,
        *,
        profile_id: UUID,
        game_run_id: str,
        receipts: Sequence[RewardReceipt],
    ) -> set[UUID]:
        rows = await self.session.scalars(
            insert(RewardReceiptModel)
            .values([
                {
                    "application_id": item.application_id,
                    "profile_id": profile_id,
                    "game_run_id": game_run_id,
                    "reward_id": item.reward_id,
                    "history_entry_id": item.history_entry_id,
                    "history_sequence": item.history_sequence,
                    "outcome": item.outcome,
                }
                for item in receipts
            ])
            .on_conflict_do_nothing(index_elements=[RewardReceiptModel.application_id])
            .returning(RewardReceiptModel.application_id),
        )
        return set(rows)

    async def insert_ack(self, *, profile_id: UUID, idempotency_key: str, digest: str) -> None:
        await self.session.execute(
            insert(RewardAckModel).values(
                profile_id=profile_id,
                idempotency_key=idempotency_key,
                digest=digest,
            ),
        )
