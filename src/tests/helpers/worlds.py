import json
from typing import Any

WORLD_RUN_ID = "run-1"


def world_snapshot_document(**overrides: Any) -> dict[str, Any]:  # noqa: ANN401
    document: dict[str, Any] = {
        "worldFormatVersion": 1,
        "runId": WORLD_RUN_ID,
        "historySequence": 12,
        "generation": "gen-1",
        "checksum": "c" * 64,
        "state": {
            "pet": {
                "name": "Шарик",
                "age": "TEEN",
                "temperament": "CURIOUS",
                "selectedLookId": "BANDANA",
            },
            "economy": {
                "unallocated": 40,
                "availableBalance": 640,
                "savingsBalance": 300,
                "plan": {"needs": 500, "wants": 150, "savings": 100, "reserve": 50},
            },
            "story": {
                "currentDayId": "campaign-choice-v1:act-3:day",
                "nextScriptPosition": 2,
                "activeEventId": None,
                "decisions": [],
            },
            "engine": {"day": 7},
            "completedMiniGames": ["a1", "a2"],
            "ownedItems": [{"id": "o1", "itemId": "ball"}],
            "completedGoalProjects": [{"goalId": "campaign-tower-kit-v1", "decisionId": "d1"}],
        },
    }
    document["state"].update(overrides.pop("state", {}))
    document.update(overrides)
    return document


def legacy_fact(event_id: str, detail: dict[str, Any]) -> dict[str, Any]:
    return {
        "eventId": event_id,
        "gameRunId": WORLD_RUN_ID,
        "episodeId": "episode-1",
        "actionId": f"action-{event_id}",
        "sequence": 1,
        "detail": detail,
        "actor": "CHILD",
        "mode": "REAL",
    }


def world_snapshot_json(**overrides: Any) -> str:  # noqa: ANN401
    return json.dumps(world_snapshot_document(**overrides))


def legacy_archive_json(**overrides: Any) -> str:  # noqa: ANN401
    """Full v5 archive with a history entry carrying facts — the pre-CURRENT_WORLD lane."""
    document = world_snapshot_document(**overrides)
    document.pop("worldFormatVersion")
    document["formatVersion"] = 5
    document["history"] = overrides.pop(
        "history",
        [
            {
                "id": "entry-1",
                "sequence": 1,
                "runId": document["runId"],
                "type": "COMMAND",
                "facts": [
                    legacy_fact("e1", {"_type": "interaction", "name": "RenamePet"}),
                    legacy_fact(
                        "e2",
                        {
                            "_type": "optional_purchase",
                            "itemId": "ball",
                            "price": 50,
                            "purchased": True,
                        },
                    ),
                    legacy_fact(
                        "e3",
                        {
                            "_type": "budget_confirmed",
                            "planId": "p1",
                            "planVersion": 1,
                            "allocationBase": 800,
                            "needs": 500,
                            "wants": 100,
                            "savings": 150,
                            "reserve": 50,
                            "cause": "WEEKLY",
                        },
                    ),
                ],
            }
        ],
    )
    return json.dumps(document)
