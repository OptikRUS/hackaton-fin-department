from abc import ABCMeta, abstractmethod
from collections.abc import Sequence
from typing import Any


class MetricsSink(metaclass=ABCMeta):
    """Business observability port; implementations must never raise from observe methods."""

    @abstractmethod
    def observe_snapshot_upload(self, *, created: bool) -> None:
        raise NotImplementedError

    @abstractmethod
    def observe_snapshot_download(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def observe_analytics_batch(self, *, created: bool, facts: list[dict[str, Any]]) -> None:
        raise NotImplementedError

    @abstractmethod
    def observe_profile_registration(self, *, created: bool) -> None:
        raise NotImplementedError

    @abstractmethod
    def observe_pet_created(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def observe_reward_issued(self, *, reward_type: str, created: bool) -> None:
        raise NotImplementedError

    @abstractmethod
    def observe_rewards_acknowledged(self, *, outcomes: Sequence[str]) -> None:
        raise NotImplementedError
