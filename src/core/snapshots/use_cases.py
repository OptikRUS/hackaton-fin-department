from dataclasses import dataclass
from uuid import UUID

from src.core.metrics import MetricsSink
from src.core.snapshots.exceptions import (
    SnapshotGameRunConflictError,
    SnapshotIdempotencyConflictError,
    SnapshotNotFoundError,
    SnapshotRevisionConflictError,
)
from src.core.snapshots.schemas import (
    Snapshot,
    SnapshotUploadReceipt,
    UploadSnapshotParams,
    UploadSnapshotResult,
)
from src.core.snapshots.storages import SnapshotStorage
from src.core.use_case import UseCase


@dataclass(frozen=True, slots=True, kw_only=True)
class UploadSnapshotUseCase(UseCase):
    snapshot_storage: SnapshotStorage
    metrics: MetricsSink | None = None

    async def execute(
        self,
        *,
        params: UploadSnapshotParams,
        idempotency_key: str,
    ) -> UploadSnapshotResult:
        params.validate(idempotency_key=idempotency_key)
        request_digest = params.request_digest()

        await self.snapshot_storage.ensure_head(profile_id=params.profile_id)
        head = await self.snapshot_storage.get_head_for_update(profile_id=params.profile_id)
        previous_upload = await self.snapshot_storage.get_upload(
            profile_id=params.profile_id,
            upload_id=params.upload_id,
        )
        if previous_upload is not None:
            if previous_upload.request_digest != request_digest:
                raise SnapshotIdempotencyConflictError
            return previous_upload.result

        if head.server_revision == 0:
            if params.expected_server_revision is not None:
                raise SnapshotRevisionConflictError
        elif params.expected_server_revision != head.server_revision:
            raise SnapshotRevisionConflictError

        if head.server_revision > 0:
            previous_snapshot = await self.snapshot_storage.get_latest(profile_id=params.profile_id)
            if previous_snapshot is None:
                raise SnapshotGameRunConflictError
            params.validate_continuation(previous=previous_snapshot)

        result = UploadSnapshotResult(
            upload_id=params.upload_id,
            game_run_id=params.game_run_id,
            server_revision=head.server_revision + 1,
            checksum=params.checksum,
            created=head.server_revision == 0,
        )
        await self.snapshot_storage.replace_head(
            snapshot=Snapshot(
                profile_id=params.profile_id,
                game_run_id=params.game_run_id,
                server_revision=result.server_revision,
                current_content_fingerprint=params.current_content_fingerprint,
                snapshot_json=params.snapshot_json,
            ),
        )
        await self.snapshot_storage.insert_upload(
            upload=SnapshotUploadReceipt(
                profile_id=params.profile_id,
                request_digest=request_digest,
                result=result,
            ),
        )
        if self.metrics is not None:
            self.metrics.observe_snapshot_upload(created=result.created)
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class DownloadSnapshotUseCase(UseCase):
    snapshot_storage: SnapshotStorage
    metrics: MetricsSink | None = None

    async def execute(self, *, profile_id: UUID) -> Snapshot:
        snapshot = await self.snapshot_storage.get_latest(profile_id=profile_id)
        if snapshot is None:
            raise SnapshotNotFoundError
        if self.metrics is not None:
            self.metrics.observe_snapshot_download()
        return snapshot
