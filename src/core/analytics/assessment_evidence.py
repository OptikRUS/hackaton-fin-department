from typing import Any

from src.core.analytics.schemas import AssessmentProjection


def merge_observations(projections: list[AssessmentProjection]) -> list[dict[str, Any]]:
    """Overlay cumulative ranges without counting the same episode twice.

    Preserve the accepted prefix after a current-world restore. When an episode
    straddles that boundary, a partial/incomplete result cannot erase its earlier
    completed evidence. This merges observations; it does not rerun the mobile
    evaluator on a reconstructed event history.
    """
    retained: dict[tuple[str, str], tuple[dict[str, Any], int]] = {}
    for projection in sorted(
        projections,
        key=lambda p: (
            p.through_history_sequence,
            p.revision,
            p.history_start_sequence,
        ),
    ):
        start = projection.history_start_sequence
        retained = {
            key: value for key, value in retained.items() if start > 0 and value[1] <= start
        }
        sequences = {fact["eventId"]: fact["sequence"] for fact in projection.facts}
        for skill in projection.skills:
            for observation in skill["observations"]:
                sources = observation["sourceEventIds"]
                if not sources:
                    continue
                key = (observation["skill"], observation["episodeId"])
                previous = retained.get(key)
                if previous is not None and _completed(previous[0]) and not _completed(observation):
                    continue
                retained[key] = (observation, min(sequences[source] for source in sources))
    return [observation for observation, _ in retained.values()]


def _completed(observation: dict[str, Any]) -> bool:
    return bool(
        observation["completion"] == "COMPLETE"
        and observation["eligibility"] == "ELIGIBLE"
        and observation["outcome"] in {"SUPPORTED", "DIFFICULTY", "NEUTRAL"}
    )
