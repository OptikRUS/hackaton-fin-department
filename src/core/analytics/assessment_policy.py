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
            SkillAssessment(
                skill_id=skill,
                status=_status(suitable_by_skill[skill]),
                policy_version=POLICY_VERSION,
            )
            for skill in _SKILL_IDS
        ),
    )


def _status(observations: list[dict[str, Any]]) -> str:
    if not observations:
        return "NO_DATA"
    supported = [item for item in observations if item["outcome"] == "SUPPORTED"]
    difficulty_count = sum(item["outcome"] == "DIFFICULTY" for item in observations)
    # This records assistance in the evidence; adultHelpKnown does not establish its absence.
    supported_without_assistance = sum(
        all(assistance == "INFORMATION_ONLY" for assistance in item["assistance"])
        for item in supported
    )
    if supported_without_assistance >= _MIN_REPEATED_OUTCOMES and len(supported) > difficulty_count:
        return "MASTERED"
    if difficulty_count >= _MIN_REPEATED_OUTCOMES and difficulty_count > len(supported):
        return "HAS_PROBLEM"
    return "PRACTICING"
