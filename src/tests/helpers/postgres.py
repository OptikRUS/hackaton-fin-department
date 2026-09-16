from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.storages.postgres.models import PetModel


@dataclass(kw_only=True, slots=True)
class PostgresHelper:
    session: AsyncSession

    async def get_pet(self, *, pet_id: UUID) -> PetModel | None:
        return await self.session.get(PetModel, pet_id)
