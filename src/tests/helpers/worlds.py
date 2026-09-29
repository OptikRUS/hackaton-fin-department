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


def world_snapshot_json(**overrides: Any) -> str:  # noqa: ANN401
    return json.dumps(world_snapshot_document(**overrides))
