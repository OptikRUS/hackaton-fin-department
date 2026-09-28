from src.core.exceptions import BaseExceptionError


class InvalidAnalyticsRequestError(BaseExceptionError):
    detail: str = "INVALID_REQUEST"


class InvalidAnalyticsError(BaseExceptionError):
    detail: str = "INVALID_ANALYTICS"


class UnsupportedAnalyticsSchemaError(BaseExceptionError):
    detail: str = "UNSUPPORTED_SCHEMA"


class AnalyticsIdempotencyConflictError(BaseExceptionError):
    detail: str = "IDEMPOTENCY_CONFLICT"


class AnalyticsFactConflictError(BaseExceptionError):
    detail: str = "FACT_CONFLICT"


class AnalyticsStaleError(BaseExceptionError):
    detail: str = "STALE_ANALYTICS"


class AssessmentNotReadyError(BaseExceptionError):
    detail: str = "ASSESSMENT_NOT_READY"


class AnalyticsGameRunNotRegisteredError(BaseExceptionError):
    detail: str = "GAME_RUN_NOT_REGISTERED"
