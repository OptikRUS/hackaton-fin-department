from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("temper", sa.String(), nullable=False),
        sa.Column("balance", sa.Numeric(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pets")),
    )


def downgrade() -> None:
    op.drop_table("pets")
