from dataclasses import dataclass

from httpx2 import AsyncClient, Response


@dataclass(kw_only=True, slots=True)
class APIHelper:
    client: AsyncClient

    async def get_health(self) -> Response:
        return await self.client.get(url="/health")

    async def get_parent_report(self, *, pet_id: str) -> Response:
        return await self.client.get(url=f"/api/parents/{pet_id}")

    async def upload_snapshot(  # noqa: PLR0913
        self,
        *,
        profile_id: str,
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
        json_data = {
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
            url=f"/v1/profiles/{profile_id}/snapshot",
            headers={"Idempotency-Key": upload_id},
            json=json_data,
        )

    async def download_snapshot(self, *, profile_id: str) -> Response:
        return await self.client.get(url=f"/v1/profiles/{profile_id}/snapshot")

    async def create_pet(
        self,
        *,
        name: str | None = None,
        temper: str | None = None,
    ) -> Response:
        json_data = {
            key: value
            for key, value in {"name": name, "temper": temper}.items()
            if value is not None
        }
        return await self.client.post(url="/api/pets", json=json_data)
