from dishka import Provider, Scope, provide

from src.core.snapshots.storages import SnapshotStorage
from src.core.snapshots.use_cases import DownloadSnapshotUseCase, UploadSnapshotUseCase
from src.infra.observability.business_metrics import BusinessMetrics


class SnapshotsProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def get_upload_snapshot_use_case(
        self,
        storage: SnapshotStorage,
        metrics: BusinessMetrics,
    ) -> UploadSnapshotUseCase:
        return UploadSnapshotUseCase(snapshot_storage=storage, metrics=metrics)

    @provide(scope=Scope.REQUEST)
    def get_download_snapshot_use_case(
        self,
        storage: SnapshotStorage,
        metrics: BusinessMetrics,
    ) -> DownloadSnapshotUseCase:
        return DownloadSnapshotUseCase(snapshot_storage=storage, metrics=metrics)
