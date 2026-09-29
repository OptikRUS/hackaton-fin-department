import json
from collections.abc import AsyncIterator
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from httpx2 import ASGITransport, AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncEngine

from src.core.profiles.schemas import DeviceId
from src.infra.api.app import create_app
from src.infra.storages.postgres.config import async_engine
from src.infra.storages.postgres.models import (
    AnalyticsProjectionModel,
    RewardReceiptModel,
    SkillAssessmentModel,
)


@pytest_asyncio.fixture
async def production_client(clear_tables: None, engine: AsyncEngine) -> AsyncIterator[AsyncClient]:  # noqa: ARG001
    app = create_app()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            yield client
    finally:
        await app.state.dishka_container.close()
        await async_engine.dispose()
        # Test-only cleanup: migration downgrade intentionally refuses partial ranges.
        async with engine.begin() as connection:
            await connection.execute(delete(AnalyticsProjectionModel))
            await connection.execute(delete(RewardReceiptModel))


def android_example(name: str) -> dict[str, Any]:
    return json.loads((Path(__file__).parents[1] / "data" / name).read_text())


async def test_android_reregistration_after_local_identity_migration(
    production_client: AsyncClient,
) -> None:
    original = android_example("android-register-profile.json")
    original["deviceId"] = "migration-device"
    original["pet"]["name"] = "Первый питомец"
    first = await production_client.post(
        "/api/pets", json=original, headers={"Idempotency-Key": "old-registration"}
    )
    assert first.status_code == 201, first.text

    migrated = deepcopy(original)
    migrated["pet"]["name"] = "Новый питомец"
    migrated["pet"]["temperament"] = "Joyful"
    migrated["pet"]["selectedLookId"] = "HAT"
    repeated = await production_client.post(
        "/api/pets", json=migrated, headers={"Idempotency-Key": "new-registration"}
    )
    assert repeated.status_code == 201, repeated.text
    assert repeated.json() == {"deviceId": "migration-device"}
    replay = await production_client.post(
        "/api/pets", json=migrated, headers={"Idempotency-Key": "new-registration"}
    )
    assert replay.status_code == 201, replay.text
    old_replay = await production_client.post(
        "/api/pets", json=original, headers={"Idempotency-Key": "old-registration"}
    )
    assert old_replay.status_code == 201, old_replay.text
    changed_replay = await production_client.post(
        "/api/pets", json=original, headers={"Idempotency-Key": "new-registration"}
    )
    assert changed_replay.status_code == 409, changed_replay.text
    assert changed_replay.json() == {"code": "IDEMPOTENCY_CONFLICT"}

    report = await production_client.get("/api/parents/migration-device")
    assert report.status_code == 200, report.text
    assert report.json()["pet"]["name"] == "Новый питомец"
    assert report.json()["pet"]["temper"] == "Joyful"
    assert report.json()["pet"]["selectedLookId"] == "HAT"


async def test_android_backup_analytics_and_rewards_with_production_dependencies(
    production_client: AsyncClient,
) -> None:
    client = production_client
    registration = android_example("android-register-profile.json")
    world = android_example("android-current-world-upload.json")
    analytics = android_example("android-analytics-upload.json")
    device_id = registration["deviceId"]
    run_id = world["gameRunId"]
    registered = await client.post(
        "/api/pets",
        json=registration,
        headers={"Idempotency-Key": "registration"},
    )
    assert registered.status_code == 201, registered.text

    # The independent worker may run before the first world backup.
    accepted = await client.post(
        "/v1/profiles/analytics",
        json=analytics,
        headers={"Idempotency-Key": analytics["batchId"]},
    )
    assert accepted.status_code == 200, accepted.text
    saved = await client.put(
        "/v1/profiles/snapshot",
        json=world,
        headers={"Idempotency-Key": world["uploadId"]},
    )
    assert saved.status_code == 200, saved.text
    downloaded = await client.post("/v1/profiles/snapshot/download", json={"deviceId": device_id})
    assert downloaded.status_code == 200, downloaded.text
    assert downloaded.json()["snapshotJson"] == world["snapshotJson"]
    assert saved.json()["checksum"] == world["checksum"]
    assert json.loads(downloaded.json()["snapshotJson"])["checksum"] == world["checksum"]
    assert downloaded.json()["payloadKind"] == "CURRENT_WORLD"

    # Restore resets the available local history; analytics may also lead backup.
    partial: dict[str, Any] = dict(
        analytics, batchId="restored-batch", historyStartSequence=1, throughHistorySequence=2
    )
    restored = await client.post(
        "/v1/profiles/analytics",
        json=partial,
        headers={"Idempotency-Key": partial["batchId"]},
    )
    assert restored.status_code == 200, restored.text
    replay = await client.post(
        "/v1/profiles/analytics",
        json=partial,
        headers={"Idempotency-Key": partial["batchId"]},
    )
    assert replay.json() == restored.json()
    await assert_reward_roundtrip(client, device_id, run_id)


async def assert_reward_roundtrip(client: AsyncClient, device_id: str, run_id: str) -> None:
    issued = await client.post(
        "/v1/parent-profiles/rewards",
        json={
            "deviceId": device_id,
            "gameRunId": run_id,
            "reward": {"type": "ACCESSORY", "itemId": "cosmetic-explorer-hat-v2"},
        },
        headers={"Idempotency-Key": "gift"},
    )
    assert issued.status_code == 201, issued.text
    pull_body = {"deviceId": device_id, "gameRunId": run_id, "afterSequence": 0}
    pulled = await client.post("/v1/profiles/rewards/pull", json=pull_body)
    assert pulled.status_code == 200, pulled.text
    assert pulled.json()["rewards"] == [issued.json()]
    acknowledged = await client.post(
        "/v1/profiles/rewards/ack",
        json={
            "deviceId": device_id,
            "gameRunId": run_id,
            "receipts": [
                {
                    "rewardId": issued.json()["rewardId"],
                    "applicationId": "application-1",
                    "historyEntryId": "history-1",
                    "historySequence": 3,
                    "outcome": "APPLIED",
                }
            ],
        },
        headers={"Idempotency-Key": "ack-gift"},
    )
    assert acknowledged.status_code == 200, acknowledged.text
    assert acknowledged.json()["acceptedApplicationIds"] == ["application-1"]
    # A restore can redeliver an already acknowledged gift without losing the ledger.
    redelivered = await client.post("/v1/profiles/rewards/pull", json=pull_body)
    assert redelivered.json() == pulled.json()


class TestParentReportRoundtrip:
    async def test_current_android_snapshot_and_analytics_populate_parent_report(
        self, production_client: AsyncClient
    ) -> None:
        client = production_client
        registration = android_example("android-register-profile.json")
        snapshot = android_example("android-legacy-snapshot-upload.json")
        device_id = registration["deviceId"]
        await register_skill_profile(client, device_id)

        before_snapshot = await client.get(f"/api/parents/{device_id}")
        assert before_snapshot.status_code == 200, before_snapshot.text
        assert before_snapshot.json()["pet"] == {
            "id": device_id,
            "name": "Рыжик",
            "temper": "Curious",
            "balance": None,
            "selectedLookId": "PLAIN",
            "visualState": None,
        }
        assert before_snapshot.json()["isDemo"] is False
        assert {skill["status"] for skill in before_snapshot.json()["skills"]} == {"NO_DATA"}

        saved = await client.put(
            "/v1/profiles/snapshot",
            json=snapshot,
            headers={"Idempotency-Key": snapshot["uploadId"]},
        )
        assert saved.status_code == 200, saved.text
        payload = mixed_skill_upload()
        await upload_skills(client, payload)

        report = await client.get(f"/api/parents/{device_id}")
        assert report.status_code == 200, report.text
        assert report.json()["pet"] == {
            "id": device_id,
            "name": "Рыжик",
            "temper": None,
            "balance": 100,
            "selectedLookId": "PLAIN",
            "visualState": "NORMAL",
        }
        skills = {skill["id"]: skill for skill in report.json()["skills"]}
        assert len(skills) == 12
        assert skills["FIN-01"]["status"] == "MASTERED"
        assert skills["FIN-01"]["isMastered"] is True
        assert skills["FIN-11"]["status"] == "HAS_PROBLEM"
        assert skills["FIN-11"]["isMastered"] is False
        assert skills["FIN-02"]["status"] == "NO_DATA"
        assert skills["FIN-02"]["isMastered"] is None
        assert skills["FIN-01"]["materialsAvailable"] is True

        other_run = android_example("android-analytics-upload.json")
        other_run.update(batchId="new-run-before-snapshot", gameRunId="new-run")
        await upload_skills(client, other_run)
        still_current = await client.get(f"/api/parents/{device_id}")
        assert still_current.status_code == 200, still_current.text
        assert still_current.json()["skills"] == report.json()["skills"]


MIXED_SKILL_STATUSES = {
    "FIN-01": "MASTERED",
    "FIN-02": "NO_DATA",
    "FIN-03": "NO_DATA",
    "FIN-04": "NO_DATA",
    "FIN-05": "NO_DATA",
    "FIN-06": "NO_DATA",
    "FIN-07": "NO_DATA",
    "FIN-08": "NO_DATA",
    "FIN-09": "NO_DATA",
    "FIN-10": "NO_DATA",
    "FIN-11": "HAS_PROBLEM",
    "FIN-12": "PRACTICING",
}


def mixed_skill_upload() -> dict[str, Any]:
    payload = android_example("android-analytics-upload.json")
    payload["batchId"] = "mixed-skills"
    payload["throughHistorySequence"] = 5
    run_id = payload["gameRunId"]
    tasks = [
        {"_type": "compare_amounts", "left": 20, "right": 10, "chosen": "LEFT"},
        {"_type": "compare_amounts", "left": 10, "right": 30, "chosen": "RIGHT"},
        {
            "_type": "explain_cause",
            "expectedOptionId": "larger-cost",
            "chosenOptionId": "smaller-cost",
            "sourceFactIds": ["answer-1"],
        },
        {
            "_type": "explain_cause",
            "expectedOptionId": "larger-cost",
            "chosenOptionId": "smaller-cost",
            "sourceFactIds": ["answer-2"],
        },
        {
            "_type": "read_ledger",
            "openingAvailable": 20,
            "openingSavings": 0,
            "entries": [{"operationId": "income-1", "kind": "INCOME", "amount": 10}],
            "question": "AVAILABLE_REMAINDER",
            "answer": 30,
        },
    ]
    payload["facts"] = [
        {
            "eventId": f"answer-{sequence}",
            "gameRunId": run_id,
            "episodeId": f"episode-{sequence}",
            "actionId": f"submission-{sequence}",
            "sequence": sequence,
            "detail": {
                "_type": "question_answer",
                "questionId": f"question-{sequence}",
                "attempt": 1,
                "task": task,
            },
            "contextFamily": task["_type"],
        }
        for sequence, task in enumerate(tasks, start=1)
    ]
    payload["skills"][0].update(
        completedEpisodes=2,
        supportedEpisodes=2,
        supportedWithoutGameHints=2,
        observations=[
            question_observation(run_id, "FIN-01", 1, "SUPPORTED", "CORRECT_COMPARISON"),
            question_observation(run_id, "FIN-01", 2, "SUPPORTED", "CORRECT_COMPARISON"),
        ],
    )
    payload["skills"][10].update(
        completedEpisodes=2,
        difficultyEpisodes=2,
        observations=[
            question_observation(run_id, "FIN-11", 3, "DIFFICULTY", "INCORRECT_EXPLANATION"),
            question_observation(run_id, "FIN-11", 4, "DIFFICULTY", "INCORRECT_EXPLANATION"),
        ],
    )
    payload["skills"][11].update(
        completedEpisodes=1,
        supportedEpisodes=1,
        supportedWithoutGameHints=1,
        observations=[
            question_observation(run_id, "FIN-12", 5, "SUPPORTED", "CORRECT_LEDGER_ANSWER"),
        ],
    )
    return payload


def question_observation(
    run_id: str, skill_id: str, sequence: int, outcome: str, reason: str
) -> dict[str, Any]:
    return {
        "gameRunId": run_id,
        "skill": skill_id,
        "episodeId": f"episode-{sequence}",
        "outcome": outcome,
        "eligibility": "ELIGIBLE",
        "completion": "COMPLETE",
        "reason": reason,
        "sourceEventIds": [f"answer-{sequence}"],
        "assistance": [],
        "adultHelpKnown": False,
        "learningContexts": ["GAME"],
        "contextFamilies": [
            {"FIN-01": "compare_amounts", "FIN-11": "explain_cause", "FIN-12": "read_ledger"}[
                skill_id
            ]
        ],
    }


async def register_skill_profile(client: AsyncClient, device_id: str) -> None:
    registration = android_example("android-register-profile.json")
    registration["deviceId"] = device_id
    response = await client.post(
        "/api/pets", json=registration, headers={"Idempotency-Key": f"register-{device_id}"}
    )
    assert response.status_code == 201, response.text


async def upload_skills(client: AsyncClient, payload: dict[str, Any]) -> dict[str, Any]:
    response = await client.post(
        "/v1/profiles/analytics", json=payload, headers={"Idempotency-Key": payload["batchId"]}
    )
    assert response.status_code == 200, response.text
    return response.json()


async def query_skills(client: AsyncClient, payload: dict[str, Any]) -> dict[str, Any]:
    response = await client.post(
        "/v1/profiles/skills/query",
        json={"deviceId": payload["deviceId"], "gameRunId": payload["gameRunId"]},
    )
    assert response.status_code == 200, response.text
    return response.json()


def assert_skill_response(
    response: dict[str, Any], *, run_id: str, sequence: int, statuses: dict[str, str]
) -> None:
    assert response == {
        "schemaVersion": 1,
        "gameRunId": run_id,
        "basedOnHistorySequence": sequence,
        "skills": [
            {"skillId": skill_id, "status": status, "policyVersion": "skills-mvp-v1"}
            for skill_id, status in statuses.items()
        ],
    }


async def assert_persisted_skills(
    engine: AsyncEngine, payload: dict[str, Any], statuses: dict[str, str]
) -> None:
    async with engine.connect() as connection:
        result = await connection.execute(
            select(
                SkillAssessmentModel.policy_version,
                SkillAssessmentModel.based_on_history_sequence,
                SkillAssessmentModel.skills,
            ).where(
                SkillAssessmentModel.profile_id == DeviceId(value=payload["deviceId"]).profile_id,
                SkillAssessmentModel.game_run_id == payload["gameRunId"],
            )
        )
        row = result.one_or_none()
    assert row is not None, "Analytics upload must persist a skill assessment"
    policy_version, sequence, skills = row
    assert policy_version == "skills-mvp-v1"
    assert sequence == payload["throughHistorySequence"]
    assert skills == [
        {"skillId": skill_id, "status": status} for skill_id, status in statuses.items()
    ]


async def test_android_upload_persists_all_skill_statuses_before_query(
    production_client: AsyncClient, engine: AsyncEngine
) -> None:
    payload = mixed_skill_upload()
    await register_skill_profile(production_client, payload["deviceId"])
    before_upload = await production_client.post(
        "/v1/profiles/skills/query",
        json={"deviceId": payload["deviceId"], "gameRunId": payload["gameRunId"]},
    )
    assert before_upload.status_code == 409, before_upload.text
    assert before_upload.json()["code"] == "ASSESSMENT_NOT_READY"

    await upload_skills(production_client, payload)
    # Uploading must persist the assessment before it is requested.
    await assert_persisted_skills(engine, payload, MIXED_SKILL_STATUSES)
    response = await query_skills(production_client, payload)
    assert_skill_response(
        response, run_id=payload["gameRunId"], sequence=5, statuses=MIXED_SKILL_STATUSES
    )


async def test_new_android_upload_refreshes_skills_and_old_replay_keeps_latest(
    production_client: AsyncClient, engine: AsyncEngine
) -> None:
    payload = mixed_skill_upload()
    await register_skill_profile(production_client, payload["deviceId"])
    accepted = await upload_skills(production_client, payload)
    initial = await query_skills(production_client, payload)
    assert await upload_skills(production_client, payload) == accepted
    assert await query_skills(production_client, payload) == initial

    refreshed = deepcopy(payload)
    refreshed["batchId"] = "second-ledger-answer"
    refreshed["throughHistorySequence"] = 6
    fact = deepcopy(payload["facts"][-1])
    fact.update(eventId="answer-6", episodeId="episode-6", actionId="submission-6", sequence=6)
    fact["detail"]["questionId"] = "question-6"
    refreshed["facts"].append(fact)
    refreshed["skills"][11].update(
        completedEpisodes=2, supportedEpisodes=2, supportedWithoutGameHints=2
    )
    refreshed["skills"][11]["observations"].append(
        question_observation(
            payload["gameRunId"], "FIN-12", 6, "SUPPORTED", "CORRECT_LEDGER_ANSWER"
        )
    )
    await upload_skills(production_client, refreshed)
    statuses = dict(MIXED_SKILL_STATUSES, **{"FIN-12": "MASTERED"})
    await assert_persisted_skills(engine, refreshed, statuses)
    assert_skill_response(
        await query_skills(production_client, refreshed),
        run_id=payload["gameRunId"],
        sequence=6,
        statuses=statuses,
    )
    assert await upload_skills(production_client, payload) == accepted
    assert_skill_response(
        await query_skills(production_client, payload),
        run_id=payload["gameRunId"],
        sequence=6,
        statuses=statuses,
    )


async def test_skill_assessments_are_isolated_by_profile_and_game_run(
    production_client: AsyncClient,
) -> None:
    payload = mixed_skill_upload()
    await register_skill_profile(production_client, payload["deviceId"])
    await upload_skills(production_client, payload)

    another_run = android_example("android-analytics-upload.json")
    another_run.update(batchId="another-run", gameRunId="new-game-run")
    await upload_skills(production_client, another_run)
    another_profile = android_example("android-analytics-upload.json")
    another_profile.update(batchId="another-profile", deviceId="1234567890abcdef")
    await register_skill_profile(production_client, another_profile["deviceId"])
    await upload_skills(production_client, another_profile)

    assert_skill_response(
        await query_skills(production_client, payload),
        run_id=payload["gameRunId"],
        sequence=5,
        statuses=MIXED_SKILL_STATUSES,
    )
    for isolated in (another_run, another_profile):
        assert_skill_response(
            await query_skills(production_client, isolated),
            run_id=isolated["gameRunId"],
            sequence=1,
            statuses=dict.fromkeys(MIXED_SKILL_STATUSES, "NO_DATA"),
        )


async def test_skill_query_backfills_a_predeployment_accepted_projection(
    production_client: AsyncClient, engine: AsyncEngine
) -> None:
    payload = mixed_skill_upload()
    await register_skill_profile(production_client, payload["deviceId"])
    await upload_skills(production_client, payload)
    async with engine.begin() as connection:
        # Model an accepted predeployment projection that has no assessment row.
        await connection.execute(delete(SkillAssessmentModel))
    assert_skill_response(
        await query_skills(production_client, payload),
        run_id=payload["gameRunId"],
        sequence=5,
        statuses=MIXED_SKILL_STATUSES,
    )
    await assert_persisted_skills(engine, payload, MIXED_SKILL_STATUSES)


@pytest.mark.parametrize("full_sequence", [5, 6])
async def test_partial_android_upload_retains_prefix_skills_and_combines_new_episode(
    production_client: AsyncClient, engine: AsyncEngine, full_sequence: int
) -> None:
    payload = mixed_skill_upload()
    payload["throughHistorySequence"] = full_sequence
    await register_skill_profile(production_client, payload["deviceId"])
    await upload_skills(production_client, payload)

    partial = android_example("android-analytics-upload.json")
    partial.update(batchId="restored-skills", historyStartSequence=5, throughHistorySequence=6)
    fact = deepcopy(payload["facts"][-1])
    fact.update(eventId="answer-6", episodeId="episode-6", actionId="submission-6", sequence=6)
    fact["detail"]["questionId"] = "question-6"
    partial["facts"] = [fact]
    partial["skills"][11].update(
        completedEpisodes=1,
        supportedEpisodes=1,
        supportedWithoutGameHints=1,
        observations=[
            question_observation(
                payload["gameRunId"], "FIN-12", 6, "SUPPORTED", "CORRECT_LEDGER_ANSWER"
            )
        ],
    )
    await upload_skills(production_client, partial)
    statuses = dict(MIXED_SKILL_STATUSES, **{"FIN-12": "MASTERED"})
    assert_skill_response(
        await query_skills(production_client, partial),
        run_id=payload["gameRunId"],
        sequence=6,
        statuses=statuses,
    )
    await assert_persisted_skills(engine, partial, statuses)


@pytest.mark.parametrize("latest_sequence", [6, 7])
async def test_later_partial_upload_does_not_resurrect_a_replaced_prefix_episode(
    production_client: AsyncClient, engine: AsyncEngine, latest_sequence: int
) -> None:
    payload = mixed_skill_upload()
    await register_skill_profile(production_client, payload["deviceId"])
    await upload_skills(production_client, payload)

    crossing = android_example("android-analytics-upload.json")
    crossing.update(batchId="crossing-episode", historyStartSequence=5, throughHistorySequence=6)
    fact = deepcopy(payload["facts"][-1])
    fact.update(eventId="answer-6", actionId="submission-6", sequence=6)
    fact["detail"]["questionId"] = "question-6"
    crossing["facts"] = [fact]
    observation = question_observation(
        payload["gameRunId"], "FIN-12", 6, "SUPPORTED", "CORRECT_LEDGER_ANSWER"
    )
    observation["episodeId"] = "episode-5"
    crossing["skills"][11].update(
        completedEpisodes=1,
        supportedEpisodes=1,
        supportedWithoutGameHints=1,
        observations=[observation],
    )
    await upload_skills(production_client, crossing)
    assert_skill_response(
        await query_skills(production_client, crossing),
        run_id=payload["gameRunId"],
        sequence=6,
        statuses=MIXED_SKILL_STATUSES,
    )

    latest = android_example("android-analytics-upload.json")
    latest.update(
        batchId="removed-crossing-episode",
        historyStartSequence=5,
        throughHistorySequence=latest_sequence,
    )
    latest["facts"] = [fact]
    await upload_skills(production_client, latest)
    statuses = dict(MIXED_SKILL_STATUSES, **{"FIN-12": "NO_DATA"})
    assert_skill_response(
        await query_skills(production_client, latest),
        run_id=payload["gameRunId"],
        sequence=latest_sequence,
        statuses=statuses,
    )
    await assert_persisted_skills(engine, latest, statuses)
