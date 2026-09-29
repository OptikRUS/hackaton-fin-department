from enum import StrEnum

from src.infra.api.boundary import BoundaryModel
from src.infra.api.parents.skill_content import ParentMaterialsResponse


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
    materials_available: bool
    learning_goal: str
    story: str
    replace_with_parent_story: str
    conversation_starters: list[str]
    parent_takeaway: str
    research_basis: str
    research_sources: list[str]


class ParentResponse(BoundaryModel):
    pet: ParentPetResponse
    skills: list[SkillResponse]
    is_demo: bool


DEMO_SKILLS: tuple[tuple[str, str, SkillStatus], ...] = (
    ("FIN-01", "Сравнивает денежные суммы", SkillStatus.MASTERED),
    ("FIN-02", "Планирует бюджет на период", SkillStatus.NO_DATA),
    ("FIN-03", "Учитывает обязательные нужды перед желаниями", SkillStatus.PRACTICING),
    ("FIN-04", "Следит, чтобы денег хватало до следующего дохода", SkillStatus.NO_DATA),
    ("FIN-05", "Последовательно собирает на выбранную цель", SkillStatus.MASTERED),
    ("FIN-06", "Откладывает желанную покупку ради приоритета", SkillStatus.NO_DATA),
    ("FIN-07", "Создаёт запас на непредвиденные расходы", SkillStatus.NO_DATA),
    ("FIN-08", "Перестраивает действия после неожиданной траты", SkillStatus.PRACTICING),
    ("FIN-09", "Сопоставляет денежные и другие затраты", SkillStatus.NO_DATA),
    ("FIN-10", "Планирует дополнительный заработок", SkillStatus.NO_DATA),
    ("FIN-11", "Разбирает финансовые последствия и меняет решение", SkillStatus.NO_DATA),
    ("FIN-12", "Понимает свои доходы и расходы", SkillStatus.NO_DATA),
)


def demo_skills(materials: ParentMaterialsResponse) -> list[SkillResponse]:
    content_by_id = {skill.skill_id: skill for skill in materials.skills}
    skills: list[SkillResponse] = []
    for skill_id, title, status in DEMO_SKILLS:
        content = content_by_id.get(skill_id)
        skills.append(
            SkillResponse(
                id=skill_id,
                title=title,
                status=status,
                is_mastered=(
                    None if status == SkillStatus.NO_DATA else status == SkillStatus.MASTERED
                ),
                materials_available=content is not None,
                learning_goal=content.learning_goal if content else "",
                story=content.story if content else "",
                replace_with_parent_story=content.replace_with_parent_story if content else "",
                conversation_starters=list(content.conversation_starters) if content else [],
                parent_takeaway=content.parent_takeaway if content else "",
                research_basis=content.research_basis if content else "",
                research_sources=list(content.research_sources) if content else [],
            ),
        )
    return skills
