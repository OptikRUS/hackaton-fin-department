from dataclasses import dataclass

from httpx2 import AsyncClient, Response


@dataclass(kw_only=True, slots=True)
class APIHelper:
    client: AsyncClient

    async def get_health(self) -> Response:
        return await self.client.get(url="/health")
