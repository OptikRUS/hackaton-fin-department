from dataclasses import dataclass

from httpx2 import AsyncClient, Response


@dataclass(kw_only=True, slots=True)
class APIHelper:
    client: AsyncClient

    async def get_health(self) -> Response:
        return await self.client.get(url="/health")

    async def get_parent_report(self, *, pet_id: str) -> Response:
        return await self.client.get(url=f"/api/parents/{pet_id}")

    async def register_profile(  # noqa: PLR0913
        self,
        *,
        device_id: str | None,
        idempotency_key: str,
        pet_name: str = "Рыжик",
        pet_age: str = "CUB",
        pet_color: str = "COPPER",
        pet_temperament: str | None = "Curious",
        selected_look_id: str = "PLAIN",
        schema_version: int = 1,
    ) -> Response:
        return await self.client.post(
            url="/api/pets",
            headers={"Idempotency-Key": idempotency_key},
            json={
                **({"deviceId": device_id} if device_id is not None else {}),
                "schemaVersion": schema_version,
                "pet": {
                    "name": pet_name,
                    "age": pet_age,
                    "color": pet_color,
                    "temperament": pet_temperament,
                    "selectedLookId": selected_look_id,
                },
            },
        )

    async def upload_snapshot(  # noqa: PLR0913
        self,
        *,
        device_id: str,
        upload_id: str,
        expected_server_revision: int | None = None,
        game_run_id: str | None = None,
        through_history_sequence: int | None = None,
        current_content_fingerprint: str | None = None,
        snapshot_format_version: int | None = None,
        checksum: str | None = None,
        snapshot_json: str | None = None,
        schema_version: int = 1,
    ) -> Response:
        body = {
            "deviceId": device_id,
            "schemaVersion": schema_version,
            "uploadId": upload_id,
            "expectedServerRevision": expected_server_revision,
            **{
                key: value
                for key, value in {
                    "gameRunId": game_run_id,
                    "throughHistorySequence": through_history_sequence,
                    "currentContentFingerprint": current_content_fingerprint,
                    "snapshotFormatVersion": snapshot_format_version,
                    "checksum": checksum,
                    "snapshotJson": snapshot_json,
                }.items()
                if value is not None
            },
        }
        return await self.client.put(
            url="/v1/profiles/snapshot",
            headers={"Idempotency-Key": upload_id},
            json=body,
        )

    async def download_snapshot(self, *, device_id: str) -> Response:
        return await self.client.post(
            url="/v1/profiles/snapshot/download",
            json={"deviceId": device_id, "schemaVersion": 1},
        )

    async def upload_analytics(  # noqa: PLR0913
        self,
        *,
        device_id: str,
        idempotency_key: str,
        batch_id: str,
        game_run_id: str,
        through_history_sequence: int,
        facts: list[dict[str, object]],
        skills: list[dict[str, object]],
        projection_version: int = 4,
        evaluator_version: int = 1,
        schema_version: int = 1,
    ) -> Response:
        return await self.client.post(
            url="/v1/profiles/analytics",
            headers={"Idempotency-Key": idempotency_key},
            json={
                "deviceId": device_id,
                "batchId": batch_id,
                "gameRunId": game_run_id,
                "throughHistorySequence": through_history_sequence,
                "facts": facts,
                "skills": skills,
                "projectionVersion": projection_version,
                "evaluatorVersion": evaluator_version,
                "schemaVersion": schema_version,
            },
        )

    async def get_skills(self, *, device_id: str, game_run_id: str) -> Response:
        return await self.client.post(
            url="/v1/profiles/skills/query",
            json={"deviceId": device_id, "gameRunId": game_run_id, "schemaVersion": 1},
        )

    async def issue_reward(
        self,
        *,
        device_id: str,
        idempotency_key: str,
        game_run_id: str,
        reward_type: str,
        amount: int | None = None,
        item_id: str | None = None,
    ) -> Response:
        return await self.client.post(
            url="/v1/parent-profiles/rewards",
            headers={"Idempotency-Key": idempotency_key},
            json={
                "deviceId": device_id,
                "gameRunId": game_run_id,
                "reward": {
                    "type": reward_type,
                    **({"amount": amount} if amount is not None else {}),
                    **({"itemId": item_id} if item_id is not None else {}),
                },
                "schemaVersion": 1,
            },
        )

    async def list_rewards(
        self,
        *,
        device_id: str,
        game_run_id: str,
        after_sequence: int = 0,
        limit: int = 50,
    ) -> Response:
        return await self.client.post(
            url="/v1/profiles/rewards/pull",
            json={
                "deviceId": device_id,
                "gameRunId": game_run_id,
                "afterSequence": after_sequence,
                "limit": limit,
                "schemaVersion": 1,
            },
        )

    async def ack_rewards(
        self,
        *,
        device_id: str,
        idempotency_key: str,
        game_run_id: str,
        receipts: list[dict[str, object]],
    ) -> Response:
        return await self.client.post(
            url="/v1/profiles/rewards/ack",
            headers={"Idempotency-Key": idempotency_key},
            json={
                "deviceId": device_id,
                "gameRunId": game_run_id,
                "receipts": receipts,
                "schemaVersion": 1,
            },
        )

    async def create_pet(
        self,
        *,
        name: str | None = None,
        temper: str | None = None,
    ) -> Response:
        return await self.client.post(
            url="/api/legacy/pets",
            json={
                key: value
                for key, value in {"name": name, "temper": temper}.items()
                if value is not None
            },
        )
