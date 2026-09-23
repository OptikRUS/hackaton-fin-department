from enum import StrEnum

from src.infra.api.boundary import BoundaryModel


class SkillStatus(StrEnum):
    MASTERED = "MASTERED"
    PRACTICING = "PRACTICING"
    NO_DATA = "NO_DATA"


class ParentPetResponse(BoundaryModel):
    id: str
    name: str
    temper: str
    balance: int
    selected_look_id: str
    visual_state: str


class SkillResponse(BoundaryModel):
    id: str
    title: str
    status: SkillStatus
    is_mastered: bool | None


class ParentResponse(BoundaryModel):
    pet: ParentPetResponse
    skills: list[SkillResponse]
    is_demo: bool


DEMO_SKILLS: tuple[tuple[str, str, SkillStatus], ...] = (
    ("FIN-01", "Сравнивает денежные суммы", SkillStatus.MASTERED),
    ("FIN-03", "Учитывает обязательные нужды перед желаниями", SkillStatus.PRACTICING),
    ("FIN-04", "Следит, чтобы денег хватало до следующего дохода", SkillStatus.NO_DATA),
    ("FIN-05", "Последовательно собирает на выбранную цель", SkillStatus.MASTERED),
    ("FIN-08", "Перестраивает действия после неожиданной траты", SkillStatus.PRACTICING),
    ("FIN-10", "Планирует дополнительный заработок", SkillStatus.NO_DATA),
)


def demo_skills() -> list[SkillResponse]:
    return [
        SkillResponse(
            id=skill_id,
            title=title,
            status=status,
            is_mastered=(None if status == SkillStatus.NO_DATA else status == SkillStatus.MASTERED),
        )
        for skill_id, title, status in DEMO_SKILLS
    ]
