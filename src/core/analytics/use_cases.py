import json
from dataclasses import dataclass
from uuid import UUID

from src.core.analytics.exceptions import (
    AnalyticsFactConflictError,
    AnalyticsGameRunNotRegisteredError,
    AnalyticsIdempotencyConflictError,
    AnalyticsStaleError,
    AssessmentNotReadyError,
    InvalidAnalyticsError,
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
        await self.analytics_storage.ensure_head(
            profile_id=params.profile_id,
            game_run_id=params.game_run_id,
        )
        current_sequence = await self.analytics_storage.get_head_for_update(
            profile_id=params.profile_id,
            game_run_id=params.game_run_id,
        )
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
        archive_json = await self.analytics_storage.get_snapshot_archive(
            profile_id=params.profile_id
        )
        if archive_json is None:
            raise AnalyticsGameRunNotRegisteredError
        self._verify_snapshot_source(params=params, archive_json=archive_json)
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
        if any(event_id not in originals for event_id in stored_originals):
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
            )
        await self.analytics_storage.insert_projection(params=params)
        if params.through_history_sequence > current_sequence:
            await self.analytics_storage.update_head(
                profile_id=params.profile_id,
                game_run_id=params.game_run_id,
                through_history_sequence=params.through_history_sequence,
            )
        return result

    @staticmethod
    def _verify_snapshot_source(*, params: AnalyticsUploadParams, archive_json: str) -> None:
        try:
            archive = json.loads(archive_json)
            if (
                archive["runId"] != params.game_run_id
                or archive["historySequence"] < params.through_history_sequence
            ):
                raise AnalyticsGameRunNotRegisteredError
            source_facts = {
                fact["eventId"]: AnalyticsUploadParams.digest_value(fact)
                for entry in archive["history"]
                if entry["sequence"] <= params.through_history_sequence
                for fact in entry.get("facts", [])
            }
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidAnalyticsError from exc
        if source_facts != params.original_digests():
            raise AnalyticsFactConflictError


@dataclass(frozen=True, slots=True, kw_only=True)
class GetSkillAssessmentsUseCase(UseCase):
    analytics_storage: AnalyticsStorage

    async def execute(self, *, profile_id: UUID, game_run_id: str) -> SkillAssessments:
        assessment = await self.analytics_storage.get_assessment(
            profile_id=profile_id,
            game_run_id=game_run_id,
        )
        if assessment is None:
            raise AssessmentNotReadyError
        return assessment
