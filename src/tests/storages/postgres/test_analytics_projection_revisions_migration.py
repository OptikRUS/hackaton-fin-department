import asyncio
import json
from uuid import UUID

import pytest
from sqlalchemy import NullPool, text
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import create_async_engine

from src.config.settings import settings
from src.infra.migrations.commands import downgrade, migrate


def query(statement: str, params: dict[str, object] | None = None) -> list[RowMapping]:
    async def execute() -> list[RowMapping]:
        engine = create_async_engine(settings.POSTGRES.DSN.get_secret_value(), poolclass=NullPool)
        try:
            async with engine.begin() as connection:
                result = await connection.execute(text(statement), params or {})
                return list(result.mappings().all()) if result.returns_rows else []
        finally:
            await engine.dispose()

    return asyncio.run(execute())


@pytest.mark.usefixtures("clear_tables")
def test_projection_revisions_preserve_evidence_and_refuse_lossy_downgrade() -> None:
    dsn = settings.POSTGRES.DSN.get_secret_value()
    profile: dict[str, object] = {"profile_id": UUID(int=808)}
    original = [{"eventId": "original", "sequence": 9}]
    revised = [{"eventId": "revised", "sequence": 9}]
    skills = [{"skillId": "FIN-01", "observations": []}]
    downgrade("0007", dsn)
    try:
        query(
            "INSERT INTO analytics_projections "
            "(profile_id, game_run_id, projection_version, evaluator_version, "
            "through_history_sequence, history_start_sequence, facts, skills) VALUES "
            "(:profile_id, 'run-1', 4, 1, 10, 0, CAST(:facts AS jsonb), CAST(:skills AS jsonb))",
            {**profile, "facts": json.dumps(original), "skills": json.dumps(skills)},
        )
        migrate("heads", dsn)
        rows = query(
            "SELECT revision, facts, skills FROM analytics_projections "
            "WHERE profile_id=:profile_id",
            profile,
        )
        assert len(rows) == 1
        assert dict(rows[0]) == {"revision": 0, "facts": original, "skills": skills}

        query(
            "INSERT INTO analytics_projections "
            "(profile_id, game_run_id, projection_version, evaluator_version, "
            "through_history_sequence, history_start_sequence, revision, facts, skills) VALUES "
            "(:profile_id, 'run-1', 4, 1, 10, 0, 1, CAST(:facts AS jsonb), CAST(:skills AS jsonb))",
            {**profile, "facts": json.dumps(revised), "skills": json.dumps(skills)},
        )
        with pytest.raises(RuntimeError, match="Cannot downgrade analytics projection revisions"):
            downgrade("0007", dsn)
        rows = query(
            "SELECT revision, facts, skills FROM analytics_projections "
            "WHERE profile_id=:profile_id ORDER BY revision",
            profile,
        )
        assert [dict(row) for row in rows] == [
            {"revision": 0, "facts": original, "skills": skills},
            {"revision": 1, "facts": revised, "skills": skills},
        ]
        assert query("SELECT version_num FROM alembic_version")[0]["version_num"] == "0008"

        # Test-only removal makes the old schema representable, without asking
        # the downgrade itself to discard either accepted revision.
        query(
            "DELETE FROM analytics_projections WHERE profile_id=:profile_id AND revision=0", profile
        )
        downgrade("0007", dsn)
        row = query(
            "SELECT facts, skills FROM analytics_projections WHERE profile_id=:profile_id", profile
        )[0]
        assert dict(row) == {"facts": revised, "skills": skills}
        migrate("heads", dsn)
        assert (
            query(
                "SELECT revision FROM analytics_projections WHERE profile_id=:profile_id", profile
            )[0]["revision"]
            == 0
        )
    finally:
        query("DELETE FROM analytics_projections WHERE profile_id=:profile_id", profile)
        migrate("heads", dsn)
