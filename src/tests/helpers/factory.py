import json
from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from src.core.pets.schemas import CreatePetParams, Pet
from src.core.snapshots.schemas import (
    Snapshot,
    SnapshotHead,
    SnapshotUploadReceipt,
    UploadSnapshotParams,
    UploadSnapshotResult,
)


class PetsFactory:
    @classmethod
    def create_pet_params(cls, *, pet_id: UUID, name: str, temper: str) -> CreatePetParams:
        return CreatePetParams(id=pet_id, name=name, temper=temper)

    @classmethod
    def create_pet(cls, *, pet_id: UUID, name: str, temper: str, balance: Decimal) -> Pet:
        return Pet(id=pet_id, name=name, temper=temper, balance=balance)


class SnapshotsFactory:
    @classmethod
    def archive_json(
        cls,
        *,
        format_version: int = 4,
        run_id: str = "run-1",
        history_sequence: int = 0,
        checksum: str = "a" * 64,
    ) -> str:
        return json.dumps(
            {
                "formatVersion": format_version,
                "runId": run_id,
                "historySequence": history_sequence,
                "checksum": checksum,
            },
            separators=(",", ":"),
        )

    @classmethod
    def upload_params(
        cls,
        *,
        profile_id: UUID,
        upload_id: str = "upload-1",
        expected_server_revision: int | None = None,
        game_run_id: str = "run-1",
        snapshot_json: str | None = None,
    ) -> UploadSnapshotParams:
        return UploadSnapshotParams(
            profile_id=profile_id,
            upload_id=upload_id,
            expected_server_revision=expected_server_revision,
            game_run_id=game_run_id,
            through_history_sequence=0,
            current_content_fingerprint="catalog-v1",
            snapshot_format_version=4,
            checksum="a" * 64,
            snapshot_json=snapshot_json
            if snapshot_json is not None
            else cls.archive_json(
                run_id=game_run_id,
            ),
        )

    @staticmethod
    def upload_result(
        *,
        upload_id: str = "upload-1",
        game_run_id: str = "run-1",
        server_revision: int = 1,
        checksum: str = "a" * 64,
        created: bool = True,
    ) -> UploadSnapshotResult:
        return UploadSnapshotResult(
            upload_id=upload_id,
            game_run_id=game_run_id,
            server_revision=server_revision,
            checksum=checksum,
            created=created,
        )

    @classmethod
    def snapshot(
        cls,
        *,
        profile_id: UUID,
        game_run_id: str = "run-1",
        server_revision: int = 1,
        current_content_fingerprint: str = "catalog-v1",
        snapshot_json: str | None = None,
    ) -> Snapshot:
        return Snapshot(
            profile_id=profile_id,
            game_run_id=game_run_id,
            server_revision=server_revision,
            current_content_fingerprint=current_content_fingerprint,
            snapshot_json=snapshot_json if snapshot_json is not None else cls.archive_json(),
        )

    @staticmethod
    def head(
        *,
        profile_id: UUID,
        server_revision: int = 0,
        game_run_id: str = "",
    ) -> SnapshotHead:
        return SnapshotHead(
            profile_id=profile_id,
            server_revision=server_revision,
            game_run_id=game_run_id,
        )

    @classmethod
    def receipt(
        cls,
        *,
        profile_id: UUID,
        request_digest: str = "a" * 64,
        result: UploadSnapshotResult | None = None,
    ) -> SnapshotUploadReceipt:
        return SnapshotUploadReceipt(
            profile_id=profile_id,
            request_digest=request_digest,
            result=result if result is not None else cls.upload_result(),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class FactoryHelper:
    pets: PetsFactory = field(default_factory=PetsFactory)
    snapshots: SnapshotsFactory = field(default_factory=SnapshotsFactory)
