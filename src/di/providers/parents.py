from dishka import Provider, Scope, provide

from src.core.analytics.storages import AnalyticsStorage
from src.core.parents.use_cases import GetParentReportUseCase
from src.core.profiles.storages import ProfileStorage
from src.core.snapshots.storages import SnapshotStorage


class ParentsProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def get_parent_report_use_case(
        self,
        profile_storage: ProfileStorage,
        snapshot_storage: SnapshotStorage,
        analytics_storage: AnalyticsStorage,
    ) -> GetParentReportUseCase:
        return GetParentReportUseCase(
            profile_storage=profile_storage,
            snapshot_storage=snapshot_storage,
            analytics_storage=analytics_storage,
        )
