from uuid import UUID

import pytest
from httpx2 import codes

from src.core.snapshots.exceptions import (
    InvalidSnapshotError,
    InvalidSnapshotRequestError,
    SnapshotGameRunConflictError,
    SnapshotIdempotencyConflictError,
    SnapshotNotFoundError,
    SnapshotRevisionConflictError,
)
from src.core.snapshots.use_cases import DownloadSnapshotUseCase, UploadSnapshotUseCase
from src.tests.fixtures import APIFixture, ContainerFixture, FactoryFixture


class TestUploadSnapshotAPI(APIFixture, ContainerFixture, FactoryFixture):
    @pytest.fixture(autouse=True)
    async def setup(self) -> None:
        self.use_case = await self.container_helper.override_use_case(
            use_case_type=UploadSnapshotUseCase,
        )

    async def test_first_upload_returns_created_response(self) -> None:
        self.use_case.execute.return_value = self.factory.snapshots.upload_result()

        response = await self.api.upload_snapshot(
            profile_id="12345678-1234-5678-1234-567812345678",
            upload_id="upload-1",
            expected_server_revision=None,
            game_run_id="run-1",
            through_history_sequence=0,
            current_content_fingerprint="catalog-v1",
            snapshot_format_version=4,
            checksum="a" * 64,
            snapshot_json=self.factory.snapshots.archive_json(),
        )

        assert response.status_code == codes.CREATED
        assert response.json() == {
            "uploadId": "upload-1",
            "gameRunId": "run-1",
            "serverRevision": 1,
            "checksum": "a" * 64,
        }
        self.use_case.execute.assert_awaited_once_with(
            params=self.factory.snapshots.upload_params(
                profile_id=UUID("12345678-1234-5678-1234-567812345678"),
            ),
            idempotency_key="upload-1",
        )

    async def test_update_returns_ok_response(self) -> None:
        self.use_case.execute.return_value = self.factory.snapshots.upload_result(
            upload_id="upload-2",
            server_revision=2,
            created=False,
        )

        response = await self.api.upload_snapshot(
            profile_id="12345678-1234-5678-1234-567812345678",
            upload_id="upload-2",
            expected_server_revision=1,
            game_run_id="run-1",
            through_history_sequence=0,
            current_content_fingerprint="catalog-v1",
            snapshot_format_version=4,
            checksum="a" * 64,
            snapshot_json=self.factory.snapshots.archive_json(),
        )

        assert response.status_code == codes.OK
        assert response.json() == {
            "uploadId": "upload-2",
            "gameRunId": "run-1",
            "serverRevision": 2,
            "checksum": "a" * 64,
        }
        self.use_case.execute.assert_awaited_once_with(
            params=self.factory.snapshots.upload_params(
                profile_id=UUID("12345678-1234-5678-1234-567812345678"),
                upload_id="upload-2",
                expected_server_revision=1,
            ),
            idempotency_key="upload-2",
        )

    async def test_maps_invalid_request(self) -> None:
        self.use_case.execute.side_effect = InvalidSnapshotRequestError

        response = await self.api.upload_snapshot(
            profile_id="12345678-1234-5678-1234-567812345678",
            upload_id="upload-1",
            expected_server_revision=None,
            game_run_id="run-1",
            through_history_sequence=0,
            current_content_fingerprint="catalog-v1",
            snapshot_format_version=4,
            checksum="a" * 64,
            snapshot_json=self.factory.snapshots.archive_json(),
        )

        assert response.status_code == codes.BAD_REQUEST
        assert response.json() == {"code": "INVALID_REQUEST"}
        self.use_case.execute.assert_awaited_once_with(
            params=self.factory.snapshots.upload_params(
                profile_id=UUID("12345678-1234-5678-1234-567812345678"),
            ),
            idempotency_key="upload-1",
        )

    async def test_maps_invalid_snapshot(self) -> None:
        self.use_case.execute.side_effect = InvalidSnapshotError

        response = await self.api.upload_snapshot(
            profile_id="12345678-1234-5678-1234-567812345678",
            upload_id="upload-1",
            expected_server_revision=None,
            game_run_id="run-1",
            through_history_sequence=0,
            current_content_fingerprint="catalog-v1",
            snapshot_format_version=4,
            checksum="a" * 64,
            snapshot_json=self.factory.snapshots.archive_json(),
        )

        assert response.status_code == codes.UNPROCESSABLE_CONTENT
        assert response.json() == {"code": "SNAPSHOT_INVALID"}
        self.use_case.execute.assert_awaited_once_with(
            params=self.factory.snapshots.upload_params(
                profile_id=UUID("12345678-1234-5678-1234-567812345678"),
            ),
            idempotency_key="upload-1",
        )

    async def test_maps_revision_conflict(self) -> None:
        self.use_case.execute.side_effect = SnapshotRevisionConflictError

        response = await self.api.upload_snapshot(
            profile_id="12345678-1234-5678-1234-567812345678",
            upload_id="upload-1",
            expected_server_revision=None,
            game_run_id="run-1",
            through_history_sequence=0,
            current_content_fingerprint="catalog-v1",
            snapshot_format_version=4,
            checksum="a" * 64,
            snapshot_json=self.factory.snapshots.archive_json(),
        )

        assert response.status_code == codes.CONFLICT
        assert response.json() == {"code": "SNAPSHOT_REVISION_CONFLICT"}
        self.use_case.execute.assert_awaited_once_with(
            params=self.factory.snapshots.upload_params(
                profile_id=UUID("12345678-1234-5678-1234-567812345678"),
            ),
            idempotency_key="upload-1",
        )

    async def test_maps_game_run_conflict(self) -> None:
        self.use_case.execute.side_effect = SnapshotGameRunConflictError

        response = await self.api.upload_snapshot(
            profile_id="12345678-1234-5678-1234-567812345678",
            upload_id="upload-1",
            expected_server_revision=None,
            game_run_id="run-1",
            through_history_sequence=0,
            current_content_fingerprint="catalog-v1",
            snapshot_format_version=4,
            checksum="a" * 64,
            snapshot_json=self.factory.snapshots.archive_json(),
        )

        assert response.status_code == codes.CONFLICT
        assert response.json() == {"code": "GAME_RUN_CONFLICT"}
        self.use_case.execute.assert_awaited_once_with(
            params=self.factory.snapshots.upload_params(
                profile_id=UUID("12345678-1234-5678-1234-567812345678"),
            ),
            idempotency_key="upload-1",
        )

    async def test_maps_idempotency_conflict(self) -> None:
        self.use_case.execute.side_effect = SnapshotIdempotencyConflictError

        response = await self.api.upload_snapshot(
            profile_id="12345678-1234-5678-1234-567812345678",
            upload_id="upload-1",
            expected_server_revision=None,
            game_run_id="run-1",
            through_history_sequence=0,
            current_content_fingerprint="catalog-v1",
            snapshot_format_version=4,
            checksum="a" * 64,
            snapshot_json=self.factory.snapshots.archive_json(),
        )

        assert response.status_code == codes.CONFLICT
        assert response.json() == {"code": "IDEMPOTENCY_CONFLICT"}
        self.use_case.execute.assert_awaited_once_with(
            params=self.factory.snapshots.upload_params(
                profile_id=UUID("12345678-1234-5678-1234-567812345678"),
            ),
            idempotency_key="upload-1",
        )

    async def test_rejects_incomplete_envelope_before_use_case(self) -> None:
        response = await self.api.upload_snapshot(
            profile_id="12345678-1234-5678-1234-567812345678",
            upload_id="upload-1",
        )

        assert response.status_code == codes.BAD_REQUEST
        assert response.json() == {"code": "INVALID_REQUEST"}
        self.use_case.execute.assert_not_awaited()


class TestDownloadSnapshotAPI(APIFixture, ContainerFixture, FactoryFixture):
    @pytest.fixture(autouse=True)
    async def setup(self) -> None:
        self.use_case = await self.container_helper.override_use_case(
            use_case_type=DownloadSnapshotUseCase,
        )

    async def test_download_returns_exact_archive(self) -> None:
        self.use_case.execute.return_value = self.factory.snapshots.snapshot(
            profile_id=UUID("12345678-1234-5678-1234-567812345678"),
        )

        response = await self.api.download_snapshot(
            profile_id="12345678-1234-5678-1234-567812345678",
        )

        assert response.status_code == codes.OK
        assert response.json() == {
            "schemaVersion": 1,
            "gameRunId": "run-1",
            "serverRevision": 1,
            "currentContentFingerprint": "catalog-v1",
            "snapshotJson": self.factory.snapshots.archive_json(),
        }
        self.use_case.execute.assert_awaited_once_with(
            profile_id=UUID("12345678-1234-5678-1234-567812345678"),
        )

    async def test_missing_snapshot_maps_to_not_found(self) -> None:
        self.use_case.execute.side_effect = SnapshotNotFoundError

        response = await self.api.download_snapshot(
            profile_id="12345678-1234-5678-1234-567812345678",
        )

        assert response.status_code == codes.NOT_FOUND
        assert response.json() == {"code": "SNAPSHOT_NOT_FOUND"}
        self.use_case.execute.assert_awaited_once_with(
            profile_id=UUID("12345678-1234-5678-1234-567812345678"),
        )
