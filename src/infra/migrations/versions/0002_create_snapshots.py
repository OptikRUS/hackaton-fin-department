from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "snapshot_heads",
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("server_revision", sa.BigInteger(), nullable=False),
        sa.Column("game_run_id", sa.String(), nullable=False),
        sa.Column("current_content_fingerprint", sa.String(), nullable=False),
        sa.Column("snapshot_json", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("profile_id", name=op.f("pk_snapshot_heads")),
    )
    op.create_table(
        "snapshot_uploads",
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("upload_id", sa.String(), nullable=False),
        sa.Column("request_digest", sa.String(length=64), nullable=False),
        sa.Column("game_run_id", sa.String(), nullable=False),
        sa.Column("server_revision", sa.BigInteger(), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("created", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("profile_id", "upload_id", name=op.f("pk_snapshot_uploads")),
    )


def downgrade() -> None:
    op.drop_table("snapshot_uploads")
    op.drop_table("snapshot_heads")
