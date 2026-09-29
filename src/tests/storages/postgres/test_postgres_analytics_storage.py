from dataclasses import replace
from uuid import UUID

import pytest
from sqlalchemy import delete

from src.core.analytics.schemas import AnalyticsUploadParams
from src.core.analytics.use_cases import UploadAnalyticsUseCase
from src.infra.storages.postgres.analytics_storage import PostgresAnalyticsStorage
from src.infra.storages.postgres.models import AnalyticsProjectionModel
from src.tests.fixtures import FactoryFixture, PostgresFixture


class TestPostgresAnalyticsStorage(FactoryFixture, PostgresFixture):
    @pytest.fixture(autouse=True)
    async def setup(self, analytics_storage: PostgresAnalyticsStorage) -> None:
        self.storage = analytics_storage

    async def test_snapshot_archive_read_returns_exact_saved_json(self) -> None:
        profile_id = UUID("b09682a3-1421-488c-a3e1-58b18ac94121")
        result = await self.storage.get_snapshot_archive(profile_id=profile_id)

        assert result is None
        await self.postgres_helper.insert_snapshot(
            snapshot=self.factory.snapshots.snapshot(
                profile_id=profile_id,
                server_revision=1,
                game_run_id="run-1",
                current_content_fingerprint="fingerprint",
                snapshot_json=' {"runId":"run-1","history":[]} ',
            )
        )

        result = await self.storage.get_snapshot_archive(profile_id=profile_id)

        assert result == ' {"runId":"run-1","history":[]} '

    async def test_head_creation_lock_read_and_update(self) -> None:
        profile_id = UUID("b09682a3-1421-488c-a3e1-58b18ac94122")
        await self.storage.ensure_head(profile_id=profile_id, game_run_id="run-1")
        await self.storage.ensure_head(profile_id=profile_id, game_run_id="run-1")
        result = await self.storage.get_head_for_update(profile_id=profile_id, game_run_id="run-1")

        assert result == -1

        await self.storage.update_head(
            profile_id=profile_id,
            game_run_id="run-1",
            through_history_sequence=8,
        )
        result = await self.storage.get_head_for_update(profile_id=profile_id, game_run_id="run-1")

        assert result == 8
        stored = await self.postgres_helper.get_analytics_head(
            profile_id=profile_id, game_run_id="run-1"
        )
        assert stored is not None
        assert stored.through_history_sequence == 8

    async def test_batch_insert_and_read_preserves_ack(self) -> None:
        profile_id = UUID("b09682a3-1421-488c-a3e1-58b18ac94123")
        result = await self.storage.get_batch(profile_id=profile_id, batch_id="batch-1")

        assert result is None
        receipt = self.factory.analytics.stored_batch(
            profile_id=profile_id,
            result=self.factory.analytics.upload_result(
                sequence=3, event_ids=("event-1", "derived:4:run-1:interval")
            ),
        )
        result = await self.storage.insert_batch(batch=receipt)

        assert result is True
        result = await self.storage.insert_batch(batch=receipt)

        assert result is False

        result = await self.storage.get_batch(profile_id=profile_id, batch_id="batch-1")

        assert result == receipt

    async def test_original_fact_digests_are_stored_per_run(self) -> None:
        profile_id = UUID("b09682a3-1421-488c-a3e1-58b18ac94124")
        result = await self.storage.get_original_facts(profile_id=profile_id, game_run_id="run-1")

        assert result == {}

        await self.storage.insert_original_facts(
            profile_id=profile_id,
            game_run_id="run-1",
            facts={"event-1": "b" * 64, "event-2": "c" * 64},
        )

        result = await self.storage.get_original_facts(profile_id=profile_id, game_run_id="run-1")

        assert result == {"event-1": "b" * 64, "event-2": "c" * 64}
        result = await self.storage.get_original_facts(profile_id=profile_id, game_run_id="run-2")

        assert result == {}

    async def test_projection_replacement_uses_versioned_boundary(self) -> None:
        profile_id = UUID("b09682a3-1421-488c-a3e1-58b18ac94125")
        await self.storage.insert_projection(
            params=AnalyticsUploadParams(
                profile_id=profile_id,
                batch_id="batch-1",
                game_run_id="run-1",
                through_history_sequence=2,
                projection_version=4,
                evaluator_version=1,
                facts=[{"eventId": "event-1"}],
                skills=[{"skillId": "FIN-01"}],
            )
        )
        await self.storage.insert_projection(
            params=AnalyticsUploadParams(
                profile_id=profile_id,
                batch_id="batch-2",
                game_run_id="run-1",
                through_history_sequence=2,
                projection_version=4,
                evaluator_version=1,
                facts=[{"eventId": "event-2"}],
                skills=[{"skillId": "FIN-02"}],
            )
        )
        stored = await self.postgres_helper.get_analytics_projections(
            profile_id=profile_id, game_run_id="run-1"
        )

        assert len(stored) == 1
        assert stored[0].facts == [{"eventId": "event-2"}]
        assert stored[0].skills == [{"skillId": "FIN-02"}]

    async def test_latest_policy_assessment_is_read_without_inventing_status(self) -> None:
        profile_id = UUID("b09682a3-1421-488c-a3e1-58b18ac94126")
        result = await self.storage.get_assessment(profile_id=profile_id, game_run_id="run-1")

        assert result is None
        await self.postgres_helper.insert_skill_assessment(
            profile_id=profile_id,
            assessment=self.factory.analytics.assessment(
                sequence=2, policy_version="policy-1", status="PRACTICING"
            ),
        )
        await self.postgres_helper.insert_skill_assessment(
            profile_id=profile_id,
            assessment=self.factory.analytics.assessment(
                sequence=5, policy_version="policy-2", status="MASTERED"
            ),
        )

        result = await self.storage.get_assessment(profile_id=profile_id, game_run_id="run-1")

        assert result == self.factory.analytics.assessment(
            sequence=5, policy_version="policy-2", status="MASTERED"
        )

    async def test_equal_end_ranges_preserve_prior_projection(self) -> None:
        profile_id = UUID(int=101)
        first = self.factory.analytics.upload_params(profile_id=profile_id, sequence=901)
        await self.storage.insert_projection(params=first)
        await self.storage.insert_projection(
            params=replace(
                first,
                batch_id="batch-2",
                history_start_sequence=900,
                facts=[{"eventId": "event-901", "sequence": 901}],
            )
        )
        stored = await self.postgres_helper.get_analytics_projections(
            profile_id=profile_id, game_run_id="run-1"
        )
        assert len(stored) == 2
        assert {row.history_start_sequence for row in stored} == {0, 900}
        assert next(row for row in stored if row.history_start_sequence == 0).facts == []

        await self.storage.session.execute(
            delete(AnalyticsProjectionModel).where(
                AnalyticsProjectionModel.profile_id == profile_id
            )
        )

    async def test_registered_profile_uploads_without_snapshot_and_survives_session_refresh(
        self,
    ) -> None:
        profile_id = UUID(int=105)
        await self.postgres_helper.insert_profile(
            profile=self.factory.profiles.registered_profile(
                profile_id=profile_id, device_id="analytics-device"
            )
        )
        upload = self.factory.analytics.upload_params(
            profile_id=profile_id,
            sequence=901,
            facts=[
                {
                    "eventId": "after",
                    "gameRunId": "run-1",
                    "episodeId": "ep",
                    "actionId": "action",
                    "sequence": 901,
                    "detail": {"_type": "interaction", "name": "tap"},
                }
            ],
        )
        upload = replace(upload, history_start_sequence=900)
        use_case = UploadAnalyticsUseCase(analytics_storage=self.storage)
        result = await use_case.execute(params=upload, idempotency_key="batch-1")
        await self.storage.session.commit()
        self.storage.session.expunge_all()
        replay = await use_case.execute(params=upload, idempotency_key="batch-1")
        assert replay == result
        assert replay.accepted_event_ids == ("after",)
        assert await self.storage.get_original_fact_sequences(
            profile_id=profile_id, game_run_id="run-1"
        ) == {"after": 901}
        assert await self.storage.get_snapshot_archive(profile_id=profile_id) is None
        await self.storage.session.execute(
            delete(AnalyticsProjectionModel).where(
                AnalyticsProjectionModel.profile_id == profile_id
            )
        )
