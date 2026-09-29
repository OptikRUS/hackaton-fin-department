from datetime import datetime
from decimal import Decimal
from typing import Literal, Self, cast
from uuid import UUID

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from src.core.analytics.schemas import (
    AnalyticsUploadResult,
    SkillAssessment,
    SkillAssessments,
    StoredBatch,
)
from src.core.pets.schemas import Pet
from src.core.profiles.schemas import (
    PetAge,
    PetColor,
    PetTemperament,
    RegisteredPet,
    RegisteredProfile,
    RegisterProfileResult,
    RegistrationReceipt,
)
from src.core.rewards.schemas import AccessoryReward, CoinReward, Reward, RewardReceipt
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


class ProfileModel(Base):
    __tablename__ = "profiles"

    profile_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    device_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    pet_json: Mapped[dict[str, str | None]] = mapped_column(JSON, nullable=False)

    def to_domain(self) -> RegisteredProfile:
        return RegisteredProfile(
            profile_id=self.profile_id,
            device_id=self.device_id,
            pet=RegisteredPet(
                name=cast("str", self.pet_json["name"]),
                age=cast("PetAge", self.pet_json["age"]),
                color=cast("PetColor", self.pet_json["color"]),
                temperament=cast("PetTemperament", self.pet_json["temperament"]),
                selected_look_id=cast("str", self.pet_json["selectedLookId"]),
            ),
        )

    @classmethod
    def from_domain(cls, *, profile: RegisteredProfile) -> Self:
        return cls(
            profile_id=profile.profile_id,
            device_id=profile.device_id,
            pet_json={
                "name": profile.pet.name,
                "age": profile.pet.age,
                "color": profile.pet.color,
                "temperament": profile.pet.temperament,
                "selectedLookId": profile.pet.selected_look_id,
            },
        )


class ProfileRegistrationModel(Base):
    __tablename__ = "profile_registrations"

    profile_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("profiles.profile_id"),
        primary_key=True,
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), primary_key=True)
    request_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    device_id: Mapped[str] = mapped_column(String, nullable=False)
    created: Mapped[bool] = mapped_column(Boolean, nullable=False)

    def to_domain(self) -> RegistrationReceipt:
        return RegistrationReceipt(
            profile_id=self.profile_id,
            idempotency_key=self.idempotency_key,
            request_digest=self.request_digest,
            result=RegisterProfileResult(
                device_id=self.device_id,
                created=self.created,
            ),
        )


class AnalyticsHeadModel(Base):
    __tablename__ = "analytics_heads"

    profile_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    game_run_id: Mapped[str] = mapped_column(String, primary_key=True)
    through_history_sequence: Mapped[int] = mapped_column(BigInteger, nullable=False, default=-1)


class AnalyticsBatchModel(Base):
    __tablename__ = "analytics_batches"

    profile_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    batch_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    request_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    game_run_id: Mapped[str] = mapped_column(String, nullable=False)
    accepted_through_history_sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    accepted_event_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    created: Mapped[bool] = mapped_column(Boolean, nullable=False)

    def to_domain(self) -> StoredBatch:
        return StoredBatch(
            profile_id=self.profile_id,
            request_digest=self.request_digest,
            result=AnalyticsUploadResult(
                batch_id=self.batch_id,
                game_run_id=self.game_run_id,
                accepted_through_history_sequence=self.accepted_through_history_sequence,
                accepted_event_ids=tuple(self.accepted_event_ids),
                created=self.created,
            ),
        )

    @classmethod
    def from_domain(cls, *, batch: StoredBatch) -> Self:
        return cls(
            profile_id=batch.profile_id,
            batch_id=batch.result.batch_id,
            request_digest=batch.request_digest,
            game_run_id=batch.result.game_run_id,
            accepted_through_history_sequence=batch.result.accepted_through_history_sequence,
            accepted_event_ids=list(batch.result.accepted_event_ids),
            created=batch.result.created,
        )


class AnalyticsOriginalFactModel(Base):
    __tablename__ = "analytics_original_facts"

    profile_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    game_run_id: Mapped[str] = mapped_column(String, primary_key=True)
    event_id: Mapped[str] = mapped_column(String, primary_key=True)
    fact_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    sequence: Mapped[int | None] = mapped_column(BigInteger, nullable=True)


class AnalyticsProjectionModel(Base):
    __tablename__ = "analytics_projections"
    __table_args__ = (
        CheckConstraint(
            "history_start_sequence >= 0 AND history_start_sequence <= through_history_sequence",
            name="valid_history_range",
        ),
    )

    profile_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    game_run_id: Mapped[str] = mapped_column(String, primary_key=True)
    projection_version: Mapped[int] = mapped_column(Integer, primary_key=True)
    evaluator_version: Mapped[int] = mapped_column(Integer, primary_key=True)
    through_history_sequence: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    history_start_sequence: Mapped[int] = mapped_column(BigInteger, primary_key=True, default=0)
    revision: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, default=0, server_default="0"
    )
    facts: Mapped[list[dict[str, object]]] = mapped_column(JSONB, nullable=False)
    skills: Mapped[list[dict[str, object]]] = mapped_column(JSONB, nullable=False)


class SkillAssessmentModel(Base):
    __tablename__ = "skill_assessments"
    __table_args__ = (
        Index(
            "ix_skill_assessments_latest", "profile_id", "game_run_id", "based_on_history_sequence"
        ),
    )

    profile_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    game_run_id: Mapped[str] = mapped_column(String, primary_key=True)
    policy_version: Mapped[str] = mapped_column(String, primary_key=True)
    based_on_history_sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    skills: Mapped[list[dict[str, object]]] = mapped_column(JSONB, nullable=False)

    def to_domain(self) -> SkillAssessments:
        return SkillAssessments(
            game_run_id=self.game_run_id,
            based_on_history_sequence=self.based_on_history_sequence,
            skills=tuple(
                SkillAssessment(
                    skill_id=cast("str", skill["skillId"]),
                    status=cast("str", skill["status"]),
                    policy_version=self.policy_version,
                )
                for skill in self.skills
            ),
        )

    @classmethod
    def from_domain(cls, *, profile_id: UUID, assessment: SkillAssessments) -> Self:
        return cls(
            profile_id=profile_id,
            game_run_id=assessment.game_run_id,
            policy_version=assessment.skills[0].policy_version,
            based_on_history_sequence=assessment.based_on_history_sequence,
            skills=[
                {"skillId": skill.skill_id, "status": skill.status} for skill in assessment.skills
            ],
        )


class RewardModel(Base):
    __tablename__ = "parent_rewards"
    __table_args__ = (
        UniqueConstraint(
            "profile_id", "game_run_id", "sequence", name="uq_parent_rewards_sequence"
        ),
        UniqueConstraint(
            "profile_id",
            "idempotency_key",
            name="uq_parent_rewards_request",
        ),
        CheckConstraint("sequence > 0", name="positive_sequence"),
        CheckConstraint(
            "(reward_type = 'COINS' AND amount > 0 AND item_id IS NULL) OR "
            "(reward_type = 'ACCESSORY' AND amount IS NULL AND item_id IS NOT NULL)",
            name="valid_payload",
        ),
    )

    reward_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    profile_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("snapshot_heads.profile_id"),
        nullable=False,
    )
    game_run_id: Mapped[str] = mapped_column(String, nullable=False)
    sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    reward_type: Mapped[str] = mapped_column(String(16), nullable=False)
    amount: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    item_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def to_domain(self) -> Reward:
        payload = (
            CoinReward(amount=self.amount)
            if self.reward_type == "COINS" and self.amount is not None
            else AccessoryReward(item_id=self.item_id or "")
        )
        return Reward(
            reward_id=self.reward_id,
            profile_id=self.profile_id,
            game_run_id=self.game_run_id,
            sequence=self.sequence,
            reward=payload,
            created_at=self.created_at,
        )


class RewardReceiptModel(Base):
    __tablename__ = "parent_reward_receipts"
    __table_args__ = (
        CheckConstraint("history_sequence > 0", name="positive_history_sequence"),
        CheckConstraint("outcome IN ('APPLIED', 'ALREADY_OWNED')", name="valid_outcome"),
    )

    application_id: Mapped[str] = mapped_column(String(), primary_key=True)
    profile_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    game_run_id: Mapped[str] = mapped_column(String, nullable=False)
    reward_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("parent_rewards.reward_id"),
        nullable=False,
    )
    history_entry_id: Mapped[str] = mapped_column(String, nullable=False)
    history_sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)

    def to_domain(self) -> RewardReceipt:
        return RewardReceipt(
            reward_id=self.reward_id,
            application_id=self.application_id,
            history_entry_id=self.history_entry_id,
            history_sequence=self.history_sequence,
            outcome=cast("Literal['APPLIED', 'ALREADY_OWNED']", self.outcome),
        )


class RewardAckModel(Base):
    __tablename__ = "parent_reward_ack_requests"

    profile_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), primary_key=True)
    digest: Mapped[str] = mapped_column(String(64), nullable=False)
