import asyncio
import time
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager, suppress
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select

from src.infra.observability.business_metrics import (
    BusinessMetrics,
    WorldSample,
    parse_world_sample,
)
from src.infra.storages.postgres.config import async_session
from src.infra.storages.postgres.models import (
    AnalyticsProjectionModel,
    PetModel,
    ProfileModel,
    SnapshotHeadModel,
)


@dataclass(frozen=True, slots=True)
class Aggregator:
    """Periodically reads stored worlds and republishes instant business gauges/distributions."""

    metrics: BusinessMetrics
    interval_seconds: float
    session_factory: Callable[[], AbstractAsyncContextManager[Any]] = async_session

    async def run_forever(self, stop: asyncio.Event) -> None:
        while not stop.is_set():
            try:
                await self.collect_once()
            except Exception:  # noqa: BLE001
                self.metrics.observe_aggregation_error()
            with suppress(asyncio.TimeoutError):
                await asyncio.wait_for(stop.wait(), timeout=self.interval_seconds)

    async def collect_once(self) -> None:
        started = time.monotonic()
        worlds: list[WorldSample] = []
        runs: set[str] = set()
        parse_errors = 0
        async with self.session_factory() as session:
            heads = await session.execute(
                select(SnapshotHeadModel.game_run_id, SnapshotHeadModel.snapshot_json).where(
                    SnapshotHeadModel.server_revision > 0,
                ),
            )
            for game_run_id, snapshot_json in heads:
                runs.add(game_run_id)
                sample = parse_world_sample(snapshot_json)
                if sample is None:
                    parse_errors += 1
                else:
                    worlds.append(sample)
            profiles = await session.scalar(select(func.count()).select_from(ProfileModel))
            pets = await session.scalar(select(func.count()).select_from(PetModel))
            skills = await self._latest_skills(session)
        for _ in range(parse_errors):
            self.metrics.observe_aggregation_parse_error()
        self.metrics.publish_worlds(
            samples=worlds,
            worlds=len(worlds),
            runs=len(runs),
            profiles=int(profiles or 0),
            pets=int(pets or 0),
            skills=skills,
        )
        self.metrics.observe_aggregation_success(duration_seconds=time.monotonic() - started)

    async def _latest_skills(self, session: Any) -> list[list[dict[str, Any]]]:  # noqa: ANN401
        rows = await session.execute(
            select(
                AnalyticsProjectionModel.profile_id,
                AnalyticsProjectionModel.game_run_id,
                AnalyticsProjectionModel.through_history_sequence,
                AnalyticsProjectionModel.skills,
            ).order_by(
                AnalyticsProjectionModel.profile_id,
                AnalyticsProjectionModel.game_run_id,
                AnalyticsProjectionModel.through_history_sequence.desc(),
            ),
        )
        latest: dict[tuple[Any, str], list[dict[str, Any]]] = {}
        for profile_id, game_run_id, _sequence, skills in rows:
            key = (profile_id, game_run_id)
            if key not in latest and isinstance(skills, list):
                latest[key] = [skill for skill in skills if isinstance(skill, dict)]
        return list(latest.values())
