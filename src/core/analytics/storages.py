from abc import ABCMeta, abstractmethod
from uuid import UUID

from src.core.analytics.schemas import (
    AnalyticsUploadParams,
    AssessmentProjection,
    SkillAssessments,
    StoredBatch,
)


class AnalyticsStorage(metaclass=ABCMeta):
    @abstractmethod
    async def is_profile_registered(self, *, profile_id: UUID) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get_original_fact_sequences(
        self, *, profile_id: UUID, game_run_id: str
    ) -> dict[str, int | None]:
        raise NotImplementedError

    @abstractmethod
    async def get_snapshot_archive(self, *, profile_id: UUID) -> str | None:
        raise NotImplementedError

    @abstractmethod
    async def ensure_head(self, *, profile_id: UUID, game_run_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_head_for_update(self, *, profile_id: UUID, game_run_id: str) -> int | None:
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
        sequences: dict[str, int] | None = None,
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

    @abstractmethod
    async def get_assessment_projections(
        self,
        *,
        profile_id: UUID,
        game_run_id: str,
    ) -> list[AssessmentProjection]:
        raise NotImplementedError

    @abstractmethod
    async def save_assessment(
        self,
        *,
        profile_id: UUID,
        assessment: SkillAssessments,
    ) -> None:
        raise NotImplementedError
