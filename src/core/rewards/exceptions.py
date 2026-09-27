from src.core.exceptions import BaseExceptionError


class ParentAccessDeniedError(BaseExceptionError):
    detail = "PARENT_ACCESS_DENIED"


class ProfileAccessDeniedError(BaseExceptionError):
    detail = "PROFILE_ACCESS_DENIED"


class GameRunNotRegisteredError(BaseExceptionError):
    detail = "GAME_RUN_NOT_REGISTERED"


class GameRunConflictError(BaseExceptionError):
    detail = "GAME_RUN_CONFLICT"


class RewardIdempotencyConflictError(BaseExceptionError):
    detail = "IDEMPOTENCY_CONFLICT"


class RewardReceiptConflictError(BaseExceptionError):
    detail = "REWARD_RECEIPT_CONFLICT"


class InvalidRewardError(BaseExceptionError):
    detail = "INVALID_REWARD"


class UnknownAccessoryError(BaseExceptionError):
    detail = "UNKNOWN_ACCESSORY"


class InvalidRewardCursorError(BaseExceptionError):
    detail = "INVALID_REWARD_CURSOR"


class InvalidRewardReceiptError(BaseExceptionError):
    detail = "INVALID_REWARD_RECEIPT"


class InvalidRewardRequestError(BaseExceptionError):
    detail = "INVALID_REQUEST"
