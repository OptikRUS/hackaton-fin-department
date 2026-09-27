from decimal import Decimal
from typing import Self
from uuid import UUID

from sqlalchemy import BigInteger, Boolean, MetaData, Numeric, String, Text, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from src.core.pets.schemas import Pet
from src.core.snapshots.schemas import (
    Snapshot,
    SnapshotHead,
    SnapshotUploadReceipt,
    UploadSnapshotResult,
)


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        },
    )


class PetModel(Base):
    __tablename__ = "pets"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(), nullable=False)
    temper: Mapped[str] = mapped_column(String(), nullable=False)
    balance: Mapped[Decimal] = mapped_column(Numeric, nullable=False)

    def to_domain(self) -> Pet:
        return Pet(
            id=self.id,
            name=self.name,
            temper=self.temper,
            balance=self.balance,
        )

    @classmethod
    def from_domain(cls, *, pet: Pet) -> Self:
        return cls(
            id=pet.id,
            name=pet.name,
            temper=pet.temper,
            balance=pet.balance,
        )


class SnapshotHeadModel(Base):
    __tablename__ = "snapshot_heads"

    profile_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    server_revision: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    game_run_id: Mapped[str] = mapped_column(String, nullable=False, default="")
    current_content_fingerprint: Mapped[str] = mapped_column(String, nullable=False, default="")
    snapshot_json: Mapped[str] = mapped_column(Text, nullable=False, default="")

    def to_head(self) -> SnapshotHead:
        return SnapshotHead(
            profile_id=self.profile_id,
            server_revision=self.server_revision,
            game_run_id=self.game_run_id,
        )

    def to_domain(self) -> Snapshot:
        return Snapshot(
            profile_id=self.profile_id,
            game_run_id=self.game_run_id,
            server_revision=self.server_revision,
            current_content_fingerprint=self.current_content_fingerprint,
            snapshot_json=self.snapshot_json,
        )

    @classmethod
    def from_domain(cls, *, snapshot: Snapshot) -> Self:
        return cls(
            profile_id=snapshot.profile_id,
            server_revision=snapshot.server_revision,
            game_run_id=snapshot.game_run_id,
            current_content_fingerprint=snapshot.current_content_fingerprint,
            snapshot_json=snapshot.snapshot_json,
        )


class SnapshotUploadModel(Base):
    __tablename__ = "snapshot_uploads"

    profile_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    upload_id: Mapped[str] = mapped_column(String, primary_key=True)
    request_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    game_run_id: Mapped[str] = mapped_column(String, nullable=False)
    server_revision: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    created: Mapped[bool] = mapped_column(Boolean, nullable=False)

    def to_domain(self) -> SnapshotUploadReceipt:
        return SnapshotUploadReceipt(
            profile_id=self.profile_id,
            request_digest=self.request_digest,
            result=self.to_result(),
        )

    def to_result(self) -> UploadSnapshotResult:
        return UploadSnapshotResult(
            upload_id=self.upload_id,
            game_run_id=self.game_run_id,
            server_revision=self.server_revision,
            checksum=self.checksum,
            created=self.created,
        )

    @classmethod
    def from_domain(cls, *, upload: SnapshotUploadReceipt) -> Self:
        return cls(
            profile_id=upload.profile_id,
            upload_id=upload.result.upload_id,
            request_digest=upload.request_digest,
            game_run_id=upload.result.game_run_id,
            server_revision=upload.result.server_revision,
            checksum=upload.result.checksum,
            created=upload.result.created,
        )
