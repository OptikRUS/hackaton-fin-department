from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.pets.schemas import Pet
from src.core.pets.storages import PetStorage
from src.infra.storages.postgres.models import PetModel


@dataclass(kw_only=True, slots=True)
class PostgresPetStorage(PetStorage):
    session: AsyncSession

    async def create_pet(self, *, pet: Pet) -> Pet:
        model = PetModel.from_domain(pet=pet)
        self.session.add(model)
        await self.session.flush()
        return model.to_domain()
