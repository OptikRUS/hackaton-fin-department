from typing import cast
from unittest.mock import AsyncMock

from dishka import Provider, Scope, provide

from src.core.snapshots.use_cases import DownloadSnapshotUseCase, UploadSnapshotUseCase


class MockSnapshotsUseCaseProvider(Provider):
    @provide(scope=Scope.APP)
    def get_upload_snapshot_use_case(self) -> UploadSnapshotUseCase:
        return cast("UploadSnapshotUseCase", AsyncMock(spec=UploadSnapshotUseCase))

    @provide(scope=Scope.APP)
    def get_download_snapshot_use_case(self) -> DownloadSnapshotUseCase:
        return cast("DownloadSnapshotUseCase", AsyncMock(spec=DownloadSnapshotUseCase))
