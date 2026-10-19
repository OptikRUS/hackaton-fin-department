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
    all_by_skill: dict[str, list[dict[str, Any]]] = {skill: [] for skill in _SKILL_IDS}
    suitable_by_skill: dict[str, list[dict[str, Any]]] = {skill: [] for skill in _SKILL_IDS}
    for observation in latest.values():
        if observation["skill"] in all_by_skill:
            all_by_skill[observation["skill"]].append(observation)
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
            _assessment(
                skill,
                suitable_by_skill[skill],
                (explanations or {}).get(skill),
                all_by_skill[skill],
            )
            for skill in _SKILL_IDS
        ),
    )


def _assessment(
    skill: str,
    observations: list[dict[str, Any]],
    explanation: dict[str, Any] | None,
    all_observations: list[dict[str, Any]],
) -> SkillAssessment:
    status, reason = _decision(observations)
    return SkillAssessment(
        skill_id=skill,
        status=status,
        policy_version=POLICY_VERSION,
        explanation=explanation,
        assessment_reason=reason,
        observation_counts=_observation_counts(all_observations),
    )


def _decision(observations: list[dict[str, Any]]) -> tuple[str, str]:
    if not observations:
        return (
            "NO_DATA",
            (
                "Завершённых игровых ситуаций по этой теме пока не было. "
                "Это не значит, что ребёнок не умеет, — просто таких случаев ещё не случилось."
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
            f"У ребёнка минимум два успеха без игровых подсказок: успешных ситуаций {len(supported)}, "
            f"с трудностями {difficulty_count}. Успехов больше, поэтому по правилу игры "
            "навык отмечен как освоенный. Помощь взрослого могла остаться незамеченной."
        )
    if difficulty_count >= _MIN_REPEATED_OUTCOMES and difficulty_count > len(supported):
        return "HAS_PROBLEM", (
            f"Трудности повторились минимум в двух ситуациях: их {difficulty_count}, успешных {len(supported)}. "
            "Трудностей больше, поэтому по правилу игры отмечены трудности. "
            "Разберите одну из таких ситуаций вместе — это обычно помогает."
        )
    return "PRACTICING", (
        f"Успешных ситуаций пока {len(supported)}, из них без подсказок {supported_without_assistance}, "
        f"с трудностями {difficulty_count}. Для статуса «Освоен» или «Есть трудности» этого мало. "
        "Ребёнок тренируется — это обычный этап."
    )


def _observation_counts(observations: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "observedEpisodes": len(observations),
        "completedEpisodes": sum(
            o["completion"] == "COMPLETE" and o["eligibility"] == "ELIGIBLE" for o in observations
        ),
        "supportedEpisodes": sum(o["outcome"] == "SUPPORTED" for o in observations),
        "difficultyEpisodes": sum(o["outcome"] == "DIFFICULTY" for o in observations),
        "neutralEpisodes": sum(o["outcome"] == "NEUTRAL" for o in observations),
        "pendingEpisodes": sum(o["completion"] == "PENDING" for o in observations),
        "incompleteEpisodes": sum(o["outcome"] == "INSUFFICIENT_DATA" for o in observations),
        "supportedWithoutGameHints": sum(
            o["outcome"] == "SUPPORTED" and all(a == "INFORMATION_ONLY" for a in o["assistance"])
            for o in observations
        ),
        "assistedEpisodes": sum(
            any(a != "INFORMATION_ONLY" for a in o["assistance"]) for o in observations
        ),
    }
