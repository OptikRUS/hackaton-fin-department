from unittest.mock import AsyncMock, call
from uuid import UUID

import pytest

from src.core.snapshots.exceptions import (
    InvalidSnapshotError,
    InvalidSnapshotRequestError,
    SnapshotGameRunConflictError,
    SnapshotIdempotencyConflictError,
    SnapshotNotFoundError,
    SnapshotRevisionConflictError,
)
from src.core.snapshots.storages import SnapshotStorage
from src.core.snapshots.use_cases import DownloadSnapshotUseCase, UploadSnapshotUseCase
from src.tests.fixtures import FactoryFixture


class TestUploadSnapshotParams(FactoryFixture):
    def test_validates_snapshot(self) -> None:
        self.factory.snapshots.upload_params(
            profile_id=UUID("12345678-1234-5678-1234-567812345678"),
        ).validate(idempotency_key="upload-1")

    def test_calculates_request_digest(self) -> None:
        assert (
            self.factory.snapshots.upload_params(
                profile_id=UUID("12345678-1234-5678-1234-567812345678"),
            ).request_digest()
            == "3fa562f122079c2c5bb8026bfb4e18bfd09f7fcf09cc818847ea91984fc5d636"
        )


class TestUploadSnapshotUseCase(FactoryFixture):
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.storage = AsyncMock(spec=SnapshotStorage)
        self.storage.get_head_for_update.return_value = self.factory.snapshots.head(
            profile_id=UUID("12345678-1234-5678-1234-567812345678"),
        )
        self.storage.get_upload.return_value = None
        self.use_case = UploadSnapshotUseCase(snapshot_storage=self.storage)

    async def test_stores_first_snapshot_in_order(self) -> None:
        result = await self.use_case.execute(
            params=self.factory.snapshots.upload_params(
                profile_id=UUID("12345678-1234-5678-1234-567812345678"),
            ),
            idempotency_key="upload-1",
        )

        assert result == self.factory.snapshots.upload_result()
        assert self.storage.mock_calls == [
            call.ensure_head(profile_id=UUID("12345678-1234-5678-1234-567812345678")),
            call.get_head_for_update(profile_id=UUID("12345678-1234-5678-1234-567812345678")),
            call.get_upload(
                profile_id=UUID("12345678-1234-5678-1234-567812345678"),
                upload_id="upload-1",
            ),
            call.replace_head(
                snapshot=self.factory.snapshots.snapshot(
                    profile_id=UUID("12345678-1234-5678-1234-567812345678"),
                ),
            ),
            call.insert_upload(
                upload=self.factory.snapshots.receipt(
                    profile_id=UUID("12345678-1234-5678-1234-567812345678"),
                    request_digest="3fa562f122079c2c5bb8026bfb4e18bfd09f7fcf09cc818847ea91984fc5d636",
                ),
            ),
        ]

    async def test_updates_snapshot_and_revision(self) -> None:
        self.storage.get_head_for_update.return_value = self.factory.snapshots.head(
            profile_id=UUID("12345678-1234-5678-1234-567812345678"),
            server_revision=1,
            game_run_id="run-1",
        )

        result = await self.use_case.execute(
            params=self.factory.snapshots.upload_params(
                profile_id=UUID("12345678-1234-5678-1234-567812345678"),
                upload_id="upload-2",
                expected_server_revision=1,
            ),
            idempotency_key="upload-2",
        )

        assert result == self.factory.snapshots.upload_result(
            upload_id="upload-2",
            server_revision=2,
            created=False,
        )
        self.storage.replace_head.assert_awaited_once_with(
            snapshot=self.factory.snapshots.snapshot(
                profile_id=UUID("12345678-1234-5678-1234-567812345678"),
                server_revision=2,
            ),
        )
        self.storage.insert_upload.assert_awaited_once()

    async def test_replays_original_result_after_newer_upload(self) -> None:
        self.storage.get_head_for_update.return_value = self.factory.snapshots.head(
            profile_id=UUID("12345678-1234-5678-1234-567812345678"),
            server_revision=2,
            game_run_id="run-1",
        )
        self.storage.get_upload.return_value = self.factory.snapshots.receipt(
            profile_id=UUID("12345678-1234-5678-1234-567812345678"),
            request_digest="3fa562f122079c2c5bb8026bfb4e18bfd09f7fcf09cc818847ea91984fc5d636",
        )

        result = await self.use_case.execute(
            params=self.factory.snapshots.upload_params(
                profile_id=UUID("12345678-1234-5678-1234-567812345678"),
            ),
            idempotency_key="upload-1",
        )

        assert result == self.factory.snapshots.upload_result()
        self.storage.replace_head.assert_not_awaited()
        self.storage.insert_upload.assert_not_awaited()

    async def test_rejects_changed_request_with_same_upload_id(self) -> None:
        self.storage.get_upload.return_value = self.factory.snapshots.receipt(
            profile_id=UUID("12345678-1234-5678-1234-567812345678"),
            request_digest="different",
        )

        with pytest.raises(SnapshotIdempotencyConflictError):
            await self.use_case.execute(
                params=self.factory.snapshots.upload_params(
                    profile_id=UUID("12345678-1234-5678-1234-567812345678"),
                ),
                idempotency_key="upload-1",
            )

        self.storage.replace_head.assert_not_awaited()
        self.storage.insert_upload.assert_not_awaited()

    async def test_rejects_expected_revision_on_first_upload(self) -> None:
        with pytest.raises(SnapshotRevisionConflictError):
            await self.use_case.execute(
                params=self.factory.snapshots.upload_params(
                    profile_id=UUID("12345678-1234-5678-1234-567812345678"),
                    expected_server_revision=1,
                ),
                idempotency_key="upload-1",
            )

        self.storage.replace_head.assert_not_awaited()

    async def test_rejects_stale_revision(self) -> None:
        self.storage.get_head_for_update.return_value = self.factory.snapshots.head(
            profile_id=UUID("12345678-1234-5678-1234-567812345678"),
            server_revision=2,
            game_run_id="run-1",
        )

        with pytest.raises(SnapshotRevisionConflictError):
            await self.use_case.execute(
                params=self.factory.snapshots.upload_params(
                    profile_id=UUID("12345678-1234-5678-1234-567812345678"),
                    upload_id="upload-2",
                    expected_server_revision=1,
                ),
                idempotency_key="upload-2",
            )

        self.storage.replace_head.assert_not_awaited()

    async def test_rejects_another_game_run(self) -> None:
        self.storage.get_head_for_update.return_value = self.factory.snapshots.head(
            profile_id=UUID("12345678-1234-5678-1234-567812345678"),
            server_revision=1,
            game_run_id="run-1",
        )

        with pytest.raises(SnapshotGameRunConflictError):
            await self.use_case.execute(
                params=self.factory.snapshots.upload_params(
                    profile_id=UUID("12345678-1234-5678-1234-567812345678"),
                    upload_id="upload-2",
                    expected_server_revision=1,
                    game_run_id="run-2",
                ),
                idempotency_key="upload-2",
            )

        self.storage.replace_head.assert_not_awaited()

    async def test_rejects_mismatched_idempotency_key_before_storage(self) -> None:
        with pytest.raises(InvalidSnapshotRequestError):
            await self.use_case.execute(
                params=self.factory.snapshots.upload_params(
                    profile_id=UUID("12345678-1234-5678-1234-567812345678"),
                ),
                idempotency_key="another-upload",
            )

        self.storage.ensure_head.assert_not_awaited()

    async def test_rejects_upload_id_over_255_bytes(self) -> None:
        with pytest.raises(InvalidSnapshotRequestError):
            await self.use_case.execute(
                params=self.factory.snapshots.upload_params(
                    profile_id=UUID("12345678-1234-5678-1234-567812345678"),
                    upload_id="é" * 128,
                ),
                idempotency_key="é" * 128,
            )

        self.storage.ensure_head.assert_not_awaited()

    async def test_rejects_nul_in_postgres_text(self) -> None:
        with pytest.raises(InvalidSnapshotRequestError):
            await self.use_case.execute(
                params=self.factory.snapshots.upload_params(
                    profile_id=UUID("12345678-1234-5678-1234-567812345678"),
                    game_run_id="run\x00id",
                ),
                idempotency_key="upload-1",
            )

        self.storage.ensure_head.assert_not_awaited()

    async def test_rejects_invalid_json(self) -> None:
        with pytest.raises(InvalidSnapshotError):
            await self.use_case.execute(
                params=self.factory.snapshots.upload_params(
                    profile_id=UUID("12345678-1234-5678-1234-567812345678"),
                    snapshot_json="{bad-json",
                ),
                idempotency_key="upload-1",
            )

        self.storage.ensure_head.assert_not_awaited()

    async def test_rejects_non_json_numeric_constant(self) -> None:
        with pytest.raises(InvalidSnapshotError):
            await self.use_case.execute(
                params=self.factory.snapshots.upload_params(
                    profile_id=UUID("12345678-1234-5678-1234-567812345678"),
                    snapshot_json=self.factory.snapshots.archive_json()[:-1] + ',"state":NaN}',
                ),
                idempotency_key="upload-1",
            )

        self.storage.ensure_head.assert_not_awaited()

    async def test_rejects_mismatched_format_version(self) -> None:
        with pytest.raises(InvalidSnapshotError):
            await self.use_case.execute(
                params=self.factory.snapshots.upload_params(
                    profile_id=UUID("12345678-1234-5678-1234-567812345678"),
                    snapshot_json=self.factory.snapshots.archive_json(format_version=3),
                ),
                idempotency_key="upload-1",
            )

        self.storage.ensure_head.assert_not_awaited()

    async def test_rejects_mismatched_game_run(self) -> None:
        with pytest.raises(InvalidSnapshotError):
            await self.use_case.execute(
                params=self.factory.snapshots.upload_params(
                    profile_id=UUID("12345678-1234-5678-1234-567812345678"),
                    snapshot_json=self.factory.snapshots.archive_json(run_id="run-2"),
                ),
                idempotency_key="upload-1",
            )

        self.storage.ensure_head.assert_not_awaited()

    async def test_rejects_mismatched_history_sequence(self) -> None:
        with pytest.raises(InvalidSnapshotError):
            await self.use_case.execute(
                params=self.factory.snapshots.upload_params(
                    profile_id=UUID("12345678-1234-5678-1234-567812345678"),
                    snapshot_json=self.factory.snapshots.archive_json(history_sequence=1),
                ),
                idempotency_key="upload-1",
            )

        self.storage.ensure_head.assert_not_awaited()

    async def test_rejects_mismatched_checksum(self) -> None:
        with pytest.raises(InvalidSnapshotError):
            await self.use_case.execute(
                params=self.factory.snapshots.upload_params(
                    profile_id=UUID("12345678-1234-5678-1234-567812345678"),
                    snapshot_json=self.factory.snapshots.archive_json(checksum="b" * 64),
                ),
                idempotency_key="upload-1",
            )

        self.storage.ensure_head.assert_not_awaited()


class TestDownloadSnapshotUseCase(FactoryFixture):
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.storage = AsyncMock(spec=SnapshotStorage)
        self.use_case = DownloadSnapshotUseCase(snapshot_storage=self.storage)

    async def test_raises_not_found_when_storage_is_empty(self) -> None:
        self.storage.get_latest.return_value = None

        with pytest.raises(SnapshotNotFoundError):
            await self.use_case.execute(
                profile_id=UUID("12345678-1234-5678-1234-567812345678"),
            )

        self.storage.get_latest.assert_awaited_once_with(
            profile_id=UUID("12345678-1234-5678-1234-567812345678"),
        )

    async def test_returns_stored_snapshot(self) -> None:
        self.storage.get_latest.return_value = self.factory.snapshots.snapshot(
            profile_id=UUID("12345678-1234-5678-1234-567812345678"),
        )

        result = await self.use_case.execute(
            profile_id=UUID("12345678-1234-5678-1234-567812345678"),
        )

        assert result == self.factory.snapshots.snapshot(
            profile_id=UUID("12345678-1234-5678-1234-567812345678"),
        )
        self.storage.get_latest.assert_awaited_once_with(
            profile_id=UUID("12345678-1234-5678-1234-567812345678"),
        )
