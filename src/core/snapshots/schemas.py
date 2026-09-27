import json
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Never
from uuid import UUID

from src.core.snapshots.exceptions import InvalidSnapshotError, InvalidSnapshotRequestError


@dataclass(frozen=True, slots=True, kw_only=True)
class UploadSnapshotParams:
    profile_id: UUID
    upload_id: str
    expected_server_revision: int | None
    game_run_id: str
    through_history_sequence: int
    current_content_fingerprint: str
    snapshot_format_version: int
    checksum: str
    snapshot_json: str
    schema_version: int = 1

    @staticmethod
    def _reject_non_json_constant(_: str) -> Never:
        raise ValueError

    def validate(self, *, idempotency_key: str) -> None:
        if idempotency_key != self.upload_id:
            raise InvalidSnapshotRequestError

        db_text_fields = (
            self.upload_id,
            self.game_run_id,
            self.current_content_fingerprint,
            self.snapshot_json,
        )
        if any("\x00" in value for value in db_text_fields):
            raise InvalidSnapshotRequestError
        try:
            upload_id_bytes = self.upload_id.encode("utf-8")
            for value in db_text_fields[1:]:
                value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise InvalidSnapshotRequestError from exc
        max_upload_id_bytes = 255
        if len(upload_id_bytes) > max_upload_id_bytes:
            raise InvalidSnapshotRequestError

        try:
            archive = json.loads(self.snapshot_json, parse_constant=self._reject_non_json_constant)
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
            raise InvalidSnapshotError from exc
        if not isinstance(archive, dict) or any(
            type(archive.get(key)) is not expected_type or archive[key] != expected_value
            for key, expected_type, expected_value in (
                ("formatVersion", int, self.snapshot_format_version),
                ("runId", str, self.game_run_id),
                ("historySequence", int, self.through_history_sequence),
                ("checksum", str, self.checksum),
            )
        ):
            raise InvalidSnapshotError

    def request_digest(self) -> str:
        digest_fields = asdict(self)
        digest_fields["profile_id"] = str(self.profile_id)
        return sha256(
            json.dumps(digest_fields, sort_keys=True, separators=(",", ":")).encode("utf-8"),
        ).hexdigest()


@dataclass(frozen=True, slots=True, kw_only=True)
class UploadSnapshotResult:
    upload_id: str
    game_run_id: str
    server_revision: int
    checksum: str
    created: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class Snapshot:
    profile_id: UUID
    game_run_id: str
    server_revision: int
    current_content_fingerprint: str
    snapshot_json: str
    schema_version: int = 1


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotHead:
    profile_id: UUID
    server_revision: int
    game_run_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotUploadReceipt:
    profile_id: UUID
    request_digest: str
    result: UploadSnapshotResult
