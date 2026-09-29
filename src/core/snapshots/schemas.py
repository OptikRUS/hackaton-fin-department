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

    @property
    def is_current_world(self) -> bool:
        return "worldFormatVersion" in self.document

    def predecessors(self) -> dict[str, dict[str, Any]]:
        entries = self.document.get("predecessors", [])
        if not isinstance(entries, list):
            raise InvalidSnapshotError
        runs: dict[str, dict[str, Any]] = {}
        for entry in entries:
            if (
                not isinstance(entry, dict)
                or not all(
                    isinstance(entry.get(key), str) and entry[key].strip()
                    for key in ("runId", "generation")
                )
                or type(entry.get("historySequence")) is not int
                or not 0 <= entry["historySequence"] <= 2**63 - 1
                or entry["runId"] == self.document["runId"]
                or entry["runId"] in runs
            ):
                raise InvalidSnapshotError
            runs[entry["runId"]] = entry
        return runs

    def validate_world_rewards(self) -> None:
        entries = self.document.get("parentRewards", [])
        if not isinstance(entries, list):
            raise InvalidSnapshotError
        reward_ids: set[str] = set()
        application_ids: set[str] = set()
        profiles: set[str] = set()
        for entry in entries:
            if not isinstance(entry, dict):
                raise InvalidSnapshotError
            reward, receipt = entry.get("reward"), entry.get("receipt")
            if not isinstance(reward, dict) or not isinstance(receipt, dict):
                raise InvalidSnapshotError
            if (
                not all(
                    isinstance(value, str) and value.strip()
                    for value in (
                        reward.get("rewardId"),
                        reward.get("profileId"),
                        receipt.get("applicationId"),
                        receipt.get("historyEntryId"),
                    )
                )
                or reward.get("gameRunId") != self.document["runId"]
                or receipt.get("rewardId") != reward["rewardId"]
                or type(receipt.get("historySequence")) is not int
                or not 1 <= receipt["historySequence"] <= 2**63 - 1
                or reward["rewardId"] in reward_ids
                or receipt["applicationId"] in application_ids
            ):
                raise InvalidSnapshotError
            reward_ids.add(reward["rewardId"])
            application_ids.add(receipt["applicationId"])
            profiles.add(reward["profileId"])
        if len(profiles) > 1:
            raise InvalidSnapshotError

    def validate_current_world(self) -> None:
        if (
            type(self.document.get("worldFormatVersion")) is not int
            or self.document["worldFormatVersion"] != 1
            or not self.document["runId"].strip()
            or not isinstance(self.document.get("state"), dict)
            or not isinstance(self.document.get("generation"), str)
            or not self.document["generation"].strip()
            or not 0 <= self.document["historySequence"] <= 2**63 - 1
        ):
            raise InvalidSnapshotError
        self.predecessors()
        self.validate_world_rewards()

    def validate_world_continuation(self, *, previous: SnapshotArchive) -> None:
        ancestors = self.predecessors()
        if previous.is_current_world:
            if any(
                ancestors.get(run_id) != entry for run_id, entry in previous.predecessors().items()
            ):
                raise SnapshotGameRunConflictError
        elif not previous.archived_runs().keys() <= ancestors.keys():
            raise SnapshotGameRunConflictError
        previous_run_id = previous.document["runId"]
        if previous_run_id == self.document["runId"]:
            return
        checkpoint = ancestors.get(previous_run_id)
        if (
            checkpoint is None
            or checkpoint["historySequence"] < previous.document["historySequence"]
        ):
            raise SnapshotGameRunConflictError

    def validate_continuation(self, *, previous: SnapshotArchive) -> None:
        if self.is_current_world:
            self.validate_world_continuation(previous=previous)
            return
        if previous.is_current_world:
            raise SnapshotGameRunConflictError
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
    payload_kind: str | None = None

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

        if self.payload_kind not in (None, "CURRENT_WORLD"):
            raise InvalidSnapshotRequestError
        archive = SnapshotArchive.from_json(snapshot_json=self.snapshot_json)
        version_key = (
            "worldFormatVersion" if self.payload_kind == "CURRENT_WORLD" else "formatVersion"
        )
        if any(
            type(archive.document.get(key)) is not expected_type
            or archive.document[key] != expected_value
            for key, expected_type, expected_value in (
                (version_key, int, self.snapshot_format_version),
                ("runId", str, self.game_run_id),
                ("historySequence", int, self.through_history_sequence),
                ("checksum", str, self.checksum),
            )
        ):
            raise InvalidSnapshotError
        if self.payload_kind == "CURRENT_WORLD":
            archive.validate_current_world()
        else:
            if archive.is_current_world:
                raise InvalidSnapshotError
            archive.archived_runs()

    def validate_continuation(self, *, previous: Snapshot) -> None:
        SnapshotArchive.from_json(snapshot_json=self.snapshot_json).validate_continuation(
            previous=SnapshotArchive.from_json(snapshot_json=previous.snapshot_json),
        )

    def request_digest(self) -> str:
        digest_fields = asdict(self)
        digest_fields["profile_id"] = str(self.profile_id)
        # Frozen legacy retries predate the discriminator; retain their exact digest.
        if self.payload_kind is None:
            digest_fields.pop("payload_kind")
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
