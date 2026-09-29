from dataclasses import dataclass
from typing import Any

from src.core.analytics.storages import AnalyticsStorage
from src.core.parents.exceptions import ParentReportNotFoundError
from src.core.parents.schemas import ParentPet, ParentReport, ParentSkillStatus
from src.core.profiles.exceptions import InvalidRegistrationError
from src.core.profiles.schemas import DeviceId, RegisteredProfile
from src.core.profiles.storages import ProfileStorage
from src.core.snapshots.schemas import Snapshot, SnapshotArchive
from src.core.snapshots.storages import SnapshotStorage
from src.core.use_case import UseCase


@dataclass(frozen=True, slots=True, kw_only=True)
class GetParentReportUseCase(UseCase):
    profile_storage: ProfileStorage
    snapshot_storage: SnapshotStorage
    analytics_storage: AnalyticsStorage

    async def execute(self, *, device_id: str) -> ParentReport:
        try:
            profile_id = DeviceId(value=device_id).profile_id
        except InvalidRegistrationError as error:
            raise ParentReportNotFoundError from error
        profile = await self.profile_storage.get_profile(profile_id=profile_id)
        if profile is None or profile.device_id != device_id:
            raise ParentReportNotFoundError
        snapshot = await self.snapshot_storage.get_latest(profile_id=profile_id)
        assessment = (
            await self.analytics_storage.get_assessment(
                profile_id=profile_id,
                game_run_id=snapshot.game_run_id,
            )
            if snapshot is not None
            else None
        )
        statuses = (
            {skill.skill_id: skill.status for skill in assessment.skills}
            if assessment is not None
            else {}
        )
        return ParentReport(
            pet=_parent_pet(profile=profile, snapshot=snapshot),
            skill_statuses=tuple(
                ParentSkillStatus(
                    skill_id=f"FIN-{number:02d}",
                    status=statuses.get(f"FIN-{number:02d}", "NO_DATA"),
                )
                for number in range(1, 13)
            ),
        )


def _parent_pet(*, profile: RegisteredProfile, snapshot: Snapshot | None) -> ParentPet:
    pet: dict[str, Any] = {}
    economy: dict[str, Any] = {}
    if snapshot is not None:
        document = SnapshotArchive.from_json(snapshot_json=snapshot.snapshot_json).document
        state = document.get("state")
        if isinstance(state, dict):
            if isinstance(state.get("pet"), dict):
                pet = state["pet"]
            if isinstance(state.get("economy"), dict):
                economy = state["economy"]
    name = pet.get("name")
    temper = pet.get("temperament", profile.pet.temperament)
    look = pet.get("selectedLookId")
    visual = pet.get("visualState")
    available = economy.get("availableBalance")
    savings = economy.get("savingsBalance")
    balance = (
        available + savings
        if type(available) is int
        and type(savings) is int
        and available >= 0
        and savings >= 0
        and available + savings <= 2**63 - 1
        else None
    )
    return ParentPet(
        id=profile.device_id,
        name=name if isinstance(name, str) and name.strip() else profile.pet.name,
        temper=temper if isinstance(temper, str) or temper is None else profile.pet.temperament,
        balance=balance,
        selected_look_id=look
        if isinstance(look, str) and look.strip()
        else profile.pet.selected_look_id,
        visual_state=visual if isinstance(visual, str) and visual.strip() else None,
    )
