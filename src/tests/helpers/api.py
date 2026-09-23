from dataclasses import dataclass

from httpx2 import AsyncClient, Response


@dataclass(kw_only=True, slots=True)
class APIHelper:
    client: AsyncClient

    async def get_health(self) -> Response:
        return await self.client.get(url="/health")

    async def get_parent_report(self, *, pet_id: str) -> Response:
        return await self.client.get(url=f"/api/parents/{pet_id}")

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
