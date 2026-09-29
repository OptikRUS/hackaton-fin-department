from typing import Any

import pytest

from src.core.analytics.assessment_policy import calculate_assessments


def observation(
    episode_id: str,
    *,
    outcome: str = "SUPPORTED",
    completion: str = "COMPLETE",
    eligibility: str = "ELIGIBLE",
    assistance: tuple[str, ...] = (),
    skill: str = "FIN-01",
) -> dict[str, Any]:
    return {
        "gameRunId": "run-1",
        "skill": skill,
        "episodeId": episode_id,
        "outcome": outcome,
        "eligibility": eligibility,
        "completion": completion,
        "reason": "CORRECT_COMPARISON",
        "sourceEventIds": [f"event-{episode_id}"],
        "assistance": list(assistance),
        "adultHelpKnown": False,
        "learningContexts": ["GAME"],
        "contextFamilies": ["comparison"],
        "measures": {},
        "ruleVersion": 1,
    }


def test_empty_projection_returns_all_twelve_skills_without_data() -> None:
    result = calculate_assessments(
        game_run_id="run-1", based_on_history_sequence=17, observations=[]
    )

    assert result.game_run_id == "run-1"
    assert result.based_on_history_sequence == 17
    assert [skill.skill_id for skill in result.skills] == [
        "FIN-01",
        "FIN-02",
        "FIN-03",
        "FIN-04",
        "FIN-05",
        "FIN-06",
        "FIN-07",
        "FIN-08",
        "FIN-09",
        "FIN-10",
        "FIN-11",
        "FIN-12",
    ]
    assert {skill.status for skill in result.skills} == {"NO_DATA"}
    assert {skill.policy_version for skill in result.skills} == {"skills-mvp-v1"}


@pytest.mark.parametrize(
    ("outcomes", "expected_status"),
    [
        (("NEUTRAL",), "PRACTICING"),
        (("SUPPORTED",), "PRACTICING"),
        (("DIFFICULTY",), "PRACTICING"),
        (("SUPPORTED", "SUPPORTED"), "MASTERED"),
        (("SUPPORTED", "SUPPORTED", "DIFFICULTY"), "MASTERED"),
        (("DIFFICULTY", "DIFFICULTY"), "HAS_PROBLEM"),
        (("DIFFICULTY", "DIFFICULTY", "SUPPORTED"), "HAS_PROBLEM"),
        (("SUPPORTED", "DIFFICULTY"), "PRACTICING"),
        (("SUPPORTED", "SUPPORTED", "DIFFICULTY", "DIFFICULTY"), "PRACTICING"),
        (("SUPPORTED", "SUPPORTED", "NEUTRAL", "NEUTRAL"), "MASTERED"),
    ],
)
def test_status_requires_repeated_outcomes_and_a_strict_majority(
    outcomes: tuple[str, ...], expected_status: str
) -> None:
    result = calculate_assessments(
        game_run_id="run-1",
        based_on_history_sequence=20,
        observations=[
            observation(f"ep-{index}", outcome=outcome) for index, outcome in enumerate(outcomes)
        ],
    )

    assert result.skills[0].status == expected_status
    assert {skill.status for skill in result.skills[1:]} == {"NO_DATA"}


@pytest.mark.parametrize(
    ("completion", "eligibility", "outcome"),
    [
        ("PENDING", "ELIGIBLE", "SUPPORTED"),
        ("COMPLETE", "NOT_ELIGIBLE", "SUPPORTED"),
        ("COMPLETE", "UNDETERMINED", "SUPPORTED"),
        ("COMPLETE", "ELIGIBLE", "INSUFFICIENT_DATA"),
    ],
)
def test_unsuitable_observations_do_not_establish_data(
    completion: str, eligibility: str, outcome: str
) -> None:
    result = calculate_assessments(
        game_run_id="run-1",
        based_on_history_sequence=20,
        observations=[
            observation(
                f"ep-{index}", outcome=outcome, completion=completion, eligibility=eligibility
            )
            for index in range(2)
        ],
    )

    assert result.skills[0].status == "NO_DATA"


@pytest.mark.parametrize(
    "assistance", ["HINT", "WORKED_EXAMPLE", "ANSWER_REVEALED", "ADULT_REPORTED"]
)
def test_assisted_success_does_not_complete_the_mastery_threshold(assistance: str) -> None:
    result = calculate_assessments(
        game_run_id="run-1",
        based_on_history_sequence=20,
        observations=[
            observation("ep-1"),
            observation("ep-2", assistance=(assistance,)),
            observation("ep-3", assistance=(assistance,)),
        ],
    )

    assert result.skills[0].status == "PRACTICING"


def test_information_only_assistance_does_not_prevent_mastery() -> None:
    result = calculate_assessments(
        game_run_id="run-1",
        based_on_history_sequence=20,
        observations=[
            observation("ep-1", assistance=("INFORMATION_ONLY",)),
            observation("ep-2", assistance=("INFORMATION_ONLY",)),
        ],
    )

    assert result.skills[0].status == "MASTERED"


def test_assisted_success_counts_when_balancing_difficulties() -> None:
    result = calculate_assessments(
        game_run_id="run-1",
        based_on_history_sequence=20,
        observations=[
            observation("ep-1", assistance=("HINT",)),
            observation("ep-2", assistance=("HINT",)),
            observation("ep-3", outcome="DIFFICULTY"),
            observation("ep-4", outcome="DIFFICULTY"),
        ],
    )

    assert result.skills[0].status == "PRACTICING"


def test_known_adult_help_flag_does_not_change_recorded_assistance() -> None:
    observations = [observation("ep-1"), observation("ep-2")]
    for item in observations:
        item["adultHelpKnown"] = True
    result = calculate_assessments(
        game_run_id="run-1", based_on_history_sequence=20, observations=observations
    )

    assert result.skills[0].status == "MASTERED"


def test_duplicate_episode_does_not_count_as_repeated_success() -> None:
    result = calculate_assessments(
        game_run_id="run-1",
        based_on_history_sequence=20,
        observations=[observation("ep-1"), observation("ep-1")],
    )

    assert result.skills[0].status == "PRACTICING"


def test_latest_observation_replaces_earlier_outcome_for_the_same_episode() -> None:
    result = calculate_assessments(
        game_run_id="run-1",
        based_on_history_sequence=20,
        observations=[
            observation("ep-1"),
            observation("ep-2"),
            observation("ep-2", completion="PENDING"),
        ],
    )

    assert result.skills[0].status == "PRACTICING"


def test_shared_episode_ids_are_counted_separately_for_each_skill() -> None:
    result = calculate_assessments(
        game_run_id="run-1",
        based_on_history_sequence=20,
        observations=[
            observation("ep-1"),
            observation("ep-2"),
            observation("ep-1", skill="FIN-12", outcome="DIFFICULTY"),
            observation("ep-2", skill="FIN-12", outcome="DIFFICULTY"),
        ],
    )

    assert result.skills[0].status == "MASTERED"
    assert result.skills[11].status == "HAS_PROBLEM"
    assert {skill.status for skill in result.skills[1:11]} == {"NO_DATA"}


def test_other_game_run_does_not_contribute_evidence() -> None:
    observations = [observation("ep-1"), observation("ep-2")]
    for item in observations:
        item["gameRunId"] = "other-run"
    result = calculate_assessments(
        game_run_id="run-1", based_on_history_sequence=20, observations=observations
    )

    assert result.skills[0].status == "NO_DATA"
