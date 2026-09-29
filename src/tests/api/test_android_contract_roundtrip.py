import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest_asyncio
from httpx2 import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncEngine

from src.infra.api.app import create_app
from src.infra.storages.postgres.config import async_engine
from src.infra.storages.postgres.models import AnalyticsProjectionModel, RewardReceiptModel


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
