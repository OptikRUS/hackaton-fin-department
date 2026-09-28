from collections.abc import AsyncIterator

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.analytics.storages import AnalyticsStorage
from src.core.pets.storages import PetStorage
from src.core.profiles.storages import ProfileStorage
from src.core.rewards.storages import RewardStorage
from src.core.snapshots.storages import SnapshotStorage
from src.infra.storages.postgres.analytics_storage import PostgresAnalyticsStorage
from src.infra.storages.postgres.config import async_session
from src.infra.storages.postgres.pet_storage import PostgresPetStorage
from src.infra.storages.postgres.profile_storage import PostgresProfileStorage
from src.infra.storages.postgres.rewards_storage import PostgresRewardStorage
from src.infra.storages.postgres.snapshot_storage import PostgresSnapshotStorage


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

    @provide(scope=Scope.REQUEST)
    def get_snapshot_storage(self, session: AsyncSession) -> SnapshotStorage:
        return PostgresSnapshotStorage(session=session)

    @provide(scope=Scope.REQUEST)
    def get_profile_storage(self, session: AsyncSession) -> ProfileStorage:
        return PostgresProfileStorage(session=session)

    @provide(scope=Scope.REQUEST)
    def get_analytics_storage(self, session: AsyncSession) -> AnalyticsStorage:
        return PostgresAnalyticsStorage(session=session)

    @provide(scope=Scope.REQUEST)
    def get_reward_storage(self, session: AsyncSession) -> RewardStorage:
        return PostgresRewardStorage(session=session)
