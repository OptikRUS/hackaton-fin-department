from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CANONICAL_KEY = [
    "profile_id",
    "game_run_id",
    "projection_version",
    "evaluator_version",
    "through_history_sequence",
    "history_start_sequence",
]


def upgrade() -> None:
    # Existing payloads stay intact as revision zero; later accepted uploads
    # receive a distinct revision under their profile/run analytics head lock.
    op.add_column(
        "analytics_projections",
        sa.Column("revision", sa.BigInteger(), nullable=False, server_default="0"),
    )
    op.drop_constraint("pk_analytics_projections", "analytics_projections", type_="primary")
    op.create_primary_key(
        "pk_analytics_projections", "analytics_projections", [*_CANONICAL_KEY, "revision"]
    )


def downgrade() -> None:
    # Keep the check and schema change under one lock, so another upload cannot
    # introduce an unrepresentable revision after the check.
    op.execute("LOCK TABLE analytics_projections IN ACCESS EXCLUSIVE MODE")
    duplicate_ranges = op.get_bind().scalar(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM analytics_projections "
            "GROUP BY profile_id, game_run_id, projection_version, evaluator_version, "
            "through_history_sequence, history_start_sequence HAVING COUNT(*) > 1)"
        )
    )
    if duplicate_ranges:
        message = "Cannot downgrade analytics projection revisions while duplicate ranges exist"
        raise RuntimeError(message)
    op.drop_constraint("pk_analytics_projections", "analytics_projections", type_="primary")
    op.create_primary_key("pk_analytics_projections", "analytics_projections", _CANONICAL_KEY)
    op.drop_column("analytics_projections", "revision")
