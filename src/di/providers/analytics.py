from dishka import Provider, Scope, provide

from src.core.analytics.storages import AnalyticsStorage
from src.core.analytics.use_cases import GetSkillAssessmentsUseCase, UploadAnalyticsUseCase


class AnalyticsProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def get_upload_analytics_use_case(self, storage: AnalyticsStorage) -> UploadAnalyticsUseCase:
        return UploadAnalyticsUseCase(analytics_storage=storage)

    @provide(scope=Scope.REQUEST)
    def get_skill_assessments_use_case(
        self,
        storage: AnalyticsStorage,
    ) -> GetSkillAssessmentsUseCase:
        return GetSkillAssessmentsUseCase(analytics_storage=storage)
