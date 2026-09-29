import json
from dataclasses import dataclass, field
from uuid import UUID

from src.core.analytics.schemas import AnalyticsUploadParams, SkillAssessments, StoredBatch
from src.core.analytics.storages import AnalyticsStorage


@dataclass
class MemoryAnalyticsStorage(AnalyticsStorage):
    heads: dict[tuple[UUID, str], int] = field(default_factory=dict)
    batches: dict[tuple[UUID, str], StoredBatch] = field(default_factory=dict)
    originals: dict[tuple[UUID, str], dict[str, str]] = field(default_factory=dict)
    projections: dict[tuple[UUID, str, int, int, int, int], AnalyticsUploadParams] = field(
        default_factory=dict
    )
    assessments: dict[tuple[UUID, str], SkillAssessments] = field(default_factory=dict)
    registered_profiles: set[UUID] = field(default_factory=lambda: {UUID(int=1)})
    original_sequences: dict[tuple[UUID, str], dict[str, int | None]] = field(default_factory=dict)
    archive: str | None = json.dumps({"runId": "run-1", "historySequence": 0, "history": []})

    async def is_profile_registered(self, *, profile_id: UUID) -> bool:
        return profile_id in self.registered_profiles

    async def get_original_fact_sequences(
        self, *, profile_id: UUID, game_run_id: str
    ) -> dict[str, int | None]:
        return self.original_sequences.get((profile_id, game_run_id), {}).copy()

    async def get_snapshot_archive(self, *, profile_id: UUID) -> str | None:
        return self.archive

    async def ensure_head(self, *, profile_id: UUID, game_run_id: str) -> None:
        self.heads.setdefault((profile_id, game_run_id), -1)

    async def get_head_for_update(self, *, profile_id: UUID, game_run_id: str) -> int:
        return self.heads[(profile_id, game_run_id)]

    async def get_batch(self, *, profile_id: UUID, batch_id: str) -> StoredBatch | None:
        return self.batches.get((profile_id, batch_id))

    async def get_original_facts(self, *, profile_id: UUID, game_run_id: str) -> dict[str, str]:
        return self.originals.get((profile_id, game_run_id), {}).copy()

    async def insert_original_facts(
        self,
        *,
        profile_id: UUID,
        game_run_id: str,
        facts: dict[str, str],
        sequences: dict[str, int] | None = None,
    ) -> None:
        self.originals.setdefault((profile_id, game_run_id), {}).update(facts)
        self.original_sequences.setdefault((profile_id, game_run_id), {}).update({
            event_id: (sequences or {}).get(event_id) for event_id in facts
        })

    async def insert_projection(self, *, params: AnalyticsUploadParams) -> None:
        key = (
            params.profile_id,
            params.game_run_id,
            params.projection_version,
            params.evaluator_version,
            params.through_history_sequence,
            params.history_start_sequence,
        )
        self.projections[key] = params

    async def update_head(
        self, *, profile_id: UUID, game_run_id: str, through_history_sequence: int
    ) -> None:
        self.heads[(profile_id, game_run_id)] = through_history_sequence

    async def insert_batch(self, *, batch: StoredBatch) -> bool:
        if (batch.profile_id, batch.result.batch_id) in self.batches:
            return False
        self.batches[(batch.profile_id, batch.result.batch_id)] = batch
        return True

    async def get_assessment(
        self, *, profile_id: UUID, game_run_id: str
    ) -> SkillAssessments | None:
        return self.assessments.get((profile_id, game_run_id))
