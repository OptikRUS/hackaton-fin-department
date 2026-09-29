import asyncio
import time
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager, suppress
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select

from src.infra.observability.business_metrics import (
    BusinessMetrics,
    StoredCounts,
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
        stored = StoredCounts()
        async with self.session_factory() as session:
            heads = await session.execute(
                select(
                    SnapshotHeadModel.profile_id,
                    SnapshotHeadModel.game_run_id,
                    SnapshotHeadModel.snapshot_json,
                ).where(SnapshotHeadModel.server_revision > 0),
            )
            head_rows = [
                (profile_id, game_run_id, snapshot_json)
                for profile_id, game_run_id, snapshot_json in heads
            ]
            profiles = await session.scalar(select(func.count()).select_from(ProfileModel))
            pets = await session.scalar(select(func.count()).select_from(PetModel))
            skills, projected_facts, projected_keys = await self._latest_projections(session)
        for profile_id, game_run_id, snapshot_json in head_rows:
            runs.add(game_run_id)
            sample = parse_world_sample(snapshot_json)
            if sample is None:
                parse_errors += 1
            else:
                worlds.append(sample)
                if (profile_id, game_run_id) not in projected_keys:
                    for fact in sample.facts:
                        stored.add_fact(fact)
        for fact in projected_facts:
            stored.add_fact(fact)
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
        self.metrics.publish_stored(stored)
        self.metrics.observe_aggregation_success(duration_seconds=time.monotonic() - started)

    async def _latest_projections(
        self,
        session: Any,  # noqa: ANN401
    ) -> tuple[list[list[dict[str, Any]]], list[dict[str, Any]], set[tuple[Any, str]]]:
        rows = await session.execute(
            select(
                AnalyticsProjectionModel.profile_id,
                AnalyticsProjectionModel.game_run_id,
                AnalyticsProjectionModel.through_history_sequence,
                AnalyticsProjectionModel.facts,
                AnalyticsProjectionModel.skills,
            ).order_by(
                AnalyticsProjectionModel.profile_id,
                AnalyticsProjectionModel.game_run_id,
                AnalyticsProjectionModel.through_history_sequence.desc(),
            ),
        )
        latest: dict[tuple[Any, str], tuple[list[dict[str, Any]], list[dict[str, Any]]]] = {}
        for profile_id, game_run_id, _sequence, facts, skills in rows:
            key = (profile_id, game_run_id)
            if key in latest or not isinstance(skills, list) or not isinstance(facts, list):
                continue
            latest[key] = (
                [skill for skill in skills if isinstance(skill, dict)],
                [fact for fact in facts if isinstance(fact, dict)],
            )
        skills_list = [skills for skills, _facts in latest.values()]
        facts_list = [fact for _skills, facts in latest.values() for fact in facts]
        return skills_list, facts_list, set(latest)
