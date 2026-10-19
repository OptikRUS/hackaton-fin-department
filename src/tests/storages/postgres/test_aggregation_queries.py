import tracemalloc
from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from prometheus_client import CollectorRegistry
from sqlalchemy import delete, insert
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from src.infra.observability.aggregation import Aggregator
from src.infra.observability.business_metrics import BusinessMetrics
from src.infra.storages.postgres.models import AnalyticsProjectionModel, SnapshotHeadModel
from src.tests.helpers.worlds import legacy_archive_json, legacy_fact, world_snapshot_json


@pytest.fixture(autouse=True)
async def clean_projection_revisions(session: AsyncSession) -> AsyncIterator[None]:
    yield
    # Downgrade deliberately refuses to discard amended revisions.
    await session.execute(delete(AnalyticsProjectionModel))
    await session.commit()


async def _collect_peak(engine: AsyncEngine, metrics: BusinessMetrics) -> int:
    aggregator = Aggregator(
        metrics=metrics,
        interval_seconds=60,
        session_factory=async_sessionmaker(engine),
    )
    tracemalloc.start()
    try:
        await aggregator.collect_once()
        return tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()


async def test_old_projection_payloads_do_not_enter_application_memory(
    engine: AsyncEngine, session: AsyncSession
) -> None:
    profile_id = uuid4()
    old_facts = [
        legacy_fact(str(number), {"_type": "interaction", "name": "Old", "padding": "x" * 4096})
        for number in range(100)
    ]
    await session.execute(
        insert(AnalyticsProjectionModel),
        [
            {
                "profile_id": profile_id,
                "game_run_id": "run-1",
                "projection_version": 4,
                "evaluator_version": 1,
                "through_history_sequence": sequence,
                "facts": old_facts,
                "skills": [],
            }
            for sequence in range(32)
        ],
    )
    await session.execute(
        insert(AnalyticsProjectionModel).values(
            profile_id=profile_id,
            game_run_id="run-1",
            projection_version=4,
            evaluator_version=1,
            through_history_sequence=32,
            facts=[legacy_fact("latest", {"_type": "interaction", "name": "Latest"})],
            skills=[{"skillId": "FIN-01", "completedEpisodes": 3}],
        ),
    )
    await session.commit()
    metrics = BusinessMetrics(registry=CollectorRegistry())

    peak = await _collect_peak(engine, metrics)

    assert metrics.registry.get_sample_value("fin_interactions_stored", {"name": "Latest"}) == 1
    assert metrics.registry.get_sample_value("fin_interactions_stored", {"name": "Old"}) is None
    # Historical payloads exceed 12 MiB; only the tiny latest payload is needed.
    assert peak < 6 * 1024 * 1024, f"Aggregation allocated {peak / 1024**2:.1f} MiB"


async def test_world_histories_are_released_as_each_world_is_counted(
    engine: AsyncEngine, session: AsyncSession
) -> None:
    snapshot_json = legacy_archive_json(
        history=[
            {
                "facts": [
                    legacy_fact(
                        str(number),
                        {"_type": "interaction", "name": "BeginDay", "padding": "x" * 16384},
                    )
                    for number in range(16)
                ],
            }
        ],
    )
    await session.execute(
        insert(SnapshotHeadModel),
        [
            {
                "profile_id": uuid4(),
                "game_run_id": "run-1",
                "server_revision": 1,
                "snapshot_json": snapshot_json,
            }
            for _ in range(32)
        ],
    )
    await session.commit()
    metrics = BusinessMetrics(registry=CollectorRegistry())

    peak = await _collect_peak(engine, metrics)

    assert metrics.registry.get_sample_value("fin_worlds_total") == 32
    assert metrics.registry.get_sample_value("fin_interactions_stored", {"name": "BeginDay"}) == 512
    assert metrics.registry.get_sample_value("fin_pet_balance_sum") == 20480
    assert peak < 6 * 1024 * 1024, f"Aggregation allocated {peak / 1024**2:.1f} MiB"


async def test_latest_revision_is_selected_per_profile_and_run(
    engine: AsyncEngine, session: AsyncSession
) -> None:
    profile_id = uuid4()
    other_profile_id = uuid4()
    await session.execute(
        insert(AnalyticsProjectionModel),
        [
            {
                "profile_id": profile,
                "game_run_id": run,
                "projection_version": 4,
                "evaluator_version": 1,
                "through_history_sequence": sequence,
                "history_start_sequence": start,
                "revision": revision,
                "facts": [legacy_fact(name, {"_type": "interaction", "name": name})],
                "skills": [{"skillId": "FIN-01", "completedEpisodes": episodes}],
            }
            for profile, run, sequence, start, revision, name, episodes in [
                (profile_id, "run-1", 8, 0, 1, "Replaced", 100),
                (profile_id, "run-1", 8, 0, 2, "Amended", 4),
                (profile_id, "run-2", 1, 0, 1, "OtherRun", 2),
                (other_profile_id, "run-1", 2, 0, 1, "OtherProfile", 3),
            ]
        ],
    )
    await session.execute(
        insert(SnapshotHeadModel).values(
            profile_id=profile_id,
            game_run_id="run-1",
            server_revision=1,
            snapshot_json=world_snapshot_json(),
        ),
    )
    await session.commit()
    metrics = BusinessMetrics(registry=CollectorRegistry())

    await _collect_peak(engine, metrics)

    assert metrics.registry.get_sample_value("fin_skill_assessed_worlds_total") == 3
    assert (
        metrics.registry.get_sample_value(
            "fin_skill_episodes_avg", {"skill": "FIN-01", "counter": "completed_episodes"}
        )
        == 3
    )
    assert (
        metrics.registry.get_sample_value("fin_interactions_stored", {"name": "Replaced"}) is None
    )
    for name in ("Amended", "OtherRun", "OtherProfile"):
        assert metrics.registry.get_sample_value("fin_interactions_stored", {"name": name}) == 1


async def test_projection_pagination_counts_every_run_once(
    engine: AsyncEngine, session: AsyncSession
) -> None:
    profile_id = uuid4()
    await session.execute(
        insert(AnalyticsProjectionModel),
        [
            {
                "profile_id": profile_id,
                "game_run_id": f"run-{run}",
                "projection_version": 4,
                "evaluator_version": 1,
                "through_history_sequence": sequence,
                "facts": [legacy_fact("event", {"_type": "interaction", "name": name})],
                "skills": [{"skillId": "FIN-01", "completedEpisodes": 2}],
            }
            for run in range(23)
            for sequence, name in [(1, "Old"), (2, "Latest")]
        ],
    )
    await session.commit()
    metrics = BusinessMetrics(registry=CollectorRegistry())

    await _collect_peak(engine, metrics)

    assert metrics.registry.get_sample_value("fin_skill_assessed_worlds_total") == 23
    assert metrics.registry.get_sample_value("fin_interactions_stored", {"name": "Latest"}) == 23
    assert metrics.registry.get_sample_value("fin_interactions_stored", {"name": "Old"}) is None
