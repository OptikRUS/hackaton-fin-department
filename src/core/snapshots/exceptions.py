from src.core.exceptions import BaseExceptionError


class InvalidSnapshotError(BaseExceptionError):
    detail: str = "SNAPSHOT_INVALID"


class InvalidSnapshotRequestError(BaseExceptionError):
    detail: str = "INVALID_REQUEST"


class SnapshotNotFoundError(BaseExceptionError):
    detail: str = "SNAPSHOT_NOT_FOUND"


class SnapshotRevisionConflictError(BaseExceptionError):
    detail: str = "SNAPSHOT_REVISION_CONFLICT"


class SnapshotGameRunConflictError(BaseExceptionError):
    detail: str = "GAME_RUN_CONFLICT"


class SnapshotIdempotencyConflictError(BaseExceptionError):
    detail: str = "IDEMPOTENCY_CONFLICT"
