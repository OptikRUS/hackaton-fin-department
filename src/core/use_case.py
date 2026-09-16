from abc import ABCMeta, abstractmethod
from typing import Any


class UseCase(metaclass=ABCMeta):
    @abstractmethod
    async def execute(self, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        raise NotImplementedError
