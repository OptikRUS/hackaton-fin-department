from typing import cast
from unittest.mock import AsyncMock

from dishka import Provider, Scope, provide

from src.core.profiles.use_cases import RegisterProfileUseCase


class MockProfilesUseCaseProvider(Provider):
    @provide(scope=Scope.APP)
    def get_register_profile_use_case(self) -> RegisterProfileUseCase:
        return cast("RegisterProfileUseCase", AsyncMock(spec=RegisterProfileUseCase))
