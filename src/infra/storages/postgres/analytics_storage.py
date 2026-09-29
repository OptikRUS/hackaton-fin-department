from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.analytics.schemas import (
    AnalyticsUploadParams,
    SkillAssessments,
    StoredBatch,
)
from src.core.analytics.storages import AnalyticsStorage
from src.infra.storages.postgres.models import (
    AnalyticsBatchModel,
    AnalyticsHeadModel,
    AnalyticsOriginalFactModel,
    AnalyticsProjectionModel,
    ProfileModel,
    SkillAssessmentModel,
    SnapshotHeadModel,
)


@dataclass(kw_only=True, slots=True)
class PostgresAnalyticsStorage(AnalyticsStorage):
    session: AsyncSession

    async def is_profile_registered(self, *, profile_id: UUID) -> bool:
        return (
            await self.session.scalar(
                select(ProfileModel.profile_id).where(ProfileModel.profile_id == profile_id)
            )
            is not None
        )

    async def get_original_fact_sequences(
        self, *, profile_id: UUID, game_run_id: str
    ) -> dict[str, int | None]:
        rows = await self.session.execute(
            select(AnalyticsOriginalFactModel.event_id, AnalyticsOriginalFactModel.sequence).where(
                AnalyticsOriginalFactModel.profile_id == profile_id,
                AnalyticsOriginalFactModel.game_run_id == game_run_id,
            ),
        )
        return dict(rows.tuples().all())

    async def get_snapshot_archive(self, *, profile_id: UUID) -> str | None:
        return await self.session.scalar(
            select(SnapshotHeadModel.snapshot_json).where(
                SnapshotHeadModel.profile_id == profile_id,
                SnapshotHeadModel.server_revision > 0,
            ),
        )

    async def ensure_head(self, *, profile_id: UUID, game_run_id: str) -> None:
        await self.session.execute(
            insert(AnalyticsHeadModel)
            .values(profile_id=profile_id, game_run_id=game_run_id, through_history_sequence=-1)
            .on_conflict_do_nothing(
                index_elements=[AnalyticsHeadModel.profile_id, AnalyticsHeadModel.game_run_id],
            ),
        )

    async def get_head_for_update(self, *, profile_id: UUID, game_run_id: str) -> int:
        return (
            await self.session.scalars(
                select(AnalyticsHeadModel.through_history_sequence)
                .where(
                    AnalyticsHeadModel.profile_id == profile_id,
                    AnalyticsHeadModel.game_run_id == game_run_id,
                )
                .with_for_update(),
            )
        ).one()

    async def get_batch(self, *, profile_id: UUID, batch_id: str) -> StoredBatch | None:
        model = await self.session.scalar(
            select(AnalyticsBatchModel).where(
                AnalyticsBatchModel.profile_id == profile_id,
                AnalyticsBatchModel.batch_id == batch_id,
            ),
        )
        if model is None:
            return None
        return model.to_domain()

    async def get_original_facts(self, *, profile_id: UUID, game_run_id: str) -> dict[str, str]:
        rows = await self.session.execute(
            select(
                AnalyticsOriginalFactModel.event_id, AnalyticsOriginalFactModel.fact_digest
            ).where(
                AnalyticsOriginalFactModel.profile_id == profile_id,
                AnalyticsOriginalFactModel.game_run_id == game_run_id,
            ),
        )
        return {event_id: digest for event_id, digest in rows.tuples().all()}  # noqa: C416

    async def insert_original_facts(
        self,
        *,
        profile_id: UUID,
        game_run_id: str,
        facts: dict[str, str],
        sequences: dict[str, int] | None = None,
    ) -> None:
        await self.session.execute(
            insert(AnalyticsOriginalFactModel).values([
                {
                    "profile_id": profile_id,
                    "game_run_id": game_run_id,
                    "event_id": event_id,
                    "fact_digest": digest,
                    "sequence": (sequences or {}).get(event_id),
                }
                for event_id, digest in facts.items()
            ]),
        )

    async def insert_projection(self, *, params: AnalyticsUploadParams) -> None:
        statement = insert(AnalyticsProjectionModel).values(
            profile_id=params.profile_id,
            game_run_id=params.game_run_id,
            projection_version=params.projection_version,
            evaluator_version=params.evaluator_version,
            through_history_sequence=params.through_history_sequence,
            history_start_sequence=params.history_start_sequence,
            facts=params.facts,
            skills=params.skills,
        )
        await self.session.execute(
            statement.on_conflict_do_update(
                index_elements=[
                    AnalyticsProjectionModel.profile_id,
                    AnalyticsProjectionModel.game_run_id,
                    AnalyticsProjectionModel.projection_version,
                    AnalyticsProjectionModel.evaluator_version,
                    AnalyticsProjectionModel.through_history_sequence,
                    AnalyticsProjectionModel.history_start_sequence,
                ],
                set_={"facts": statement.excluded.facts, "skills": statement.excluded.skills},
            ),
        )

    async def update_head(
        self,
        *,
        profile_id: UUID,
        game_run_id: str,
        through_history_sequence: int,
    ) -> None:
        await self.session.execute(
            update(AnalyticsHeadModel)
            .where(
                AnalyticsHeadModel.profile_id == profile_id,
                AnalyticsHeadModel.game_run_id == game_run_id,
            )
            .values(through_history_sequence=through_history_sequence),
        )

    async def insert_batch(self, *, batch: StoredBatch) -> bool:
        result = batch.result
        inserted = await self.session.scalar(
            insert(AnalyticsBatchModel)
            .values(
                profile_id=batch.profile_id,
                batch_id=result.batch_id,
                request_digest=batch.request_digest,
                game_run_id=result.game_run_id,
                accepted_through_history_sequence=result.accepted_through_history_sequence,
                accepted_event_ids=list(result.accepted_event_ids),
                created=result.created,
            )
            .on_conflict_do_nothing(
                index_elements=[AnalyticsBatchModel.profile_id, AnalyticsBatchModel.batch_id],
            )
            .returning(AnalyticsBatchModel.batch_id),
        )
        return inserted is not None

    async def get_assessment(
        self,
        *,
        profile_id: UUID,
        game_run_id: str,
    ) -> SkillAssessments | None:
        model = await self.session.scalar(
            select(SkillAssessmentModel)
            .where(
                SkillAssessmentModel.profile_id == profile_id,
                SkillAssessmentModel.game_run_id == game_run_id,
            )
            .order_by(SkillAssessmentModel.based_on_history_sequence.desc())
            .limit(1),
        )
        if model is None:
            return None
        return model.to_domain()
