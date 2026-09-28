from abc import ABCMeta, abstractmethod
from uuid import UUID

from src.core.analytics.schemas import (
    AnalyticsUploadParams,
    SkillAssessments,
    StoredBatch,
)


class AnalyticsStorage(metaclass=ABCMeta):
    @abstractmethod
    async def get_snapshot_archive(self, *, profile_id: UUID) -> str | None:
        raise NotImplementedError

    @abstractmethod
    async def ensure_head(self, *, profile_id: UUID, game_run_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_head_for_update(self, *, profile_id: UUID, game_run_id: str) -> int:
        raise NotImplementedError

    @abstractmethod
    async def get_batch(self, *, profile_id: UUID, batch_id: str) -> StoredBatch | None:
        raise NotImplementedError

    @abstractmethod
    async def get_original_facts(self, *, profile_id: UUID, game_run_id: str) -> dict[str, str]:
        raise NotImplementedError

    @abstractmethod
    async def insert_original_facts(
        self,
        *,
        profile_id: UUID,
        game_run_id: str,
        facts: dict[str, str],
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def insert_projection(self, *, params: AnalyticsUploadParams) -> None:
        raise NotImplementedError

    @abstractmethod
    async def update_head(
        self,
        *,
        profile_id: UUID,
        game_run_id: str,
        through_history_sequence: int,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def insert_batch(self, *, batch: StoredBatch) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get_assessment(
        self,
        *,
        profile_id: UUID,
        game_run_id: str,
    ) -> SkillAssessments | None:
        raise NotImplementedError
