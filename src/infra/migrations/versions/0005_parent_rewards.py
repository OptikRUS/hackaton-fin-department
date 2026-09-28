from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "parent_rewards",
        sa.Column("reward_id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("game_run_id", sa.String(), nullable=False),
        sa.Column("sequence", sa.BigInteger(), nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("reward_type", sa.String(16), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=True),
        sa.Column("item_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("reward_id", name="pk_parent_rewards"),
        sa.ForeignKeyConstraint(["profile_id"], ["snapshot_heads.profile_id"]),
        sa.UniqueConstraint(
            "profile_id", "game_run_id", "sequence", name="uq_parent_rewards_sequence"
        ),
        sa.UniqueConstraint(
            "profile_id",
            "idempotency_key",
            name="uq_parent_rewards_request",
        ),
        sa.CheckConstraint("sequence > 0", name="ck_parent_rewards_positive_sequence"),
        sa.CheckConstraint(
            "(reward_type = 'COINS' AND amount > 0 AND item_id IS NULL) OR "
            "(reward_type = 'ACCESSORY' AND amount IS NULL AND item_id IS NOT NULL)",
            name="ck_parent_rewards_valid_payload",
        ),
    )
    op.create_table(
        "parent_reward_receipts",
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("game_run_id", sa.String(), nullable=False),
        sa.Column("reward_id", sa.Uuid(), nullable=False),
        sa.Column("history_entry_id", sa.String(), nullable=False),
        sa.Column("history_sequence", sa.BigInteger(), nullable=False),
        sa.Column("outcome", sa.String(20), nullable=False),
        sa.PrimaryKeyConstraint("application_id", name="pk_parent_reward_receipts"),
        sa.ForeignKeyConstraint(["reward_id"], ["parent_rewards.reward_id"]),
        sa.CheckConstraint(
            "history_sequence > 0", name="ck_parent_reward_receipts_positive_history_sequence"
        ),
        sa.CheckConstraint(
            "outcome IN ('APPLIED', 'ALREADY_OWNED')",
            name="ck_parent_reward_receipts_valid_outcome",
        ),
    )
    op.create_table(
        "parent_reward_ack_requests",
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("digest", sa.String(64), nullable=False),
        sa.PrimaryKeyConstraint(
            "profile_id", "idempotency_key", name="pk_parent_reward_ack_requests"
        ),
    )


def downgrade() -> None:
    op.drop_table("parent_reward_ack_requests")
    op.drop_table("parent_reward_receipts")
    op.drop_table("parent_rewards")
