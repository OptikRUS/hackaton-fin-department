from dataclasses import dataclass
from uuid import UUID

from src.core.analytics.assessment_evidence import merge_observations
from src.core.analytics.assessment_policy import calculate_assessments
from src.core.analytics.exceptions import (
    AnalyticsFactConflictError,
    AnalyticsGameRunNotRegisteredError,
    AnalyticsIdempotencyConflictError,
    AnalyticsStaleError,
    AssessmentNotReadyError,
)
from src.core.analytics.schemas import (
    AnalyticsUploadParams,
    AnalyticsUploadResult,
    SkillAssessments,
    StoredBatch,
)
from src.core.analytics.storages import AnalyticsStorage
from src.core.use_case import UseCase


@dataclass(frozen=True, slots=True, kw_only=True)
class UploadAnalyticsUseCase(UseCase):
    analytics_storage: AnalyticsStorage

    async def execute(  # noqa: C901
        self,
        *,
        params: AnalyticsUploadParams,
        idempotency_key: str,
    ) -> AnalyticsUploadResult:
        params.validate(idempotency_key=idempotency_key)
        digest = params.request_digest()
        if not await self.analytics_storage.is_profile_registered(profile_id=params.profile_id):
            raise AnalyticsGameRunNotRegisteredError
        await self.analytics_storage.ensure_head(
            profile_id=params.profile_id,
            game_run_id=params.game_run_id,
        )
        current_sequence = await self.analytics_storage.get_head_for_update(
            profile_id=params.profile_id,
            game_run_id=params.game_run_id,
        )
        if current_sequence is None:  # ensure_head must create the row before locking.
            message = "Analytics head disappeared during upload"
            raise RuntimeError(message)
        previous = await self.analytics_storage.get_batch(
            profile_id=params.profile_id,
            batch_id=params.batch_id,
        )
        if previous is not None:
            if previous.request_digest != digest:
                raise AnalyticsIdempotencyConflictError
            return previous.result
        if params.through_history_sequence < current_sequence:
            raise AnalyticsStaleError
        originals = params.original_digests()
        stored_originals = await self.analytics_storage.get_original_facts(
            profile_id=params.profile_id,
            game_run_id=params.game_run_id,
        )
        if any(
            stored_originals.get(event_id, fact_digest) != fact_digest
            for event_id, fact_digest in originals.items()
        ):
            raise AnalyticsFactConflictError
        stored_sequences = await self.analytics_storage.get_original_fact_sequences(
            profile_id=params.profile_id,
            game_run_id=params.game_run_id,
        )
        if any(
            event_id not in originals
            and (
                params.history_start_sequence == 0
                or (sequence := stored_sequences.get(event_id)) is None
                or sequence > params.history_start_sequence
            )
            for event_id in stored_originals
        ):
            raise AnalyticsFactConflictError
        new_originals = {
            event_id: fact_digest
            for event_id, fact_digest in originals.items()
            if event_id not in stored_originals
        }
        result = AnalyticsUploadResult(
            batch_id=params.batch_id,
            game_run_id=params.game_run_id,
            accepted_through_history_sequence=params.through_history_sequence,
            accepted_event_ids=tuple(fact["eventId"] for fact in params.facts),
            created=True,
        )
        inserted = await self.analytics_storage.insert_batch(
            batch=StoredBatch(profile_id=params.profile_id, request_digest=digest, result=result),
        )
        if not inserted:
            concurrent = await self.analytics_storage.get_batch(
                profile_id=params.profile_id,
                batch_id=params.batch_id,
            )
            if concurrent is None or concurrent.request_digest != digest:
                raise AnalyticsIdempotencyConflictError
            return concurrent.result
        if new_originals:
            await self.analytics_storage.insert_original_facts(
                profile_id=params.profile_id,
                game_run_id=params.game_run_id,
                facts=new_originals,
                sequences={
                    fact["eventId"]: fact["sequence"]
                    for fact in params.facts
                    if fact["eventId"] in new_originals
                },
            )
        await self.analytics_storage.insert_projection(params=params)
        if params.through_history_sequence > current_sequence:
            await self.analytics_storage.update_head(
                profile_id=params.profile_id,
                game_run_id=params.game_run_id,
                through_history_sequence=params.through_history_sequence,
            )
        await _refresh_assessment(
            self.analytics_storage,
            profile_id=params.profile_id,
            game_run_id=params.game_run_id,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class GetSkillAssessmentsUseCase(UseCase):
    analytics_storage: AnalyticsStorage

    async def execute(self, *, profile_id: UUID, game_run_id: str) -> SkillAssessments:
        # Serialize backfill with uploads to avoid persisting an older assessment
        # after a newer batch has committed. Query never creates an empty run.
        await self.analytics_storage.get_head_for_update(
            profile_id=profile_id, game_run_id=game_run_id
        )
        assessment = await _refresh_assessment(
            self.analytics_storage,
            profile_id=profile_id,
            game_run_id=game_run_id,
        )
        if assessment is None:
            assessment = await self.analytics_storage.get_assessment(
                profile_id=profile_id,
                game_run_id=game_run_id,
            )
        if assessment is None:
            raise AssessmentNotReadyError
        return assessment


async def _refresh_assessment(
    storage: AnalyticsStorage,
    *,
    profile_id: UUID,
    game_run_id: str,
) -> SkillAssessments | None:
    projections = await storage.get_assessment_projections(
        profile_id=profile_id,
        game_run_id=game_run_id,
    )
    if not projections:
        return None
    assessment = calculate_assessments(
        game_run_id=game_run_id,
        based_on_history_sequence=max(p.through_history_sequence for p in projections),
        observations=merge_observations(projections),
    )
    await storage.save_assessment(profile_id=profile_id, assessment=assessment)
    return assessment
