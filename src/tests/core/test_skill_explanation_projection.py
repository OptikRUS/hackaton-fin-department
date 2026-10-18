from typing import Any
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from src.core.analytics.schemas import AssessmentProjection
from src.core.analytics.storages import AnalyticsStorage
from src.core.analytics.use_cases import _refresh_assessment


def observation(episode_id: str, event_id: str, *, measure: int = 1) -> dict[str, Any]:
    return {
        "gameRunId": "run-1",
        "skill": "FIN-01",
        "episodeId": episode_id,
        "completion": "COMPLETE",
        "eligibility": "ELIGIBLE",
        "outcome": "SUPPORTED",
        "sourceEventIds": [event_id],
        "assistance": [],
        "measures": {"amount": measure},
    }


def projection(
    *,
    sequence: int,
    start: int,
    revision: int,
    observations: list[dict[str, Any]],
    explanation: dict[str, Any] | None = None,
) -> AssessmentProjection:
    events = {event_id for item in observations for event_id in item["sourceEventIds"]}
    return AssessmentProjection(
        through_history_sequence=sequence,
        history_start_sequence=start,
        revision=revision,
        facts=[
            {"eventId": event_id, "sequence": index + 1}
            for index, event_id in enumerate(sorted(events))
        ],
        skills=[
            {
                "skillId": "FIN-01",
                "observations": observations,
                **({"explanation": explanation} if explanation is not None else {}),
            }
        ],
    )


@pytest.mark.asyncio
async def test_restored_prefix_prevents_partial_explanation() -> None:
    explanation = {"version": 1, "description": "Навык.", "summary": "Два эпизода.", "evidence": []}
    previous = projection(
        sequence=1, start=0, revision=1, observations=[observation("first", "event-1")]
    )
    latest = projection(
        sequence=2,
        start=1,
        revision=2,
        observations=[observation("second", "event-2")],
        explanation=explanation,
    )
    storage = AsyncMock(spec=AnalyticsStorage)
    storage.get_assessment_projections.return_value = [previous, latest]

    result = await _refresh_assessment(storage, profile_id=UUID(int=1), game_run_id="run-1")

    assert result is not None
    assert result.skills[0].explanation is None


@pytest.mark.asyncio
async def test_full_latest_projection_keeps_explanation() -> None:
    explanation = {"version": 1, "description": "Навык.", "summary": "Два эпизода.", "evidence": []}
    first = observation("first", "event-1")
    second = observation("second", "event-2")
    previous = projection(sequence=1, start=0, revision=1, observations=[first])
    latest = projection(
        sequence=2,
        start=0,
        revision=2,
        observations=[first, second],
        explanation=explanation,
    )
    storage = AsyncMock(spec=AnalyticsStorage)
    storage.get_assessment_projections.return_value = [previous, latest]

    result = await _refresh_assessment(storage, profile_id=UUID(int=1), game_run_id="run-1")

    assert result is not None
    assert result.skills[0].explanation == explanation


@pytest.mark.asyncio
async def test_repeated_episode_does_not_attach_explanation() -> None:
    explanation = {"version": 1, "description": "Навык.", "summary": "Один эпизод.", "evidence": []}
    latest = projection(
        sequence=1,
        start=0,
        revision=1,
        observations=[observation("first", "event-1"), observation("first", "event-1")],
        explanation=explanation,
    )
    storage = AsyncMock(spec=AnalyticsStorage)
    storage.get_assessment_projections.return_value = [latest]

    result = await _refresh_assessment(storage, profile_id=UUID(int=1), game_run_id="run-1")

    assert result is not None
    assert result.skills[0].explanation is None


@pytest.mark.asyncio
async def test_latest_projection_without_explanation_does_not_reuse_older_text() -> None:
    explanation = {"version": 1, "description": "Навык.", "summary": "Один эпизод.", "evidence": []}
    first = observation("first", "event-1")
    previous = projection(
        sequence=1, start=0, revision=1, observations=[first], explanation=explanation
    )
    latest = projection(sequence=1, start=0, revision=2, observations=[first])
    storage = AsyncMock(spec=AnalyticsStorage)
    storage.get_assessment_projections.return_value = [previous, latest]

    result = await _refresh_assessment(storage, profile_id=UUID(int=1), game_run_id="run-1")

    assert result is not None
    assert result.skills[0].explanation is None
