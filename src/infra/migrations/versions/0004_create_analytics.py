from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analytics_heads",
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("game_run_id", sa.String(), nullable=False),
        sa.Column("through_history_sequence", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("profile_id", "game_run_id", name=op.f("pk_analytics_heads")),
    )
    op.create_table(
        "analytics_batches",
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.String(length=255), nullable=False),
        sa.Column("request_digest", sa.String(length=64), nullable=False),
        sa.Column("game_run_id", sa.String(), nullable=False),
        sa.Column("accepted_through_history_sequence", sa.BigInteger(), nullable=False),
        sa.Column("accepted_event_ids", JSONB(), nullable=False),
        sa.Column("created", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("profile_id", "batch_id", name=op.f("pk_analytics_batches")),
    )
    op.create_table(
        "analytics_original_facts",
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("game_run_id", sa.String(), nullable=False),
        sa.Column("event_id", sa.String(), nullable=False),
        sa.Column("fact_digest", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint(
            "profile_id",
            "game_run_id",
            "event_id",
            name=op.f("pk_analytics_original_facts"),
        ),
    )
    op.create_table(
        "analytics_projections",
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("game_run_id", sa.String(), nullable=False),
        sa.Column("projection_version", sa.Integer(), nullable=False),
        sa.Column("evaluator_version", sa.Integer(), nullable=False),
        sa.Column("through_history_sequence", sa.BigInteger(), nullable=False),
        sa.Column("facts", JSONB(), nullable=False),
        sa.Column("skills", JSONB(), nullable=False),
        sa.PrimaryKeyConstraint(
            "profile_id",
            "game_run_id",
            "projection_version",
            "evaluator_version",
            "through_history_sequence",
            name=op.f("pk_analytics_projections"),
        ),
    )
    op.create_table(
        "skill_assessments",
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("game_run_id", sa.String(), nullable=False),
        sa.Column("policy_version", sa.String(), nullable=False),
        sa.Column("based_on_history_sequence", sa.BigInteger(), nullable=False),
        sa.Column("skills", JSONB(), nullable=False),
        sa.PrimaryKeyConstraint(
            "profile_id",
            "game_run_id",
            "policy_version",
            name=op.f("pk_skill_assessments"),
        ),
    )
    op.create_index(
        "ix_skill_assessments_latest",
        "skill_assessments",
        ["profile_id", "game_run_id", "based_on_history_sequence"],
    )


def downgrade() -> None:
    op.drop_index("ix_skill_assessments_latest", table_name="skill_assessments")
    op.drop_table("skill_assessments")
    op.drop_table("analytics_projections")
    op.drop_table("analytics_original_facts")
    op.drop_table("analytics_batches")
    op.drop_table("analytics_heads")
