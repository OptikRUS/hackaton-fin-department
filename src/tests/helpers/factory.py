import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from src.core.analytics.schemas import (
    AnalyticsUploadParams,
    AnalyticsUploadResult,
    SkillAssessment,
    SkillAssessments,
    StoredBatch,
)
from src.core.pets.schemas import CreatePetParams, Pet
from src.core.profiles.schemas import (
    RegisteredPet,
    RegisteredProfile,
    RegisterProfileParams,
    RegisterProfileResult,
    RegistrationReceipt,
)
from src.core.rewards.schemas import CoinReward, Reward, RewardPayload, RewardReceipt
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


class ProfilesFactory:
    @staticmethod
    def registered_profile(
        *,
        profile_id: UUID,
        device_id: str,
        pet_name: str = "Рыжик",
    ) -> RegisteredProfile:
        return RegisteredProfile(
            profile_id=profile_id,
            device_id=device_id,
            pet=RegisteredPet(
                name=pet_name,
                age="CUB",
                color="COPPER",
                temperament="Curious",
                selected_look_id="PLAIN",
            ),
        )

    @staticmethod
    def register_params(
        *,
        device_id: str,
    ) -> RegisterProfileParams:
        return RegisterProfileParams(
            device_id=device_id,
            pet=RegisteredPet(
                name="Рыжик",
                age="CUB",
                color="COPPER",
                temperament="Curious",
                selected_look_id="PLAIN",
            ),
        )

    @staticmethod
    def register_result(
        *,
        device_id: str,
        created: bool = True,
    ) -> RegisterProfileResult:
        return RegisterProfileResult(
            device_id=device_id,
            created=created,
        )

    @classmethod
    def registration_receipt(
        cls,
        *,
        profile_id: UUID,
        device_id: str,
        idempotency_key: str = "registration-1",
        request_digest: str = "a" * 64,
        created: bool = True,
    ) -> RegistrationReceipt:
        return RegistrationReceipt(
            profile_id=profile_id,
            idempotency_key=idempotency_key,
            request_digest=request_digest,
            result=cls.register_result(device_id=device_id, created=created),
        )


class AnalyticsFactory:
    @staticmethod
    def upload_params(
        *,
        profile_id: UUID,
        facts: list[dict[str, Any]] | None = None,
        skills: list[dict[str, Any]] | None = None,
        sequence: int = 0,
        batch_id: str = "batch-1",
    ) -> AnalyticsUploadParams:
        if skills is None:
            skills = [
                {
                    "skillId": f"FIN-{number:02}",
                    "completedEpisodes": 0,
                    "supportedEpisodes": 0,
                    "difficultyEpisodes": 0,
                    "neutralEpisodes": 0,
                    "pendingEpisodes": 0,
                    "incompleteEpisodes": 0,
                    "supportedWithoutGameHints": 0,
                    "assistedEpisodes": 0,
                    "observations": [],
                }
                for number in range(1, 13)
            ]
        return AnalyticsUploadParams(
            profile_id=profile_id,
            batch_id=batch_id,
            game_run_id="run-1",
            through_history_sequence=sequence,
            projection_version=4,
            evaluator_version=1,
            facts=facts or [],
            skills=skills,
        )

    @staticmethod
    def upload_result(
        *,
        batch_id: str = "batch-1",
        sequence: int = 0,
        event_ids: tuple[str, ...] = (),
        created: bool = True,
    ) -> AnalyticsUploadResult:
        return AnalyticsUploadResult(
            batch_id=batch_id,
            game_run_id="run-1",
            accepted_through_history_sequence=sequence,
            accepted_event_ids=event_ids,
            created=created,
        )

    @classmethod
    def stored_batch(
        cls,
        *,
        profile_id: UUID,
        request_digest: str = "a" * 64,
        result: AnalyticsUploadResult | None = None,
    ) -> StoredBatch:
        return StoredBatch(
            profile_id=profile_id,
            request_digest=request_digest,
            result=result if result is not None else cls.upload_result(),
        )

    @staticmethod
    def assessment(
        *,
        sequence: int = 0,
        policy_version: str = "policy-1",
        status: str = "NO_DATA",
    ) -> SkillAssessments:
        return SkillAssessments(
            game_run_id="run-1",
            based_on_history_sequence=sequence,
            skills=tuple(
                SkillAssessment(
                    skill_id=f"FIN-{number:02}",
                    status=status,
                    policy_version=policy_version,
                )
                for number in range(1, 13)
            ),
        )


class RewardsFactory:
    @staticmethod
    def grant(
        *,
        profile_id: UUID,
        sequence: int = 1,
        reward_id: UUID | None = None,
        reward: RewardPayload | None = None,
        created_at: datetime = datetime(2026, 9, 27, 12, tzinfo=UTC),
    ) -> Reward:
        return Reward(
            reward_id=reward_id
            if reward_id is not None
            else UUID("5488c280-7f73-44e4-93a2-74d46e21a2e3"),
            profile_id=profile_id,
            game_run_id="run-1",
            sequence=sequence,
            reward=reward if reward is not None else CoinReward(amount=20),
            created_at=created_at,
        )

    @staticmethod
    def receipt(
        *,
        application_id: str | None = None,
        history_entry_id: str = "reward-application:7e0f74aa-9354-47f4-a2a6-3857bf3b7571",
        history_sequence: int = 18,
    ) -> RewardReceipt:
        return RewardReceipt(
            reward_id=UUID("5488c280-7f73-44e4-93a2-74d46e21a2e3"),
            application_id=application_id
            if application_id is not None
            else "7e0f74aa-9354-47f4-a2a6-3857bf3b7571",
            history_entry_id=history_entry_id,
            history_sequence=history_sequence,
            outcome="APPLIED",
        )


class SnapshotsFactory:
    @classmethod
    def archive_json(
        cls,
        *,
        format_version: int = 4,
        run_id: str = "run-1",
        history_sequence: int = 0,
        checksum: str = "a" * 64,
        history: list[dict[str, Any]] | None = None,
        archived_runs: list[dict[str, Any]] | None = None,
    ) -> str:
        return json.dumps(
            {
                "formatVersion": format_version,
                "runId": run_id,
                "historySequence": history_sequence,
                "checksum": checksum,
                **({"history": history} if history is not None else {}),
                **({"archivedRuns": archived_runs} if archived_runs is not None else {}),
            },
            separators=(",", ":"),
        )

    @classmethod
    def archived_run(
        cls,
        *,
        run_id: str = "run-1",
        next_run_id: str = "run-2",
        restart_request_id: str = "restart-1",
        history_sequence: int = 0,
        history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        return {
            "restartRequestId": restart_request_id,
            "nextRunId": next_run_id,
            "snapshot": json.loads(
                cls.archive_json(
                    run_id=run_id,
                    history_sequence=history_sequence,
                    history=history if history is not None else [],
                )
            ),
        }

    @classmethod
    def upload_params(
        cls,
        *,
        profile_id: UUID,
        upload_id: str = "upload-1",
        expected_server_revision: int | None = None,
        game_run_id: str = "run-1",
        snapshot_json: str | None = None,
        snapshot_format_version: int = 4,
    ) -> UploadSnapshotParams:
        return UploadSnapshotParams(
            profile_id=profile_id,
            upload_id=upload_id,
            expected_server_revision=expected_server_revision,
            game_run_id=game_run_id,
            through_history_sequence=0,
            current_content_fingerprint="catalog-v1",
            snapshot_format_version=snapshot_format_version,
            checksum="a" * 64,
            snapshot_json=snapshot_json
            if snapshot_json is not None
            else cls.archive_json(
                format_version=snapshot_format_version,
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
    profiles: ProfilesFactory = field(default_factory=ProfilesFactory)
    analytics: AnalyticsFactory = field(default_factory=AnalyticsFactory)
    rewards: RewardsFactory = field(default_factory=RewardsFactory)
    snapshots: SnapshotsFactory = field(default_factory=SnapshotsFactory)
