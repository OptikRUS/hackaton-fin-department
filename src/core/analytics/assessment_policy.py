from typing import Any

from src.core.analytics.schemas import SkillAssessment, SkillAssessments

POLICY_VERSION = "skills-mvp-v1"
_SKILL_IDS = tuple(f"FIN-{number:02}" for number in range(1, 13))
_MIN_REPEATED_OUTCOMES = 2


def calculate_assessments(
    *,
    game_run_id: str,
    based_on_history_sequence: int,
    observations: list[dict[str, Any]],
    explanations: dict[str, dict[str, Any]] | None = None,
) -> SkillAssessments:
    """Assess accepted observations; later occurrences replace the same skill episode."""
    latest = {
        (observation["skill"], observation["episodeId"]): observation
        for observation in observations
        if observation["gameRunId"] == game_run_id
    }
    suitable_by_skill: dict[str, list[dict[str, Any]]] = {skill: [] for skill in _SKILL_IDS}
    for observation in latest.values():
        if (
            observation["skill"] in suitable_by_skill
            and observation["completion"] == "COMPLETE"
            and observation["eligibility"] == "ELIGIBLE"
            and observation["outcome"] in {"SUPPORTED", "DIFFICULTY", "NEUTRAL"}
        ):
            suitable_by_skill[observation["skill"]].append(observation)
    return SkillAssessments(
        game_run_id=game_run_id,
        based_on_history_sequence=based_on_history_sequence,
        skills=tuple(
            _assessment(skill, suitable_by_skill[skill], (explanations or {}).get(skill))
            for skill in _SKILL_IDS
        ),
    )


def _assessment(
    skill: str,
    observations: list[dict[str, Any]],
    explanation: dict[str, Any] | None,
) -> SkillAssessment:
    status, reason = _decision(observations)
    return SkillAssessment(
        skill_id=skill,
        status=status,
        policy_version=POLICY_VERSION,
        explanation=explanation,
        assessment_reason=reason,
    )


def _decision(observations: list[dict[str, Any]]) -> tuple[str, str]:
    if not observations:
        return (
            "NO_DATA",
            (
                "Нет завершённых ситуаций, подходящих для оценки этого навыка. "
                "Это не означает, что ребёнок им не владеет."
            ),
        )
    supported = [item for item in observations if item["outcome"] == "SUPPORTED"]
    difficulty_count = sum(item["outcome"] == "DIFFICULTY" for item in observations)
    # This records assistance in the evidence; adultHelpKnown does not establish its absence.
    supported_without_assistance = sum(
        all(assistance == "INFORMATION_ONLY" for assistance in item["assistance"])
        for item in supported
    )
    if supported_without_assistance >= _MIN_REPEATED_OUTCOMES and len(supported) > difficulty_count:
        return "MASTERED", (
            f"Успешных ситуаций без игровых подсказок: {supported_without_assistance}. "
            f"Всего успешных: {len(supported)}, с трудностями: {difficulty_count}. "
            "Есть минимум два успеха без игровых подсказок, а успехов больше, чем трудностей. "
            "По текущему правилу игры навык отмечен как освоенный. "
            "Помощь взрослого могла быть не записана."
        )
    if difficulty_count >= _MIN_REPEATED_OUTCOMES and difficulty_count > len(supported):
        return "HAS_PROBLEM", (
            "Трудности повторились минимум в двух завершённых ситуациях. "
            f"Ситуаций с трудностями: {difficulty_count}, успешных: {len(supported)}. "
            "Трудностей больше, чем успехов, поэтому по текущему правилу игры отмечены трудности."
        )
    return "PRACTICING", (
        f"Успешных ситуаций: {len(supported)}, из них без игровых подсказок: "
        f"{supported_without_assistance}; с трудностями: {difficulty_count}. "
        "Этих результатов пока недостаточно для статуса «Освоен» или «Есть трудности» "
        "по текущему правилу игры. Ребёнок продолжает тренироваться."
    )
