from typing import cast
from unittest.mock import AsyncMock

from dishka import Provider, Scope, provide

from src.core.pets.use_cases import CreatePetUseCase


class MockPetsUseCaseProvider(Provider):
    @provide(scope=Scope.APP)
    def get_create_pet_use_case(self) -> CreatePetUseCase:
        return cast("CreatePetUseCase", AsyncMock(spec=CreatePetUseCase))
