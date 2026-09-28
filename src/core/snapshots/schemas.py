import json
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Any, Never, Self
from uuid import UUID

from src.core.snapshots.exceptions import (
    InvalidSnapshotError,
    InvalidSnapshotRequestError,
    SnapshotGameRunConflictError,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class SnapshotArchive:
    document: dict[str, Any]

    @staticmethod
    def _reject_non_json_constant(_: str) -> Never:
        raise ValueError

    @classmethod
    def from_json(cls, *, snapshot_json: str) -> Self:
        try:
            document = json.loads(snapshot_json, parse_constant=cls._reject_non_json_constant)
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
            raise InvalidSnapshotError from exc
        if not isinstance(document, dict):
            raise InvalidSnapshotError
        return cls(document=document)

    def archived_runs(self) -> dict[str, dict[str, Any]]:
        archive_format_version = 5
        entries = self.document.get("archivedRuns", [])
        if not isinstance(entries, list) or (
            entries and self.document.get("formatVersion") != archive_format_version
        ):
            raise InvalidSnapshotError
        runs: dict[str, dict[str, Any]] = {}
        requests: set[str] = set()
        successors: set[str] = set()
        for entry in entries:
            if not isinstance(entry, dict) or not isinstance(entry.get("snapshot"), dict):
                raise InvalidSnapshotError
            snapshot = entry["snapshot"]
            run_id = snapshot.get("runId")
            next_run_id = entry.get("nextRunId")
            request_id = entry.get("restartRequestId")
            if (
                not all(
                    isinstance(value, str) and value.strip()
                    for value in (
                        run_id,
                        next_run_id,
                        request_id,
                    )
                )
                or run_id == self.document.get("runId")
                or run_id == next_run_id
                or run_id in runs
                or request_id in requests
                or next_run_id in successors
                or snapshot.get("archivedRuns", []) != []
                or type(snapshot.get("formatVersion")) is not int
                or not 1 <= snapshot["formatVersion"] <= archive_format_version
                or type(snapshot.get("historySequence")) is not int
                or snapshot["historySequence"] < 0
                or not isinstance(snapshot.get("history"), list)
                or not isinstance(snapshot.get("checksum"), str)
            ):
                raise InvalidSnapshotError
            runs[run_id] = entry
            requests.add(request_id)
            successors.add(next_run_id)
        return runs

    def for_run(self, *, game_run_id: str) -> dict[str, Any] | None:
        if self.document.get("runId") == game_run_id:
            return self.document
        entry = self.archived_runs().get(game_run_id)
        return entry["snapshot"] if entry is not None else None

    def validate_continuation(self, *, previous: SnapshotArchive) -> None:
        archives = self.archived_runs()
        if any(archives.get(run_id) != entry for run_id, entry in previous.archived_runs().items()):
            raise SnapshotGameRunConflictError
        previous_run_id = previous.document["runId"]
        if previous_run_id == self.document["runId"]:
            return
        entry = archives.get(previous_run_id)
        if entry is None:
            raise SnapshotGameRunConflictError
        saved_history = previous.document.get("history", [])
        archived = entry["snapshot"]
        if (
            archived["historySequence"] < previous.document["historySequence"]
            or archived["history"][: len(saved_history)] != saved_history
        ):
            raise SnapshotGameRunConflictError
        visited: set[str] = set()
        run_id = previous_run_id
        while run_id != self.document["runId"]:
            if run_id in visited or run_id not in archives:
                raise SnapshotGameRunConflictError
            visited.add(run_id)
            run_id = archives[run_id]["nextRunId"]


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

        archive = SnapshotArchive.from_json(snapshot_json=self.snapshot_json)
        if any(
            type(archive.document.get(key)) is not expected_type
            or archive.document[key] != expected_value
            for key, expected_type, expected_value in (
                ("formatVersion", int, self.snapshot_format_version),
                ("runId", str, self.game_run_id),
                ("historySequence", int, self.through_history_sequence),
                ("checksum", str, self.checksum),
            )
        ):
            raise InvalidSnapshotError
        archive.archived_runs()

    def validate_continuation(self, *, previous: Snapshot) -> None:
        SnapshotArchive.from_json(snapshot_json=self.snapshot_json).validate_continuation(
            previous=SnapshotArchive.from_json(snapshot_json=previous.snapshot_json),
        )

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
