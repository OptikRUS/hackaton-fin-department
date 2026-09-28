from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.analytics.schemas import SkillAssessments
from src.core.profiles.schemas import RegisteredProfile
from src.core.snapshots.schemas import Snapshot, SnapshotUploadReceipt
from src.infra.storages.postgres.models import (
    AnalyticsHeadModel,
    AnalyticsProjectionModel,
    PetModel,
    ProfileModel,
    RewardModel,
    SkillAssessmentModel,
    SnapshotHeadModel,
    SnapshotUploadModel,
)


@dataclass(kw_only=True, slots=True)
class PostgresHelper:
    session: AsyncSession

    async def get_pet(self, *, pet_id: UUID) -> PetModel | None:
        return await self.session.scalar(select(PetModel).where(PetModel.id == pet_id))

    async def insert_profile(self, *, profile: RegisteredProfile) -> None:
        await self.session.merge(ProfileModel.from_domain(profile=profile))
        await self.session.flush()

    async def get_profile(self, *, profile_id: UUID) -> ProfileModel | None:
        return await self.session.scalar(
            select(ProfileModel).where(ProfileModel.profile_id == profile_id)
        )

    async def insert_snapshot(self, *, snapshot: Snapshot) -> None:
        await self.session.merge(SnapshotHeadModel.from_domain(snapshot=snapshot))
        await self.session.flush()

    async def get_snapshot_head(self, *, profile_id: UUID) -> SnapshotHeadModel | None:
        return await self.session.scalar(
            select(SnapshotHeadModel)
            .where(SnapshotHeadModel.profile_id == profile_id)
            .execution_options(populate_existing=True),
        )

    async def insert_snapshot_upload(self, *, upload: SnapshotUploadReceipt) -> None:
        await self.session.merge(SnapshotUploadModel.from_domain(upload=upload))
        await self.session.flush()

    async def get_snapshot_upload(
        self,
        *,
        profile_id: UUID,
        upload_id: str,
    ) -> SnapshotUploadModel | None:
        return await self.session.scalar(
            select(SnapshotUploadModel)
            .where(
                SnapshotUploadModel.profile_id == profile_id,
                SnapshotUploadModel.upload_id == upload_id,
            )
            .execution_options(populate_existing=True),
        )

    async def get_analytics_head(
        self, *, profile_id: UUID, game_run_id: str
    ) -> AnalyticsHeadModel | None:
        return await self.session.scalar(
            select(AnalyticsHeadModel).where(
                AnalyticsHeadModel.profile_id == profile_id,
                AnalyticsHeadModel.game_run_id == game_run_id,
            )
        )

    async def get_analytics_projections(
        self, *, profile_id: UUID, game_run_id: str
    ) -> list[AnalyticsProjectionModel]:
        models = await self.session.scalars(
            select(AnalyticsProjectionModel).where(
                AnalyticsProjectionModel.profile_id == profile_id,
                AnalyticsProjectionModel.game_run_id == game_run_id,
            )
        )
        return list(models.all())

    async def insert_skill_assessment(
        self, *, profile_id: UUID, assessment: SkillAssessments
    ) -> None:
        await self.session.merge(
            SkillAssessmentModel.from_domain(profile_id=profile_id, assessment=assessment)
        )
        await self.session.flush()

    async def get_reward(self, *, reward_id: UUID) -> RewardModel | None:
        return await self.session.scalar(
            select(RewardModel).where(RewardModel.reward_id == reward_id)
        )
