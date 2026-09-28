import copy
import json
from typing import Any
from uuid import UUID

import pytest

from src.core.analytics.exceptions import (
    AnalyticsFactConflictError,
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

    async def test_reject_malformed_known_detail_and_forged_source_fact(self) -> None:
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
        forged = copy.deepcopy(fact)
        forged["detail"]["name"] = "invented"
        with pytest.raises(AnalyticsFactConflictError):
            await self.use_case.execute(
                params=self.factory.analytics.upload_params(
                    profile_id=UUID(int=1), facts=[forged], sequence=1
                ),
                idempotency_key="batch-1",
            )

    async def test_mobile_snapshot_history_facts_match_projection_prefix(self) -> None:
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
