from abc import ABCMeta, abstractmethod
from uuid import UUID

from src.core.snapshots.schemas import Snapshot, SnapshotHead, SnapshotUploadReceipt


class SnapshotStorage(metaclass=ABCMeta):
    @abstractmethod
    async def ensure_head(self, *, profile_id: UUID) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_head_for_update(self, *, profile_id: UUID) -> SnapshotHead:
        raise NotImplementedError

    @abstractmethod
    async def get_upload(self, *, profile_id: UUID, upload_id: str) -> SnapshotUploadReceipt | None:
        raise NotImplementedError

    @abstractmethod
    async def replace_head(self, *, snapshot: Snapshot) -> Snapshot:
        raise NotImplementedError

    @abstractmethod
    async def insert_upload(self, *, upload: SnapshotUploadReceipt) -> SnapshotUploadReceipt:
        raise NotImplementedError

    @abstractmethod
    async def get_latest(self, *, profile_id: UUID) -> Snapshot | None:
        raise NotImplementedError
