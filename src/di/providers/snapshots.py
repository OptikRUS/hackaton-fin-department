from dishka import Provider, Scope, provide

from src.core.snapshots.storages import SnapshotStorage
from src.core.snapshots.use_cases import DownloadSnapshotUseCase, UploadSnapshotUseCase


class SnapshotsProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def get_upload_snapshot_use_case(self, storage: SnapshotStorage) -> UploadSnapshotUseCase:
        return UploadSnapshotUseCase(snapshot_storage=storage)

    @provide(scope=Scope.REQUEST)
    def get_download_snapshot_use_case(self, storage: SnapshotStorage) -> DownloadSnapshotUseCase:
        return DownloadSnapshotUseCase(snapshot_storage=storage)
