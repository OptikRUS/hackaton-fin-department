from datetime import UTC, datetime
from uuid import UUID

from src.core.analytics.schemas import AnalyticsUploadParams
from src.infra.storages.postgres.analytics_storage import PostgresAnalyticsStorage
from src.infra.storages.postgres.snapshot_storage import PostgresSnapshotStorage
from src.tests.fixtures import FactoryFixture, PostgresFixture


class TestProfileLastSync(FactoryFixture, PostgresFixture):
    async def test_snapshot_records_server_time_and_rolls_back_atomically(
        self, snapshot_storage: PostgresSnapshotStorage
    ) -> None:
        profile_id = UUID("00000000-0000-0000-0000-000000000101")
        await self.postgres_helper.insert_profile(
            profile=self.factory.profiles.registered_profile(
                profile_id=profile_id, device_id=str(profile_id)
            )
        )
        profile = await self.postgres_helper.get_profile(profile_id=profile_id)
        assert profile is not None
        assert getattr(profile, "last_synced_at", None) is None
        await snapshot_storage.ensure_head(profile_id=profile_id)
        savepoint = await snapshot_storage.session.begin_nested()
        before = datetime.now(UTC)
        await snapshot_storage.replace_head(
            snapshot=self.factory.snapshots.snapshot(profile_id=profile_id)
        )
        await snapshot_storage.session.refresh(profile)
        synced = getattr(profile, "last_synced_at", None)
        assert synced is not None, "Accepted snapshot must record last synchronization"
        assert before <= synced <= datetime.now(UTC)
        await savepoint.rollback()
        await snapshot_storage.session.refresh(profile)
        assert profile.last_synced_at is None

    async def test_analytics_records_server_time_and_reads_do_not_change_it(
        self, analytics_storage: PostgresAnalyticsStorage
    ) -> None:
        profile_id = UUID("00000000-0000-0000-0000-000000000102")
        await self.postgres_helper.insert_profile(
            profile=self.factory.profiles.registered_profile(
                profile_id=profile_id, device_id=str(profile_id)
            )
        )
        profile = await self.postgres_helper.get_profile(profile_id=profile_id)
        assert profile is not None
        assert getattr(profile, "last_synced_at", None) is None
        before = datetime.now(UTC)
        await analytics_storage.insert_projection(
            params=AnalyticsUploadParams(
                profile_id=profile_id,
                batch_id="batch-sync",
                game_run_id="run-1",
                through_history_sequence=1,
                projection_version=4,
                evaluator_version=1,
                facts=[],
                skills=[],
            )
        )
        await analytics_storage.session.refresh(profile)
        synced = getattr(profile, "last_synced_at", None)
        assert synced is not None, "Accepted analytics must record last synchronization"
        assert before <= synced <= datetime.now(UTC)
        await analytics_storage.get_snapshot_archive(profile_id=profile_id)
        await analytics_storage.ensure_head(profile_id=profile_id, game_run_id="run-1")
        await analytics_storage.session.refresh(profile)
        assert profile.last_synced_at == synced
