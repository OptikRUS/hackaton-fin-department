import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any, cast
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from dishka import AsyncContainer
from httpx2 import AsyncClient

from src.core.profiles.schemas import DeviceId
from src.core.snapshots.exceptions import (
    InvalidSnapshotError,
    SnapshotGameRunConflictError,
    SnapshotIdempotencyConflictError,
    SnapshotRevisionConflictError,
)
from src.core.snapshots.schemas import UploadSnapshotParams
from src.core.snapshots.use_cases import DownloadSnapshotUseCase, UploadSnapshotUseCase
from src.infra.api.snapshots.schemas import SnapshotUploadRequest
from src.infra.storages.postgres.snapshot_storage import PostgresSnapshotStorage
from src.tests.helpers.factory import FactoryHelper


@pytest.fixture
def android_upload() -> dict[str, Any]:
    return json.loads(
        (Path(__file__).parents[1] / "data/android-current-world-upload.json").read_text(),
    )


def world_request(
    body: dict[str, Any],
    *,
    run_id: str,
    predecessors: list[dict[str, Any]],
    revision: int = 1,
    upload_id: str = "next-world",
) -> dict[str, Any]:
    body = deepcopy(body)
    world = json.loads(body["snapshotJson"])
    world.update(runId=run_id, predecessors=predecessors)
    body.update(
        gameRunId=run_id,
        expectedServerRevision=revision,
        uploadId=upload_id,
        snapshotJson=json.dumps(world, ensure_ascii=False, separators=(",", ":")),
    )
    return body


def ancestor(body: dict[str, Any]) -> dict[str, Any]:
    world = json.loads(body["snapshotJson"])
    return {key: world[key] for key in ("runId", "generation", "historySequence")}


async def upload(storage: PostgresSnapshotStorage, body: dict[str, Any]):
    return await UploadSnapshotUseCase(snapshot_storage=storage).execute(
        params=SnapshotUploadRequest.parse(body).to_domain(),
        idempotency_key=body["uploadId"],
    )


async def test_actual_android_world_round_trips_exact_json_through_api(
    android_upload: dict[str, Any],
    snapshot_storage: PostgresSnapshotStorage,
    container: AsyncContainer,
    client: AsyncClient,
) -> None:
    upload_case = cast("AsyncMock", await container.get(UploadSnapshotUseCase))
    download_case = cast("AsyncMock", await container.get(DownloadSnapshotUseCase))
    upload_case.execute.side_effect = UploadSnapshotUseCase(
        snapshot_storage=snapshot_storage
    ).execute
    download_case.execute.side_effect = DownloadSnapshotUseCase(
        snapshot_storage=snapshot_storage
    ).execute
    response = await client.put(
        "/v1/profiles/snapshot",
        json=android_upload,
        headers={"Idempotency-Key": android_upload["uploadId"]},
    )
    assert response.status_code == 200
    assert response.json()["serverRevision"] == 1
    assert response.json()["checksum"] == android_upload["checksum"]
    response = await client.post(
        "/v1/profiles/snapshot/download",
        json={"deviceId": android_upload["deviceId"]},
    )
    assert response.status_code == 200
    assert response.json()["payloadKind"] == "CURRENT_WORLD"
    assert response.json()["snapshotJson"] == android_upload["snapshotJson"]


async def test_current_world_replay_and_changed_body_conflict(
    android_upload: dict[str, Any],
    snapshot_storage: PostgresSnapshotStorage,
) -> None:
    first = await upload(snapshot_storage, android_upload)
    assert await upload(snapshot_storage, android_upload) == first
    changed = {**android_upload, "currentContentFingerprint": "different-content"}
    with pytest.raises(SnapshotIdempotencyConflictError):
        await upload(snapshot_storage, changed)
    head = await snapshot_storage.get_latest(
        profile_id=DeviceId(value=android_upload["deviceId"]).profile_id,
    )
    assert head is not None
    assert head.server_revision == 1
    assert head.snapshot_json == android_upload["snapshotJson"]


async def test_compact_restart_and_old_completed_replay(
    android_upload: dict[str, Any],
    snapshot_storage: PostgresSnapshotStorage,
) -> None:
    original = await upload(snapshot_storage, android_upload)
    next_body = world_request(
        android_upload, run_id="run-B", predecessors=[ancestor(android_upload)]
    )
    assert (await upload(snapshot_storage, next_body)).server_revision == 2
    assert await upload(snapshot_storage, android_upload) == original
    head = await snapshot_storage.get_latest(
        profile_id=DeviceId(value=android_upload["deviceId"]).profile_id
    )
    assert head is not None
    assert head.game_run_id == "run-B"
    assert head.snapshot_json == next_body["snapshotJson"]


@pytest.mark.parametrize(
    "predecessors", [[], [{"runId": "unrelated", "generation": "g", "historySequence": 1}]]
)
async def test_rejects_arbitrary_run_replacement(
    android_upload: dict[str, Any],
    snapshot_storage: PostgresSnapshotStorage,
    predecessors: list[dict[str, Any]],
) -> None:
    await upload(snapshot_storage, android_upload)
    with pytest.raises(SnapshotGameRunConflictError):
        await upload(
            snapshot_storage,
            world_request(android_upload, run_id="run-B", predecessors=predecessors),
        )


async def test_compact_restart_requires_current_revision(
    android_upload: dict[str, Any],
    snapshot_storage: PostgresSnapshotStorage,
) -> None:
    await upload(snapshot_storage, android_upload)
    with pytest.raises(SnapshotRevisionConflictError):
        await upload(
            snapshot_storage,
            world_request(
                android_upload, run_id="run-B", predecessors=[ancestor(android_upload)], revision=2
            ),
        )


@pytest.mark.parametrize(("field", "value"), [("historySequence", 0)])
async def test_restart_rejects_changed_checkpoint(
    android_upload: dict[str, Any],
    snapshot_storage: PostgresSnapshotStorage,
    field: str,
    value: object,
) -> None:
    await upload(snapshot_storage, android_upload)
    previous = ancestor(android_upload)
    previous[field] = value
    with pytest.raises(SnapshotGameRunConflictError):
        await upload(
            snapshot_storage, world_request(android_upload, run_id="run-B", predecessors=[previous])
        )


async def test_compact_lineage_preserved_across_multiple_offline_restarts(
    android_upload: dict[str, Any],
    snapshot_storage: PostgresSnapshotStorage,
) -> None:
    await upload(snapshot_storage, android_upload)
    b = world_request(android_upload, run_id="run-B", predecessors=[ancestor(android_upload)])
    await upload(snapshot_storage, b)
    c = world_request(
        android_upload,
        run_id="run-C",
        predecessors=[ancestor(android_upload), ancestor(b)],
        revision=2,
        upload_id="world-C",
    )
    assert (await upload(snapshot_storage, c)).server_revision == 3
    changed = world_request(
        c, run_id="run-C", predecessors=[], revision=3, upload_id="drop-lineage"
    )
    with pytest.raises(SnapshotGameRunConflictError):
        await upload(snapshot_storage, changed)


async def test_legacy_to_current_same_run_and_restart_keep_original_retry_digest(
    android_upload: dict[str, Any],
    snapshot_storage: PostgresSnapshotStorage,
) -> None:
    profile_id = DeviceId(value=android_upload["deviceId"]).profile_id
    legacy = FactoryHelper().snapshots.upload_params(profile_id=profile_id)
    original = await UploadSnapshotUseCase(snapshot_storage=snapshot_storage).execute(
        params=legacy, idempotency_key=legacy.upload_id
    )
    same_run = world_request(android_upload, run_id="run-1", predecessors=[])
    await upload(snapshot_storage, same_run)
    restarted = world_request(
        android_upload,
        run_id="run-B",
        predecessors=[ancestor(same_run)],
        revision=2,
        upload_id="restart",
    )
    assert (await upload(snapshot_storage, restarted)).server_revision == 3
    assert (
        await UploadSnapshotUseCase(snapshot_storage=snapshot_storage).execute(
            params=legacy, idempotency_key=legacy.upload_id
        )
        == original
    )


async def test_legacy_to_current_direct_restart(
    android_upload: dict[str, Any],
    snapshot_storage: PostgresSnapshotStorage,
) -> None:
    legacy = FactoryHelper().snapshots.upload_params(
        profile_id=DeviceId(value=android_upload["deviceId"]).profile_id
    )
    await UploadSnapshotUseCase(snapshot_storage=snapshot_storage).execute(
        params=legacy, idempotency_key=legacy.upload_id
    )
    body = world_request(
        android_upload,
        run_id="run-B",
        predecessors=[{"runId": "run-1", "generation": "legacy-generation", "historySequence": 0}],
    )
    assert (await upload(snapshot_storage, body)).server_revision == 2


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("worldFormatVersion", 2),
        ("worldFormatVersion", True),
        ("generation", ""),
        ("generation", " "),
        ("generation", 1),
        ("state", None),
        ("historySequence", True),
        ("historySequence", -1),
        ("predecessors", {}),
        ("parentRewards", {}),
        ("predecessors", [{"runId": "x", "generation": "g", "historySequence": True}]),
        ("predecessors", [{"runId": "x", "generation": "", "historySequence": 0}]),
        ("predecessors", [{"runId": "x", "generation": "g", "historySequence": -1}]),
        ("predecessors", [{"runId": "x", "generation": "g", "historySequence": 0}] * 2),
    ],
)
def test_rejects_malformed_current_world_metadata(
    android_upload: dict[str, Any], field: str, value: object
) -> None:
    world = json.loads(android_upload["snapshotJson"])
    world[field] = value
    body = {**android_upload, "snapshotJson": json.dumps(world)}
    with pytest.raises(InvalidSnapshotError):
        SnapshotUploadRequest.parse(body).to_domain().validate(idempotency_key=body["uploadId"])


def test_rejects_self_ancestor(android_upload: dict[str, Any]) -> None:
    body = world_request(
        android_upload, run_id=android_upload["gameRunId"], predecessors=[ancestor(android_upload)]
    )
    with pytest.raises(InvalidSnapshotError):
        SnapshotUploadRequest.parse(body).to_domain().validate(idempotency_key=body["uploadId"])


def test_payload_kind_participates_in_current_request_digest(
    android_upload: dict[str, Any],
) -> None:
    params = SnapshotUploadRequest.parse(android_upload).to_domain()
    assert params.request_digest() != replace(params, payload_kind=None).request_digest()


def test_legacy_digest_stays_identical() -> None:
    params: UploadSnapshotParams = FactoryHelper().snapshots.upload_params(
        profile_id=UUID("12345678-1234-5678-1234-567812345678")
    )
    assert (
        params.request_digest()
        == "3fa562f122079c2c5bb8026bfb4e18bfd09f7fcf09cc818847ea91984fc5d636"
    )


async def test_restore_then_offline_restart_allows_changed_generation(
    android_upload: dict[str, Any],
    snapshot_storage: PostgresSnapshotStorage,
) -> None:
    await upload(snapshot_storage, android_upload)
    checkpoint = ancestor(android_upload)
    checkpoint["generation"] = "generation-after-restore"
    body = world_request(android_upload, run_id="run-B", predecessors=[checkpoint])
    assert (await upload(snapshot_storage, body)).server_revision == 2


@pytest.mark.parametrize(
    "field", ["snapshotFormatVersion", "throughHistorySequence", "expectedServerRevision"]
)
async def test_rejects_boolean_envelope_numbers_before_use_case(
    android_upload: dict[str, Any],
    client: AsyncClient,
    container: AsyncContainer,
    field: str,
) -> None:
    use_case = cast("AsyncMock", await container.get(UploadSnapshotUseCase))
    use_case.execute.return_value = FactoryHelper().snapshots.upload_result()
    body: dict[str, Any] = {**android_upload, field: True}
    response = await client.put(
        "/v1/profiles/snapshot", json=body, headers={"Idempotency-Key": body["uploadId"]}
    )
    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}


def reward_application(body: dict[str, Any]) -> dict[str, Any]:
    return {
        "reward": {
            "rewardId": "gift-1",
            "profileId": "profile",
            "gameRunId": body["gameRunId"],
            "sequence": 1,
            "reward": {"type": "COINS", "amount": 10},
            "createdAt": "2026-09-29T10:00:00Z",
        },
        "receipt": {
            "rewardId": "gift-1",
            "applicationId": "app-1",
            "historyEntryId": "entry-1",
            "historySequence": 900,
            "outcome": "APPLIED",
        },
    }


def test_preserves_original_local_reward_receipt_sequence(android_upload: dict[str, Any]) -> None:
    world = json.loads(android_upload["snapshotJson"])
    world["parentRewards"] = [reward_application(android_upload)]
    body = {**android_upload, "snapshotJson": json.dumps(world)}
    SnapshotUploadRequest.parse(body).to_domain().validate(idempotency_key=body["uploadId"])


@pytest.mark.parametrize(
    "mutation",
    [
        "not-object",
        "missing-reward",
        "wrong-run",
        "wrong-reward-id",
        "duplicate-reward",
        "duplicate-application",
        "different-profile",
        "boolean-sequence",
    ],
)
def test_rejects_malformed_world_reward_metadata(
    android_upload: dict[str, Any], mutation: str
) -> None:
    entry = reward_application(android_upload)
    rewards: list[Any] = [entry]
    if mutation == "not-object":
        rewards = [None]
    elif mutation == "missing-reward":
        entry.pop("reward")
    elif mutation == "wrong-run":
        entry["reward"]["gameRunId"] = "other-run"
    elif mutation == "wrong-reward-id":
        entry["receipt"]["rewardId"] = "other-reward"
    elif mutation == "boolean-sequence":
        entry["receipt"]["historySequence"] = True
    else:
        second = deepcopy(entry)
        if mutation != "duplicate-reward":
            second["reward"]["rewardId"] = "gift-2"
            second["receipt"]["rewardId"] = "gift-2"
        if mutation != "duplicate-application":
            second["receipt"]["applicationId"] = "app-2"
        if mutation == "different-profile":
            second["reward"]["profileId"] = "other-profile"
        rewards.append(second)
    world = json.loads(android_upload["snapshotJson"])
    world["parentRewards"] = rewards
    body = {**android_upload, "snapshotJson": json.dumps(world)}
    with pytest.raises(InvalidSnapshotError):
        SnapshotUploadRequest.parse(body).to_domain().validate(idempotency_key=body["uploadId"])
