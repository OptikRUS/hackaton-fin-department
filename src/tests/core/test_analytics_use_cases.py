import copy
import json
from dataclasses import replace
from typing import Any
from uuid import UUID

import pytest

from src.core.analytics.exceptions import (
    AnalyticsFactConflictError,
    AnalyticsGameRunNotRegisteredError,
    AnalyticsIdempotencyConflictError,
    AnalyticsStaleError,
    AssessmentNotReadyError,
    InvalidAnalyticsError,
)
from src.core.analytics.schemas import AnalyticsUploadParams
from src.core.analytics.use_cases import GetSkillAssessmentsUseCase, UploadAnalyticsUseCase
from src.tests.fixtures import FactoryFixture
from src.tests.mocks.analytics.storages import MemoryAnalyticsStorage


class TestUploadAnalyticsUseCase(FactoryFixture):
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.storage = MemoryAnalyticsStorage()
        self.use_case = UploadAnalyticsUseCase(analytics_storage=self.storage)

    async def test_upload_replay_and_conflicting_batch(self) -> None:
        upload = self.factory.analytics.upload_params(profile_id=UUID(int=1))
        result = await self.use_case.execute(params=upload, idempotency_key="batch-1")
        assert result.created is True
        assert result.accepted_event_ids == ()
        replayed_result = await self.use_case.execute(params=upload, idempotency_key="batch-1")

        assert replayed_result == result
        changed = self.factory.analytics.upload_params(profile_id=UUID(int=1), sequence=1)
        with pytest.raises(AnalyticsIdempotencyConflictError):
            await self.use_case.execute(params=changed, idempotency_key="batch-1")

    async def test_reject_stale_and_conflicting_original_fact(self) -> None:
        fact: dict[str, Any] = {
            "eventId": "event-1",
            "gameRunId": "run-1",
            "episodeId": "ep-1",
            "actionId": "action-1",
            "sequence": 1,
            "detail": {"_type": "interaction", "name": "tap"},
        }
        self.storage.archive = json.dumps({
            "runId": "run-1",
            "historySequence": 2,
            "history": [{"sequence": 1, "facts": [fact]}],
        })
        await self.use_case.execute(
            params=self.factory.analytics.upload_params(
                profile_id=UUID(int=1), facts=[fact], sequence=1
            ),
            idempotency_key="batch-1",
        )
        with pytest.raises(AnalyticsStaleError):
            await self.use_case.execute(
                params=self.factory.analytics.upload_params(
                    profile_id=UUID(int=1), batch_id="batch-2"
                ),
                idempotency_key="batch-2",
            )
        changed = copy.deepcopy(fact)
        changed["detail"]["name"] = "other"
        with pytest.raises(AnalyticsFactConflictError):
            await self.use_case.execute(
                params=self.factory.analytics.upload_params(
                    profile_id=UUID(int=1), facts=[changed], sequence=2, batch_id="batch-3"
                ),
                idempotency_key="batch-3",
            )

    async def test_reject_missing_skill_and_bad_source_reference(self) -> None:
        with pytest.raises(InvalidAnalyticsError):
            await self.use_case.execute(
                params=self.factory.analytics.upload_params(
                    profile_id=UUID(int=1),
                    skills=self.factory.analytics.upload_params(profile_id=UUID(int=1)).skills[:-1],
                ),
                idempotency_key="batch-1",
            )
        skills = copy.deepcopy(self.factory.analytics.upload_params(profile_id=UUID(int=1)).skills)
        skills[0]["observations"] = [
            {
                "gameRunId": "run-1",
                "skill": "FIN-01",
                "episodeId": "ep-1",
                "outcome": "SUPPORTED",
                "eligibility": "ELIGIBLE",
                "completion": "COMPLETE",
                "reason": "CORRECT_COMPARISON",
                "sourceEventIds": ["missing"],
                "assistance": [],
                "adultHelpKnown": False,
                "learningContexts": ["GAME"],
                "contextFamilies": ["default"],
            }
        ]
        with pytest.raises(InvalidAnalyticsError):
            await self.use_case.execute(
                params=self.factory.analytics.upload_params(profile_id=UUID(int=1), skills=skills),
                idempotency_key="batch-1",
            )

    async def test_reject_malformed_known_detail_and_changed_accepted_fact(self) -> None:
        fact: dict[str, Any] = {
            "eventId": "event-1",
            "gameRunId": "run-1",
            "episodeId": "ep-1",
            "actionId": "action-1",
            "sequence": 1,
            "detail": {"_type": "optional_purchase", "itemId": "apple"},
        }
        self.storage.archive = json.dumps({
            "runId": "run-1",
            "historySequence": 1,
            "history": [{"sequence": 1, "facts": [fact]}],
        })
        with pytest.raises(InvalidAnalyticsError):
            await self.use_case.execute(
                params=self.factory.analytics.upload_params(
                    profile_id=UUID(int=1), facts=[fact], sequence=1
                ),
                idempotency_key="batch-1",
            )
        fact["detail"] = {
            "_type": "optional_purchase",
            "itemId": "apple",
            "price": "10",
            "purchased": True,
        }
        with pytest.raises(InvalidAnalyticsError):
            await self.use_case.execute(
                params=self.factory.analytics.upload_params(
                    profile_id=UUID(int=1), facts=[fact], sequence=1
                ),
                idempotency_key="batch-1",
            )
        fact["detail"] = {
            "_type": "optional_purchase",
            "itemId": "apple",
            "price": 10,
            "purchased": True,
            "unexpected": "field",
        }
        with pytest.raises(InvalidAnalyticsError):
            await self.use_case.execute(
                params=self.factory.analytics.upload_params(
                    profile_id=UUID(int=1), facts=[fact], sequence=1
                ),
                idempotency_key="batch-1",
            )
        fact["detail"] = {
            "_type": "resource_choice",
            "chosenOptionId": "apple",
            "chosenCost": {"money": "10", "energy": 0, "time": 0},
            "alternativeCost": {"money": 0, "energy": 0, "time": 0},
            "energyBefore": 1,
            "availableTimeBefore": 1,
            "priorityId": None,
            "priorityMoney": 0,
            "priorityEnergy": 0,
            "priorityTime": 0,
        }
        with pytest.raises(InvalidAnalyticsError):
            await self.use_case.execute(
                params=self.factory.analytics.upload_params(
                    profile_id=UUID(int=1), facts=[fact], sequence=1
                ),
                idempotency_key="batch-1",
            )
        fact["detail"] = {"_type": "interaction", "name": "tap"}
        await self.use_case.execute(
            params=self.factory.analytics.upload_params(
                profile_id=UUID(int=1), facts=[fact], sequence=1, batch_id="accepted"
            ),
            idempotency_key="accepted",
        )
        forged = copy.deepcopy(fact)
        forged["detail"]["name"] = "invented"
        with pytest.raises(AnalyticsFactConflictError):
            await self.use_case.execute(
                params=self.factory.analytics.upload_params(
                    profile_id=UUID(int=1), facts=[forged], sequence=1
                ),
                idempotency_key="batch-1",
            )

    async def test_originals_exclude_derived_projection_facts(self) -> None:
        original: dict[str, Any] = {
            "eventId": "event-1",
            "gameRunId": "run-1",
            "episodeId": "ep-1",
            "actionId": "action-1",
            "sequence": 1,
            "detail": {"_type": "interaction", "name": "tap"},
        }
        later: dict[str, Any] = {
            "eventId": "event-2",
            "gameRunId": "run-1",
            "episodeId": "ep-2",
            "actionId": "action-2",
            "sequence": 2,
            "detail": {"_type": "interaction", "name": "open"},
        }
        derived: dict[str, Any] = {
            "eventId": "derived:4:run-1:interval",
            "gameRunId": "run-1",
            "episodeId": "ep-1",
            "actionId": "action-1",
            "sequence": 1,
            "detail": {"_type": "interaction", "name": "projection"},
        }
        self.storage.archive = json.dumps({
            "runId": "run-1",
            "historySequence": 2,
            "history": [
                {"id": "audit-1", "sequence": 1, "facts": [original]},
                {"id": "audit-2", "sequence": 2, "facts": [later]},
            ],
        })
        result = await self.use_case.execute(
            params=self.factory.analytics.upload_params(
                profile_id=UUID(int=1), facts=[original, derived], sequence=1
            ),
            idempotency_key="batch-1",
        )

        assert result.accepted_event_ids == ("event-1", "derived:4:run-1:interval")
        assert self.storage.originals[(UUID(int=1), "run-1")] == {
            "event-1": AnalyticsUploadParams.digest_value(original),
        }

    async def test_uploads_analytics_for_archived_mobile_run(self) -> None:
        self.storage.archive = self.factory.snapshots.archive_json(
            format_version=5,
            run_id="run-2",
            history=[],
            archived_runs=[
                self.factory.snapshots.archived_run(
                    history_sequence=1,
                    history=[
                        {
                            "sequence": 1,
                            "facts": [
                                {
                                    "eventId": "event-1",
                                    "gameRunId": "run-1",
                                    "episodeId": "ep-1",
                                    "actionId": "action-1",
                                    "sequence": 1,
                                    "detail": {"_type": "interaction", "name": "tap"},
                                }
                            ],
                        }
                    ],
                )
            ],
        )

        result = await self.use_case.execute(
            params=self.factory.analytics.upload_params(
                profile_id=UUID(int=1),
                sequence=1,
                facts=[
                    {
                        "eventId": "event-1",
                        "gameRunId": "run-1",
                        "episodeId": "ep-1",
                        "actionId": "action-1",
                        "sequence": 1,
                        "detail": {"_type": "interaction", "name": "tap"},
                    }
                ],
            ),
            idempotency_key="batch-1",
        )

        assert result == self.factory.analytics.upload_result(sequence=1, event_ids=("event-1",))

    async def test_mobile_skill_counters_are_recomputed_from_observations(self) -> None:
        fact: dict[str, Any] = {
            "eventId": "event-1",
            "gameRunId": "run-1",
            "episodeId": "ep-1",
            "actionId": "action-1",
            "sequence": 1,
            "detail": {"_type": "interaction", "name": "tap"},
        }
        skills = self.factory.analytics.upload_params(profile_id=UUID(int=1)).skills
        skills[0].update({
            "completedEpisodes": 1,
            "supportedEpisodes": 1,
            "supportedWithoutGameHints": 0,
            "assistedEpisodes": 1,
            "observations": [
                {
                    "gameRunId": "run-1",
                    "skill": "FIN-01",
                    "episodeId": "ep-1",
                    "outcome": "SUPPORTED",
                    "eligibility": "ELIGIBLE",
                    "completion": "COMPLETE",
                    "reason": "CORRECT_COMPARISON",
                    "sourceEventIds": ["event-1"],
                    "assistance": ["HINT"],
                    "adultHelpKnown": False,
                    "learningContexts": ["GAME"],
                    "contextFamilies": ["lesson-1"],
                }
            ],
        })
        self.storage.archive = json.dumps({
            "runId": "run-1",
            "historySequence": 1,
            "history": [{"sequence": 1, "facts": [fact]}],
        })

        result = await self.use_case.execute(
            params=self.factory.analytics.upload_params(
                profile_id=UUID(int=1), facts=[fact], skills=skills, sequence=1
            ),
            idempotency_key="batch-1",
        )
        assert result.accepted_event_ids == ("event-1",)

        skills[0]["supportedWithoutGameHints"] = 1
        with pytest.raises(InvalidAnalyticsError):
            await self.use_case.execute(
                params=self.factory.analytics.upload_params(
                    profile_id=UUID(int=1),
                    facts=[fact],
                    skills=skills,
                    sequence=1,
                    batch_id="batch-2",
                ),
                idempotency_key="batch-2",
            )


class TestIndependentAnalytics(FactoryFixture):
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.storage = MemoryAnalyticsStorage(archive=None)
        self.use_case = UploadAnalyticsUseCase(analytics_storage=self.storage)

    @staticmethod
    def fact(event_id: str, sequence: int) -> dict[str, Any]:
        return {
            "eventId": event_id,
            "gameRunId": "run-1",
            "episodeId": event_id,
            "actionId": event_id,
            "sequence": sequence,
            "detail": {"_type": "interaction", "name": "tap"},
        }

    async def test_registered_device_uploads_before_any_snapshot(self) -> None:
        result = await self.use_case.execute(
            params=self.factory.analytics.upload_params(
                profile_id=UUID(int=1), facts=[self.fact("event-1", 1)], sequence=1
            ),
            idempotency_key="batch-1",
        )
        assert result.accepted_event_ids == ("event-1",)
        assert result.accepted_through_history_sequence == 1

    async def test_analytics_can_advance_beyond_world_backup(self) -> None:
        self.storage.archive = json.dumps({"runId": "run-1", "historySequence": 0})
        result = await self.use_case.execute(
            params=self.factory.analytics.upload_params(
                profile_id=UUID(int=1), facts=[self.fact("event-1", 1)], sequence=1
            ),
            idempotency_key="batch-1",
        )
        assert result.accepted_through_history_sequence == 1

    async def test_restore_retains_originals_and_both_equal_end_projections(self) -> None:
        first = self.factory.analytics.upload_params(
            profile_id=UUID(int=1), facts=[self.fact("before", 899)], sequence=901
        )
        await self.use_case.execute(params=first, idempotency_key="batch-1")
        restored = replace(
            self.factory.analytics.upload_params(
                profile_id=UUID(int=1),
                facts=[self.fact("after", 901)],
                sequence=901,
                batch_id="batch-2",
            ),
            history_start_sequence=900,
        )
        result = await self.use_case.execute(params=restored, idempotency_key="batch-2")
        replay = await self.use_case.execute(params=restored, idempotency_key="batch-2")
        assert replay == result
        assert result.accepted_event_ids == ("after",)
        assert set(self.storage.originals[(UUID(int=1), "run-1")]) == {"before", "after"}
        assert len(self.storage.projections) == 2
        assert first in self.storage.projections.values()
        assert restored in self.storage.projections.values()

    async def test_restore_cannot_omit_previously_accepted_in_range_fact(self) -> None:
        first = self.factory.analytics.upload_params(
            profile_id=UUID(int=1), facts=[self.fact("after", 901)], sequence=901
        )
        await self.use_case.execute(params=first, idempotency_key="batch-1")
        missing = replace(
            self.factory.analytics.upload_params(
                profile_id=UUID(int=1), sequence=902, batch_id="batch-2"
            ),
            history_start_sequence=900,
        )
        with pytest.raises(AnalyticsFactConflictError):
            await self.use_case.execute(params=missing, idempotency_key="batch-2")
        assert (UUID(int=1), "batch-2") not in self.storage.batches

    async def test_partial_range_digest_conflicts_under_same_batch_id(self) -> None:
        upload = replace(
            self.factory.analytics.upload_params(profile_id=UUID(int=1), sequence=901),
            history_start_sequence=900,
        )
        await self.use_case.execute(params=upload, idempotency_key="batch-1")
        with pytest.raises(AnalyticsIdempotencyConflictError):
            await self.use_case.execute(
                params=replace(upload, history_start_sequence=899), idempotency_key="batch-1"
            )

    @pytest.mark.parametrize(("start", "end"), [(-1, 1), (2, 1), (True, 1), (1.5, 2)])
    async def test_invalid_range_is_rejected(self, start: float, end: int) -> None:
        upload = replace(
            self.factory.analytics.upload_params(profile_id=UUID(int=1), sequence=end),
            history_start_sequence=start,
        )
        with pytest.raises(InvalidAnalyticsError):
            await self.use_case.execute(params=upload, idempotency_key="batch-1")
        assert self.storage.batches == {}

    @pytest.mark.parametrize("sequence", [899, 900, 902])
    async def test_fact_must_be_after_restore_start_and_within_end(self, sequence: int) -> None:
        upload = replace(
            self.factory.analytics.upload_params(
                profile_id=UUID(int=1), sequence=901, facts=[self.fact("fact", sequence)]
            ),
            history_start_sequence=900,
        )
        with pytest.raises(InvalidAnalyticsError):
            await self.use_case.execute(params=upload, idempotency_key="batch-1")

    async def test_unregistered_profile_rejected_without_creating_analytics(self) -> None:
        upload = self.factory.analytics.upload_params(profile_id=UUID(int=999))
        with pytest.raises(AnalyticsGameRunNotRegisteredError):
            await self.use_case.execute(params=upload, idempotency_key="batch-1")
        assert self.storage.heads == {}
        assert self.storage.batches == {}

    async def test_unknown_legacy_sequence_cannot_be_silently_omitted(self) -> None:
        self.storage.originals[(UUID(int=1), "run-1")] = {"legacy": "a" * 64}
        upload = replace(
            self.factory.analytics.upload_params(profile_id=UUID(int=1), sequence=901),
            history_start_sequence=900,
        )
        with pytest.raises(AnalyticsFactConflictError):
            await self.use_case.execute(params=upload, idempotency_key="batch-1")
        assert self.storage.batches == {}

    async def test_changed_original_rejected_after_restore(self) -> None:
        fact = self.fact("after", 901)
        await self.use_case.execute(
            params=self.factory.analytics.upload_params(
                profile_id=UUID(int=1), sequence=901, facts=[fact]
            ),
            idempotency_key="batch-1",
        )
        changed = copy.deepcopy(fact)
        changed["detail"]["name"] = "changed"
        upload = replace(
            self.factory.analytics.upload_params(
                profile_id=UUID(int=1), sequence=902, facts=[changed], batch_id="batch-2"
            ),
            history_start_sequence=900,
        )
        with pytest.raises(AnalyticsFactConflictError):
            await self.use_case.execute(params=upload, idempotency_key="batch-2")
        assert (UUID(int=1), "batch-2") not in self.storage.batches

    async def test_new_run_retains_prior_run_and_has_separate_evidence_boundary(self) -> None:
        first = self.factory.analytics.upload_params(
            profile_id=UUID(int=1), sequence=901, facts=[self.fact("shared-id", 901)]
        )
        await self.use_case.execute(params=first, idempotency_key="batch-1")
        new_fact = {**self.fact("shared-id", 1), "gameRunId": "run-2"}
        second = replace(
            self.factory.analytics.upload_params(
                profile_id=UUID(int=1), sequence=1, facts=[new_fact], batch_id="batch-2"
            ),
            game_run_id="run-2",
        )
        result = await self.use_case.execute(params=second, idempotency_key="batch-2")
        assert result.game_run_id == "run-2"
        assert self.storage.heads[(UUID(int=1), "run-1")] == 901
        assert self.storage.heads[(UUID(int=1), "run-2")] == 1
        assert set(self.storage.originals) == {(UUID(int=1), "run-1"), (UUID(int=1), "run-2")}

    async def test_zero_range_preserves_frozen_legacy_batch_digest(self) -> None:
        upload = self.factory.analytics.upload_params(profile_id=UUID(int=1))
        frozen = AnalyticsUploadParams.digest_value({
            "profileId": str(UUID(int=1)),
            "batchId": "batch-1",
            "gameRunId": "run-1",
            "throughHistorySequence": 0,
            "projectionVersion": 4,
            "evaluatorVersion": 1,
            "schemaVersion": 1,
            "facts": [],
            "skills": upload.skills,
        })
        receipt = self.factory.analytics.stored_batch(profile_id=UUID(int=1), request_digest=frozen)
        self.storage.batches[(UUID(int=1), "batch-1")] = receipt
        assert upload.request_digest() == frozen
        replay = await self.use_case.execute(
            params=replace(upload, history_start_sequence=0), idempotency_key="batch-1"
        )
        assert replay == receipt.result


class TestGetSkillAssessmentsUseCase(FactoryFixture):
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.storage = MemoryAnalyticsStorage()
        self.use_case = GetSkillAssessmentsUseCase(analytics_storage=self.storage)

    async def test_skills_without_policy_is_explicitly_not_ready(self) -> None:
        with pytest.raises(AssessmentNotReadyError):
            await self.use_case.execute(
                profile_id=UUID(int=1),
                game_run_id="run-1",
            )

    async def test_returns_the_saved_policy_result(self) -> None:
        self.storage.assessments[(UUID(int=1), "run-1")] = self.factory.analytics.assessment(
            sequence=8,
            policy_version="policy-2",
            status="PRACTICING",
        )

        result = await self.use_case.execute(profile_id=UUID(int=1), game_run_id="run-1")

        assert result == self.factory.analytics.assessment(
            sequence=8, policy_version="policy-2", status="PRACTICING"
        )
