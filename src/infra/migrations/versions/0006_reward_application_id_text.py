from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "parent_reward_receipts",
        "application_id",
        existing_type=sa.Uuid(),
        type_=sa.String(),
        postgresql_using="application_id::text",
    )


def downgrade() -> None:
    op.alter_column(
        "parent_reward_receipts",
        "application_id",
        existing_type=sa.String(),
        type_=sa.Uuid(),
        postgresql_using="application_id::uuid",
    )
