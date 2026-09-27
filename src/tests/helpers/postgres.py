from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.snapshots.schemas import Snapshot, SnapshotUploadReceipt
from src.infra.storages.postgres.models import PetModel, SnapshotHeadModel, SnapshotUploadModel


@dataclass(kw_only=True, slots=True)
class PostgresHelper:
    session: AsyncSession

    async def get_pet(self, *, pet_id: UUID) -> PetModel | None:
        return await self.session.scalar(select(PetModel).where(PetModel.id == pet_id))

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
