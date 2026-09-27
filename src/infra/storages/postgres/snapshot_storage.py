from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.snapshots.schemas import Snapshot, SnapshotHead, SnapshotUploadReceipt
from src.core.snapshots.storages import SnapshotStorage
from src.infra.storages.postgres.models import SnapshotHeadModel, SnapshotUploadModel


@dataclass(kw_only=True, slots=True)
class PostgresSnapshotStorage(SnapshotStorage):
    session: AsyncSession

    async def ensure_head(self, *, profile_id: UUID) -> None:
        await self.session.execute(
            insert(SnapshotHeadModel)
            .values(
                profile_id=profile_id,
                server_revision=0,
                game_run_id="",
                current_content_fingerprint="",
                snapshot_json="",
            )
            .on_conflict_do_nothing(index_elements=[SnapshotHeadModel.profile_id]),
        )

    async def get_head_for_update(self, *, profile_id: UUID) -> SnapshotHead:
        model = (
            await self.session.scalars(
                select(SnapshotHeadModel)
                .where(SnapshotHeadModel.profile_id == profile_id)
                .execution_options(populate_existing=True)
                .with_for_update(),
            )
        ).one()
        return model.to_head()

    async def get_upload(
        self,
        *,
        profile_id: UUID,
        upload_id: str,
    ) -> SnapshotUploadReceipt | None:
        model = await self.session.scalar(
            select(SnapshotUploadModel)
            .where(
                SnapshotUploadModel.profile_id == profile_id,
                SnapshotUploadModel.upload_id == upload_id,
            )
            .execution_options(populate_existing=True),
        )
        return model.to_domain() if model is not None else None

    async def replace_head(self, *, snapshot: Snapshot) -> Snapshot:
        model = (
            await self.session.scalars(
                update(SnapshotHeadModel)
                .where(SnapshotHeadModel.profile_id == snapshot.profile_id)
                .values(
                    server_revision=snapshot.server_revision,
                    game_run_id=snapshot.game_run_id,
                    current_content_fingerprint=snapshot.current_content_fingerprint,
                    snapshot_json=snapshot.snapshot_json,
                )
                .returning(SnapshotHeadModel)
                .execution_options(populate_existing=True),
            )
        ).one()
        return model.to_domain()

    async def insert_upload(self, *, upload: SnapshotUploadReceipt) -> SnapshotUploadReceipt:
        model = (
            await self.session.scalars(
                insert(SnapshotUploadModel)
                .values(
                    profile_id=upload.profile_id,
                    upload_id=upload.result.upload_id,
                    request_digest=upload.request_digest,
                    game_run_id=upload.result.game_run_id,
                    server_revision=upload.result.server_revision,
                    checksum=upload.result.checksum,
                    created=upload.result.created,
                )
                .returning(SnapshotUploadModel),
            )
        ).one()
        return model.to_domain()

    async def get_latest(self, *, profile_id: UUID) -> Snapshot | None:
        model = await self.session.scalar(
            select(SnapshotHeadModel)
            .where(
                SnapshotHeadModel.profile_id == profile_id,
                SnapshotHeadModel.server_revision > 0,
            )
            .execution_options(populate_existing=True),
        )
        return model.to_domain() if model is not None else None
