from typing import cast
from unittest.mock import AsyncMock

from dishka import Provider, Scope, provide

from src.core.analytics.use_cases import GetSkillAssessmentsUseCase, UploadAnalyticsUseCase


class MockAnalyticsUseCaseProvider(Provider):
    @provide(scope=Scope.APP)
    def get_upload_analytics_use_case(self) -> UploadAnalyticsUseCase:
        return cast("UploadAnalyticsUseCase", AsyncMock(spec=UploadAnalyticsUseCase))

    @provide(scope=Scope.APP)
    def get_skill_assessments_use_case(self) -> GetSkillAssessmentsUseCase:
        return cast("GetSkillAssessmentsUseCase", AsyncMock(spec=GetSkillAssessmentsUseCase))
