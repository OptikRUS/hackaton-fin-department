import asyncio
import json
from uuid import UUID

import pytest
from sqlalchemy import NullPool, text
from sqlalchemy.ext.asyncio import create_async_engine

from src.config.settings import settings
from src.core.analytics.schemas import AnalyticsUploadParams
from src.infra.migrations.commands import downgrade, migrate


@pytest.mark.usefixtures("clear_tables")
def test_upgrade_preserves_legacy_ack_and_recovers_only_verified_fact_sequences() -> None:
    dsn = settings.POSTGRES.DSN.get_secret_value()
    profile_id = UUID(int=707)
    fact = {
        "eventId": "known",
        "gameRunId": "run-1",
        "episodeId": "ep",
        "actionId": "tap",
        "sequence": 899,
        "detail": {"_type": "interaction", "name": "tap"},
    }
    changed = {**fact, "eventId": "changed", "sequence": 900}
    downgrade("0006", dsn)

    async def seed_legacy() -> None:
        engine = create_async_engine(dsn, poolclass=NullPool)
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO analytics_original_facts "
                    "(profile_id, game_run_id, event_id, fact_digest) "
                    "VALUES (:profile_id, 'run-1', :event_id, :digest)"
                ),
                [
                    {
                        "profile_id": profile_id,
                        "event_id": "known",
                        "digest": AnalyticsUploadParams.digest_value(fact),
                    },
                    {"profile_id": profile_id, "event_id": "unknown", "digest": "a" * 64},
                    {"profile_id": profile_id, "event_id": "changed", "digest": "b" * 64},
                ],
            )
            await connection.execute(
                text(
                    "INSERT INTO analytics_projections "
                    "(profile_id, game_run_id, projection_version, evaluator_version, "
                    "through_history_sequence, facts, skills) VALUES "
                    "(:profile_id, 'run-1', 4, 1, 900, CAST(:facts AS jsonb), '[]'::jsonb)"
                ),
                {"profile_id": profile_id, "facts": json.dumps([fact, changed])},
            )
            await connection.execute(
                text(
                    "INSERT INTO analytics_batches "
                    "(profile_id, batch_id, request_digest, game_run_id, "
                    "accepted_through_history_sequence, accepted_event_ids, created) "
                    "VALUES "
                    "(:profile_id, 'frozen', :digest, 'run-1', 900, '[\"known\"]'::jsonb, true)"
                ),
                {"profile_id": profile_id, "digest": "c" * 64},
            )
        await engine.dispose()

    asyncio.run(seed_legacy())
    migrate("heads", dsn)

    async def verify_and_clean() -> None:
        engine = create_async_engine(dsn, poolclass=NullPool)
        async with engine.begin() as connection:
            rows = (
                (
                    await connection.execute(
                        text(
                            "SELECT event_id, sequence FROM analytics_original_facts "
                            "WHERE profile_id=:profile_id"
                        ),
                        {"profile_id": profile_id},
                    )
                )
                .tuples()
                .all()
            )
            assert dict(rows) == {"known": 899, "unknown": None, "changed": None}
            row = (
                await connection.execute(
                    text(
                        "SELECT history_start_sequence, facts FROM analytics_projections "
                        "WHERE profile_id=:profile_id"
                    ),
                    {"profile_id": profile_id},
                )
            ).one()
            assert row.history_start_sequence == 0
            assert row.facts == [fact, changed]
            ack = (
                await connection.execute(
                    text(
                        "SELECT request_digest, accepted_event_ids, "
                        "accepted_through_history_sequence "
                        "FROM analytics_batches WHERE profile_id=:profile_id"
                    ),
                    {"profile_id": profile_id},
                )
            ).one()
            assert ack.request_digest == "c" * 64
            assert ack.accepted_event_ids == ["known"]
            assert ack.accepted_through_history_sequence == 900
            for statement in (
                "DELETE FROM analytics_projections WHERE profile_id=:profile_id",
                "DELETE FROM analytics_original_facts WHERE profile_id=:profile_id",
                "DELETE FROM analytics_batches WHERE profile_id=:profile_id",
            ):
                await connection.execute(text(statement), {"profile_id": profile_id})
        await engine.dispose()

    asyncio.run(verify_and_clean())
