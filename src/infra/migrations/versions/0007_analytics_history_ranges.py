import json
from collections.abc import Sequence
from hashlib import sha256

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("analytics_original_facts", sa.Column("sequence", sa.BigInteger(), nullable=True))
    op.add_column(
        "analytics_projections",
        sa.Column("history_start_sequence", sa.BigInteger(), nullable=False, server_default="0"),
    )
    op.drop_constraint("pk_analytics_projections", "analytics_projections", type_="primary")
    op.create_primary_key(
        "pk_analytics_projections",
        "analytics_projections",
        [
            "profile_id",
            "game_run_id",
            "projection_version",
            "evaluator_version",
            "through_history_sequence",
            "history_start_sequence",
        ],
    )
    op.create_check_constraint(
        "valid_history_range",
        "analytics_projections",
        "history_start_sequence >= 0 AND history_start_sequence <= through_history_sequence",
    )
    # Legacy digests stay untouched. Recover only sequences whose full stored
    # fact matches its immutable digest; missing/ambiguous evidence remains NULL.
    connection = op.get_bind()
    candidates: dict[tuple[object, str, str, str], set[int]] = {}
    for row in connection.execute(
        sa.text("SELECT profile_id, game_run_id, facts FROM analytics_projections")
    ).mappings():
        for fact in row["facts"]:
            if not isinstance(fact, dict):
                continue
            event_id, sequence = fact.get("eventId"), fact.get("sequence")
            if (
                not isinstance(event_id, str)
                or event_id.startswith("derived:")
                or type(sequence) is not int
                or sequence < 0
                or fact.get("gameRunId") != row["game_run_id"]
            ):
                continue
            digest = sha256(
                json.dumps(
                    fact, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
                ).encode("utf-8")
            ).hexdigest()
            key = (row["profile_id"], row["game_run_id"], event_id, digest)
            candidates.setdefault(key, set()).add(sequence)
    for (profile_id, run_id, event_id, digest), sequences in candidates.items():
        if len(sequences) == 1:
            connection.execute(
                sa.text(
                    "UPDATE analytics_original_facts SET sequence = :sequence "
                    "WHERE profile_id = :profile_id AND game_run_id = :run_id "
                    "AND event_id = :event_id AND fact_digest = :digest"
                ),
                {
                    "sequence": next(iter(sequences)),
                    "profile_id": profile_id,
                    "run_id": run_id,
                    "event_id": event_id,
                    "digest": digest,
                },
            )


def downgrade() -> None:
    # An old schema cannot represent multiple starts at one end. Refuse a
    # downgrade containing new ranges rather than erase accepted evidence.
    partial = op.get_bind().scalar(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM analytics_projections WHERE history_start_sequence <> 0)"
        )
    )
    if partial:
        message = "Cannot downgrade analytics history ranges while partial projections exist"
        raise RuntimeError(message)
    op.drop_constraint("valid_history_range", "analytics_projections", type_="check")
    op.drop_constraint("pk_analytics_projections", "analytics_projections", type_="primary")
    op.create_primary_key(
        "pk_analytics_projections",
        "analytics_projections",
        [
            "profile_id",
            "game_run_id",
            "projection_version",
            "evaluator_version",
            "through_history_sequence",
        ],
    )
    op.drop_column("analytics_projections", "history_start_sequence")
    op.drop_column("analytics_original_facts", "sequence")
