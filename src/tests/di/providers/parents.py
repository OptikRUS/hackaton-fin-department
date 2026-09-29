from typing import cast
from unittest.mock import AsyncMock

from dishka import Provider, Scope, provide

from src.core.parents.use_cases import GetParentReportUseCase


class MockParentsUseCaseProvider(Provider):
    @provide(scope=Scope.APP)
    def get_parent_report_use_case(self) -> GetParentReportUseCase:
        return cast("GetParentReportUseCase", AsyncMock(spec=GetParentReportUseCase))
