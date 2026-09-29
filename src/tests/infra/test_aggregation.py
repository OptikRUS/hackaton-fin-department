import asyncio
from collections.abc import Iterator
from contextlib import AbstractAsyncContextManager
from typing import Any, Self
from uuid import uuid4

import pytest
from prometheus_client import CollectorRegistry

from src.infra.observability.aggregation import Aggregator
from src.infra.observability.business_metrics import BusinessMetrics
from src.tests.helpers.worlds import world_snapshot_json


class _BrokenStorageError(RuntimeError):
    pass


class _FakeResult:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def __iter__(self) -> Iterator[Any]:
        return iter(self._rows)


class _FakeSession:
    def __init__(
        self, heads: list[tuple[str, str]], counts: int = 0, skills: list[Any] | None = None
    ) -> None:
        self._heads = heads
        self._counts = counts
        self._skills = skills or []
        self.execute_calls = 0

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def execute(self, _statement: object) -> _FakeResult:
        self.execute_calls += 1
        if self.execute_calls == 1:
            return _FakeResult(self._heads)
        return _FakeResult(self._skills)

    async def scalar(self, _statement: object) -> int:
        return self._counts


@pytest.fixture
def metrics() -> BusinessMetrics:
    return BusinessMetrics(registry=CollectorRegistry())


async def test_collect_once_publishes_worlds(metrics: BusinessMetrics) -> None:
    heads = [
        ("run-1", world_snapshot_json()),
        ("run-1", world_snapshot_json()),
        ("run-2", "garbage"),
    ]
    session = _FakeSession(
        heads=heads,
        counts=2,
        skills=[(uuid4(), "run-1", 12, [{"skillId": "FIN-03", "completedEpisodes": 2}])],
    )

    def session_factory() -> AbstractAsyncContextManager[Any]:
        return session

    aggregator = Aggregator(metrics=metrics, interval_seconds=60, session_factory=session_factory)

    await aggregator.collect_once()

    assert metrics.registry.get_sample_value("fin_worlds_total") == 2
    assert metrics.registry.get_sample_value("fin_game_runs_total") == 2
    assert metrics.registry.get_sample_value("fin_profiles_total") == 2
    assert metrics.registry.get_sample_value("fin_aggregation_parse_errors_total") == 1
    assert metrics.registry.get_sample_value("fin_aggregation_last_success_unixtime") is not None


async def test_run_forever_collects_until_stop(metrics: BusinessMetrics) -> None:
    session = _FakeSession(heads=[], counts=0)

    def session_factory() -> AbstractAsyncContextManager[Any]:
        return session

    aggregator = Aggregator(metrics=metrics, interval_seconds=0.01, session_factory=session_factory)
    stop = asyncio.Event()
    task = asyncio.create_task(aggregator.run_forever(stop))
    await asyncio.sleep(0.05)
    stop.set()
    await task

    assert session.execute_calls >= 2


async def test_run_forever_counts_errors_and_keeps_going(metrics: BusinessMetrics) -> None:
    def session_factory() -> AbstractAsyncContextManager[Any]:
        raise _BrokenStorageError

    aggregator = Aggregator(metrics=metrics, interval_seconds=0.01, session_factory=session_factory)
    stop = asyncio.Event()
    task = asyncio.create_task(aggregator.run_forever(stop))
    await asyncio.sleep(0.05)
    stop.set()
    await task

    errors = metrics.registry.get_sample_value("fin_aggregation_errors_total")
    assert errors is not None
    assert errors >= 1
