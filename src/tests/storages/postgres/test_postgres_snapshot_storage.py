from uuid import UUID

import pytest

from src.infra.storages.postgres.snapshot_storage import PostgresSnapshotStorage
from src.tests.fixtures import FactoryFixture, PostgresFixture


class TestPostgresSnapshotStorage(FactoryFixture, PostgresFixture):
    @pytest.fixture(autouse=True)
    async def setup(self, snapshot_storage: PostgresSnapshotStorage) -> None:
        self.storage = snapshot_storage

    async def test_ensure_head_creates_lock_row(self) -> None:
        await self.storage.ensure_head(
            profile_id=UUID("12345678-1234-5678-1234-567812345678"),
        )

        model = await self.postgres_helper.get_snapshot_head(
            profile_id=UUID("12345678-1234-5678-1234-567812345678"),
        )

        assert model is not None
        assert model.to_head() == self.factory.snapshots.head(
            profile_id=UUID("12345678-1234-5678-1234-567812345678"),
        )

    async def test_ensure_head_preserves_saved_snapshot(self) -> None:
        await self.postgres_helper.insert_snapshot(
            snapshot=self.factory.snapshots.snapshot(
                profile_id=UUID("12345678-1234-5678-1234-567812345678"),
            ),
        )

        await self.storage.ensure_head(
            profile_id=UUID("12345678-1234-5678-1234-567812345678"),
        )

        model = await self.postgres_helper.get_snapshot_head(
            profile_id=UUID("12345678-1234-5678-1234-567812345678"),
        )

        assert model is not None
        assert model.to_domain() == self.factory.snapshots.snapshot(
            profile_id=UUID("12345678-1234-5678-1234-567812345678"),
        )

    async def test_get_head_for_update_reads_current_revision(self) -> None:
        await self.postgres_helper.insert_snapshot(
            snapshot=self.factory.snapshots.snapshot(
                profile_id=UUID("12345678-1234-5678-1234-567812345678"),
                server_revision=2,
            ),
        )

        result = await self.storage.get_head_for_update(
            profile_id=UUID("12345678-1234-5678-1234-567812345678"),
        )

        assert result == self.factory.snapshots.head(
            profile_id=UUID("12345678-1234-5678-1234-567812345678"),
            server_revision=2,
            game_run_id="run-1",
        )

    async def test_get_upload_returns_none_for_unknown_id(self) -> None:
        assert (
            await self.storage.get_upload(
                profile_id=UUID("12345678-1234-5678-1234-567812345678"),
                upload_id="missing",
            )
            is None
        )

    async def test_get_upload_returns_existing_receipt(self) -> None:
        await self.postgres_helper.insert_snapshot_upload(
            upload=self.factory.snapshots.receipt(
                profile_id=UUID("12345678-1234-5678-1234-567812345678"),
                request_digest="b" * 64,
            ),
        )

        assert await self.storage.get_upload(
            profile_id=UUID("12345678-1234-5678-1234-567812345678"),
            upload_id="upload-1",
        ) == self.factory.snapshots.receipt(
            profile_id=UUID("12345678-1234-5678-1234-567812345678"),
            request_digest="b" * 64,
        )

    async def test_insert_upload_persists_receipt(self) -> None:
        result = await self.storage.insert_upload(
            upload=self.factory.snapshots.receipt(
                profile_id=UUID("12345678-1234-5678-1234-567812345678"),
                request_digest="b" * 64,
            ),
        )

        model = await self.postgres_helper.get_snapshot_upload(
            profile_id=UUID("12345678-1234-5678-1234-567812345678"),
            upload_id="upload-1",
        )

        assert result == self.factory.snapshots.receipt(
            profile_id=UUID("12345678-1234-5678-1234-567812345678"),
            request_digest="b" * 64,
        )
        assert model is not None
        assert model.to_domain() == result

    async def test_replace_head_persists_exact_snapshot(self) -> None:
        await self.storage.ensure_head(
            profile_id=UUID("12345678-1234-5678-1234-567812345678"),
        )

        result = await self.storage.replace_head(
            snapshot=self.factory.snapshots.snapshot(
                profile_id=UUID("12345678-1234-5678-1234-567812345678"),
                snapshot_json=' {"formatVersion":4,"runId":"run-1"} ',
            ),
        )
        model = await self.postgres_helper.get_snapshot_head(
            profile_id=UUID("12345678-1234-5678-1234-567812345678"),
        )

        assert result == self.factory.snapshots.snapshot(
            profile_id=UUID("12345678-1234-5678-1234-567812345678"),
            snapshot_json=' {"formatVersion":4,"runId":"run-1"} ',
        )
        assert model is not None
        assert model.to_domain() == result

    async def test_get_latest_returns_none_without_row(self) -> None:
        assert (
            await self.storage.get_latest(
                profile_id=UUID("12345678-1234-5678-1234-567812345678"),
            )
            is None
        )

    async def test_get_latest_returns_none_for_lock_row(self) -> None:
        await self.storage.ensure_head(
            profile_id=UUID("12345678-1234-5678-1234-567812345678"),
        )

        assert (
            await self.storage.get_latest(
                profile_id=UUID("12345678-1234-5678-1234-567812345678"),
            )
            is None
        )

    async def test_get_latest_returns_saved_snapshot(self) -> None:
        await self.postgres_helper.insert_snapshot(
            snapshot=self.factory.snapshots.snapshot(
                profile_id=UUID("12345678-1234-5678-1234-567812345678"),
            ),
        )

        assert await self.storage.get_latest(
            profile_id=UUID("12345678-1234-5678-1234-567812345678"),
        ) == self.factory.snapshots.snapshot(
            profile_id=UUID("12345678-1234-5678-1234-567812345678"),
        )
