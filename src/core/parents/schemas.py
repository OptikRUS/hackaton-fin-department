from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class ParentPet:
    id: str
    name: str
    temper: str | None
    balance: int | None
    selected_look_id: str
    visual_state: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class ParentSkillStatus:
    skill_id: str
    status: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ParentReport:
    pet: ParentPet
    skill_statuses: tuple[ParentSkillStatus, ...]
