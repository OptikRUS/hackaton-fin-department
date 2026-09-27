from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import Field

from src.core.snapshots.schemas import (
    Snapshot,
    UploadSnapshotParams,
    UploadSnapshotResult,
)
from src.infra.api.boundary import BoundaryModel


class SnapshotUploadRequest(BoundaryModel):
    upload_id: Annotated[str, Field(min_length=1, max_length=255)]
    expected_server_revision: (
        Annotated[int, Field(ge=1, json_schema_extra={"format": "int64"})] | None
    )
    game_run_id: Annotated[str, Field(min_length=1)]
    through_history_sequence: Annotated[int, Field(ge=0, json_schema_extra={"format": "int64"})]
    current_content_fingerprint: Annotated[str, Field(min_length=1)]
    snapshot_format_version: Annotated[int, Field(ge=1, le=4)]
    checksum: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    snapshot_json: Annotated[str, Field(min_length=1)]
    schema_version: Literal[1] = 1

    def to_domain(self, *, profile_id: UUID) -> UploadSnapshotParams:
        return UploadSnapshotParams(
            profile_id=profile_id,
            upload_id=self.upload_id,
            expected_server_revision=self.expected_server_revision,
            game_run_id=self.game_run_id,
            through_history_sequence=self.through_history_sequence,
            current_content_fingerprint=self.current_content_fingerprint,
            snapshot_format_version=self.snapshot_format_version,
            checksum=self.checksum,
            snapshot_json=self.snapshot_json,
            schema_version=self.schema_version,
        )


class SnapshotUploadResponse(BoundaryModel):
    upload_id: Annotated[str, Field(min_length=1, max_length=255)]
    game_run_id: Annotated[str, Field(min_length=1)]
    server_revision: Annotated[int, Field(ge=1, json_schema_extra={"format": "int64"})]
    checksum: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]

    @classmethod
    def from_domain(cls, *, result: UploadSnapshotResult) -> Self:
        return cls(
            upload_id=result.upload_id,
            game_run_id=result.game_run_id,
            server_revision=result.server_revision,
            checksum=result.checksum,
        )


class SnapshotDownloadResponse(BoundaryModel):
    game_run_id: Annotated[str, Field(min_length=1)]
    server_revision: Annotated[int, Field(ge=1, json_schema_extra={"format": "int64"})]
    current_content_fingerprint: Annotated[str, Field(min_length=1)]
    snapshot_json: Annotated[str, Field(min_length=1)]
    schema_version: Literal[1] = 1

    @classmethod
    def from_domain(cls, *, snapshot: Snapshot) -> Self:
        return cls(
            game_run_id=snapshot.game_run_id,
            server_revision=snapshot.server_revision,
            current_content_fingerprint=snapshot.current_content_fingerprint,
            snapshot_json=snapshot.snapshot_json,
            schema_version=1,
        )


class SnapshotError(BoundaryModel):
    code: str
    message: str | None = None
    request_id: str | None = None
