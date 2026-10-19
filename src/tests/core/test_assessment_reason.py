from typing import Any
from uuid import UUID

import pytest

from src.core.analytics.assessment_policy import calculate_assessments
from src.core.analytics.schemas import SkillAssessment, SkillAssessments
from src.infra.api.analytics.schemas import SkillAssessmentsResponse
from src.infra.storages.postgres.models import SkillAssessmentModel


def observation(episode: str, outcome: str = "SUPPORTED", **overrides: object) -> dict[str, Any]:
    return {
        "gameRunId": "run-1",
        "skill": "FIN-01",
        "episodeId": episode,
        "completion": "COMPLETE",
        "eligibility": "ELIGIBLE",
        "outcome": outcome,
        "assistance": [],
        **overrides,
    }


@pytest.mark.parametrize(
    ("observations", "status", "reason_part"),
    [
        ([], "NO_DATA", "Нет завершённых"),
        ([observation("a")], "PRACTICING", "пока недостаточно"),
        (
            [observation("a"), observation("b")],
            "MASTERED",
            "Успешных ситуаций без игровых подсказок: 2",
        ),
        (
            [observation("a"), observation("b", assistance=["HINT"])],
            "PRACTICING",
            "пока недостаточно",
        ),
        (
            [observation("a"), observation("b", assistance=["INFORMATION_ONLY"])],
            "MASTERED",
            "Успешных ситуаций без игровых подсказок: 2",
        ),
        (
            [
                observation("a"),
                observation("b"),
                observation("c", "DIFFICULTY"),
                observation("d", "DIFFICULTY"),
            ],
            "PRACTICING",
            "пока недостаточно",
        ),
        (
            [observation("a", "DIFFICULTY"), observation("b", "DIFFICULTY")],
            "HAS_PROBLEM",
            "Трудности повторились",
        ),
        ([observation("a", "NEUTRAL")], "PRACTICING", "пока недостаточно"),
        ([observation("a", completion="PENDING")], "NO_DATA", "Нет завершённых"),
        ([observation("a", gameRunId="other")], "NO_DATA", "Нет завершённых"),
        ([observation("a"), observation("a")], "PRACTICING", "пока недостаточно"),
        (
            [observation("a"), observation("a", "DIFFICULTY"), observation("b", "DIFFICULTY")],
            "HAS_PROBLEM",
            "Трудности повторились",
        ),
    ],
)
def test_reason_uses_same_policy_branch(
    observations: list[dict[str, Any]], status: str, reason_part: str
) -> None:
    result = calculate_assessments(
        game_run_id="run-1", based_on_history_sequence=9, observations=observations
    )
    skill = result.skills[0]
    assert skill.status == status
    assert skill.assessment_reason is not None
    assert reason_part in skill.assessment_reason
    assert 1 <= len(skill.assessment_reason) <= 600
    assert skill.explanation is None


def test_reason_survives_storage_and_response_without_client_explanation() -> None:
    result = calculate_assessments(
        game_run_id="run-1", based_on_history_sequence=9, observations=[]
    )
    model = SkillAssessmentModel.from_domain(profile_id=UUID(int=1), assessment=result)
    restored = model.to_domain()
    assert restored == result
    payload = SkillAssessmentsResponse.from_domain(assessment=restored).model_dump_json(
        by_alias=True
    )
    assert '"assessmentReason"' in payload


def test_old_stored_assessment_has_no_invented_reason() -> None:
    result = SkillAssessments(
        game_run_id="run-1",
        based_on_history_sequence=7,
        skills=tuple(
            SkillAssessment(skill_id=f"FIN-{number:02}", status="PRACTICING", policy_version="old")
            for number in range(1, 13)
        ),
    )
    model = SkillAssessmentModel.from_domain(profile_id=UUID(int=1), assessment=result)
    assert all(skill.assessment_reason is None for skill in model.to_domain().skills)
    assert '"assessmentReason"' not in SkillAssessmentsResponse.from_domain(
        assessment=result
    ).model_dump_json(by_alias=True)
