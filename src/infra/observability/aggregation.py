import asyncio
import time
from collections.abc import AsyncGenerator, Callable
from contextlib import AbstractAsyncContextManager, aclosing, suppress
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Row, Select, and_, func, select, tuple_
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.sql import ColumnElement

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

_PAGE_SIZE = 8


async def _paged_rows(
    session: Any,  # noqa: ANN401
    statement: Select[Any],
    keys: tuple[InstrumentedAttribute[Any] | ColumnElement[Any], ...],
) -> AsyncGenerator[Row[Any]]:
    after: tuple[Any, ...] | None = None
    while True:
        page = statement.order_by(*keys).limit(_PAGE_SIZE)
        if after is not None:
            page = page.where(tuple_(*keys) > after)
        # asyncpg prefetches at least 50 rows even with yield_per=1. SQL LIMIT
        # bounds that buffer too; keyset pagination avoids increasingly costly OFFSET.
        rows = await session.stream(page.execution_options(yield_per=1))
        count = 0
        try:
            async for row in rows:
                count += 1
                after = tuple(row[: len(keys)])
                yield row
        finally:
            await rows.close()
        if count < _PAGE_SIZE:
            return


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
            profiles = await session.scalar(select(func.count()).select_from(ProfileModel))
            pets = await session.scalar(select(func.count()).select_from(PetModel))
            skills, projected_keys = await self._latest_projections(session, stored)
            heads = _paged_rows(
                session,
                select(
                    SnapshotHeadModel.profile_id,
                    SnapshotHeadModel.game_run_id,
                    SnapshotHeadModel.snapshot_json,
                ).where(SnapshotHeadModel.server_revision > 0),
                (SnapshotHeadModel.profile_id,),
            )
            async with aclosing(heads):
                async for profile_id, game_run_id, snapshot_json in heads:
                    runs.add(game_run_id)
                    sample = parse_world_sample(snapshot_json)
                    if sample is None:
                        parse_errors += 1
                        continue
                    if (profile_id, game_run_id) not in projected_keys:
                        for fact in sample.facts:
                            stored.add_fact(fact)
                    # Retain only the small world summary, not its complete event history.
                    sample.facts = ()
                    worlds.append(sample)
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
        stored: StoredCounts,
    ) -> tuple[list[list[dict[str, Any]]], set[tuple[Any, str]]]:
        model = AnalyticsProjectionModel
        # Sort only primary keys; old JSON payloads never leave PostgreSQL.
        keys = tuple(model.__table__.primary_key)
        latest = (
            select(*keys)
            .where(
                func.jsonb_typeof(model.skills) == "array",
                func.jsonb_typeof(model.facts) == "array",
            )
            .distinct(model.profile_id, model.game_run_id)
            .order_by(
                model.profile_id,
                model.game_run_id,
                model.through_history_sequence.desc(),
                model.revision.desc(),
                model.history_start_sequence.desc(),
                model.projection_version.desc(),
                model.evaluator_version.desc(),
            )
            .subquery()
        )
        rows = _paged_rows(
            session,
            select(
                model.profile_id,
                model.game_run_id,
                model.through_history_sequence,
                model.facts,
                model.skills,
            ).join(latest, and_(*(column == latest.c[column.name] for column in keys))),
            (latest.c.profile_id, latest.c.game_run_id),
        )
        skills_list: list[list[dict[str, Any]]] = []
        projected_keys: set[tuple[Any, str]] = set()
        async with aclosing(rows):
            async for profile_id, game_run_id, _sequence, facts, skills in rows:
                projected_keys.add((profile_id, game_run_id))
                skills_list.append([skill for skill in skills if isinstance(skill, dict)])
                for fact in facts:
                    if isinstance(fact, dict):
                        stored.add_fact(fact)
        return skills_list, projected_keys
