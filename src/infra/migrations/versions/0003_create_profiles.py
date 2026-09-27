from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "profiles",
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.String(), nullable=False),
        sa.Column("pet_json", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("profile_id", name=op.f("pk_profiles")),
        sa.UniqueConstraint("device_id", name=op.f("uq_profiles_device_id")),
    )
    op.create_table(
        "profile_registrations",
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("request_digest", sa.String(length=64), nullable=False),
        sa.Column("device_id", sa.String(), nullable=False),
        sa.Column("created", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["profiles.profile_id"],
            name=op.f("fk_profile_registrations_profile_id_profiles"),
        ),
        sa.PrimaryKeyConstraint(
            "profile_id",
            "idempotency_key",
            name=op.f("pk_profile_registrations"),
        ),
    )


def downgrade() -> None:
    op.drop_table("profile_registrations")
    op.drop_table("profiles")
