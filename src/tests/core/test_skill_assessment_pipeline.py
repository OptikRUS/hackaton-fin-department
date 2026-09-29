from dataclasses import replace
from uuid import UUID

import pytest

from src.core.analytics.schemas import AnalyticsUploadParams
from src.core.analytics.use_cases import GetSkillAssessmentsUseCase, UploadAnalyticsUseCase
from src.tests.fixtures import FactoryFixture
from src.tests.mocks.analytics.storages import MemoryAnalyticsStorage


class TestSkillAssessmentPipeline(FactoryFixture):
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.storage = MemoryAnalyticsStorage()
        self.upload = UploadAnalyticsUseCase(analytics_storage=self.storage)
        self.query = GetSkillAssessmentsUseCase(analytics_storage=self.storage)

    def projection(
        self,
        *,
        episodes: list[tuple[str, int]],
        end: int,
        start: int = 0,
        batch: str = "batch-1",
        pending: bool = False,
    ) -> AnalyticsUploadParams:
        params = self.factory.analytics.upload_params(
            profile_id=UUID(int=1), sequence=end, batch_id=batch
        )
        observations = []
        facts = []
        for episode, sequence in episodes:
            facts.append({
                "eventId": f"event-{episode}",
                "gameRunId": "run-1",
                "episodeId": episode,
                "actionId": episode,
                "sequence": sequence,
                "detail": {"_type": "interaction", "name": "test-evidence"},
            })
            observations.append({
                "gameRunId": "run-1",
                "skill": "FIN-01",
                "episodeId": episode,
                "outcome": "INSUFFICIENT_DATA" if pending else "SUPPORTED",
                "eligibility": "UNDETERMINED" if pending else "ELIGIBLE",
                "completion": "PENDING" if pending else "COMPLETE",
                "reason": "CORRECT_COMPARISON",
                "sourceEventIds": [f"event-{episode}"],
                "assistance": [],
                "adultHelpKnown": False,
                "learningContexts": ["GAME"],
                "contextFamilies": ["comparison"],
            })
        count = len(episodes)
        params.skills[0].update({
            "observations": observations,
            "completedEpisodes": 0 if pending else count,
            "supportedEpisodes": 0 if pending else count,
            "supportedWithoutGameHints": 0 if pending else count,
            "pendingEpisodes": count if pending else 0,
            "incompleteEpisodes": count if pending else 0,
        })
        return replace(params, facts=facts, history_start_sequence=start)

    async def accept(self, params: AnalyticsUploadParams) -> None:
        await self.upload.execute(params=params, idempotency_key=params.batch_id)

    async def test_upload_persists_all_twelve_assessments_before_query(self) -> None:
        await self.accept(self.projection(episodes=[("one", 1), ("two", 2)], end=2))
        saved = await self.storage.get_assessment(profile_id=UUID(int=1), game_run_id="run-1")
        assert saved is not None
        assert saved.based_on_history_sequence == 2
        assert len(saved.skills) == 12
        assert saved.skills[0].status == "MASTERED"
        assert saved.skills[1].status == "NO_DATA"

    async def test_overlapping_uploads_and_replay_do_not_count_one_episode_twice(self) -> None:
        first = self.projection(episodes=[("one", 1)], end=1)
        await self.accept(first)
        await self.accept(self.projection(episodes=[("one", 1)], end=2, batch="next"))
        await self.accept(first)
        result = await self.query.execute(profile_id=UUID(int=1), game_run_id="run-1")
        assert result.based_on_history_sequence == 2
        assert result.skills[0].status == "PRACTICING"

    async def test_partial_history_preserves_prefix_and_combines_distinct_episodes(self) -> None:
        await self.accept(self.projection(episodes=[("before", 1)], end=2))
        await self.accept(self.projection(episodes=[("after", 3)], end=3, start=2, batch="after"))
        result = await self.query.execute(profile_id=UUID(int=1), game_run_id="run-1")
        assert result.skills[0].status == "MASTERED"
        assert result.based_on_history_sequence == 3

    async def test_new_full_projection_removes_observation_no_longer_in_evaluation(self) -> None:
        first = self.projection(episodes=[("one", 1), ("two", 2)], end=2)
        await self.accept(first)
        next_projection = self.projection(episodes=[("one", 1)], end=3, batch="recomputed")
        # Original evidence stays immutable, while derived evaluation may change.
        await self.accept(replace(next_projection, facts=first.facts))
        result = await self.query.execute(profile_id=UUID(int=1), game_run_id="run-1")
        assert result.skills[0].status == "PRACTICING"

    async def test_later_partial_projection_replaces_its_own_previous_observations(self) -> None:
        await self.accept(self.projection(episodes=[("before", 1)], end=2))
        after = self.projection(episodes=[("after", 3)], end=3, start=2, batch="after")
        await self.accept(after)
        empty = self.projection(episodes=[], end=4, start=2, batch="recomputed")
        await self.accept(replace(empty, facts=after.facts))
        result = await self.query.execute(profile_id=UUID(int=1), game_run_id="run-1")
        assert result.skills[0].status == "PRACTICING"

    async def test_partial_crossing_episode_keeps_completed_prefix_over_incomplete(self) -> None:
        await self.accept(self.projection(episodes=[("same", 1)], end=2))
        partial = self.projection(
            episodes=[("same", 3)], end=3, start=2, batch="restored", pending=True
        )
        # A distinct post-restore fact refers to the same logical episode.
        partial.facts[0]["eventId"] = "post-restore"
        partial.skills[0]["observations"][0]["sourceEventIds"] = ["post-restore"]
        await self.accept(partial)
        result = await self.query.execute(profile_id=UUID(int=1), game_run_id="run-1")
        assert result.skills[0].status == "PRACTICING"

    @pytest.mark.parametrize("end", [4, 6])
    async def test_removed_crossing_episode_does_not_resurrect_its_old_prefix_result(
        self, end: int
    ) -> None:
        await self.accept(self.projection(episodes=[("same", 1)], end=2))
        partial = self.projection(episodes=[("same", 3)], end=4, start=2, batch="restored")
        partial.facts[0]["eventId"] = "post-restore"
        partial.skills[0]["observations"][0]["sourceEventIds"] = ["post-restore"]
        await self.accept(partial)
        empty = self.projection(episodes=[], end=end, start=2, batch="recomputed")
        await self.accept(replace(empty, facts=partial.facts))
        result = await self.query.execute(profile_id=UUID(int=1), game_run_id="run-1")
        assert result.skills[0].status == "NO_DATA"

    async def test_query_backfills_preexisting_projection_without_new_upload(self) -> None:
        old = self.projection(episodes=[("one", 1), ("two", 2)], end=2)
        await self.storage.insert_projection(params=old)
        self.storage.heads[(UUID(int=1), "run-1")] = 2
        result = await self.query.execute(profile_id=UUID(int=1), game_run_id="run-1")
        assert result.skills[0].status == "MASTERED"
        assert {skill.policy_version for skill in result.skills} == {"skills-mvp-v1"}

    async def test_query_replaces_obsolete_policy_using_existing_evidence(self) -> None:
        old = self.projection(episodes=[], end=2)
        await self.storage.insert_projection(params=old)
        self.storage.assessments[(UUID(int=1), "run-1")] = self.factory.analytics.assessment(
            sequence=2, policy_version="obsolete-policy", status="MASTERED"
        )
        result = await self.query.execute(profile_id=UUID(int=1), game_run_id="run-1")
        assert {skill.status for skill in result.skills} == {"NO_DATA"}
        assert {skill.policy_version for skill in result.skills} == {"skills-mvp-v1"}
