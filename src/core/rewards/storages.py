from abc import ABCMeta, abstractmethod
from collections.abc import Mapping, Sequence
from uuid import UUID

from src.core.rewards.schemas import Reward, RewardReceipt


class RewardStorage(metaclass=ABCMeta):
    @abstractmethod
    async def get_registered_run_for_update(self, *, profile_id: UUID) -> str | None: ...

    @abstractmethod
    async def get_registered_run(self, *, profile_id: UUID) -> str | None: ...

    @abstractmethod
    async def get_issue_by_key(
        self,
        *,
        profile_id: UUID,
        idempotency_key: str,
    ) -> Reward | None: ...

    @abstractmethod
    async def last_sequence(self, *, profile_id: UUID, game_run_id: str) -> int: ...

    @abstractmethod
    async def insert_reward(
        self,
        *,
        reward: Reward,
        idempotency_key: str,
    ) -> Reward: ...

    @abstractmethod
    async def list_after(
        self,
        *,
        profile_id: UUID,
        game_run_id: str,
        after_sequence: int,
        limit: int,
    ) -> Sequence[Reward]: ...

    @abstractmethod
    async def get_ack_by_key(self, *, profile_id: UUID, idempotency_key: str) -> str | None: ...

    @abstractmethod
    async def get_receipts_by_application_ids(
        self,
        *,
        application_ids: Sequence[UUID],
    ) -> Mapping[UUID, tuple[RewardReceipt, UUID, str]]: ...

    @abstractmethod
    async def get_rewards_by_ids(
        self,
        *,
        profile_id: UUID,
        game_run_id: str,
        reward_ids: Sequence[UUID],
    ) -> Mapping[UUID, Reward]: ...

    @abstractmethod
    async def insert_receipts(
        self,
        *,
        profile_id: UUID,
        game_run_id: str,
        receipts: Sequence[RewardReceipt],
    ) -> set[UUID]: ...

    @abstractmethod
    async def insert_ack(self, *, profile_id: UUID, idempotency_key: str, digest: str) -> None: ...
