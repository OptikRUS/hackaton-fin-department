from collections.abc import AsyncIterator

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.pets.storages import PetStorage
from src.infra.storages.postgres.config import async_session
from src.infra.storages.postgres.pet_storage import PostgresPetStorage


class PostgresProvider(Provider):
    @provide(scope=Scope.REQUEST)
    async def get_db_session(self) -> AsyncIterator[AsyncSession]:
        async with async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    @provide(scope=Scope.REQUEST)
    def get_pet_storage(self, session: AsyncSession) -> PetStorage:
        return PostgresPetStorage(session=session)
