from dataclasses import dataclass
from typing import cast
from unittest.mock import AsyncMock

from dishka import AsyncContainer

from src.core.use_case import UseCase


@dataclass(kw_only=True, slots=True)
class ContainerHelper:
    container: AsyncContainer

    async def override_use_case[T: UseCase](self, use_case_type: type[T]) -> AsyncMock:
        return cast("AsyncMock", await self.container.get(use_case_type))
