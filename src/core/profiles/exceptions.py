from src.core.exceptions import BaseExceptionError


class InvalidRegistrationError(BaseExceptionError):
    detail: str = "INVALID_REQUEST"


class ProfileConflictError(BaseExceptionError):
    detail: str = "PROFILE_CONFLICT"


class RegistrationIdempotencyConflictError(BaseExceptionError):
    detail: str = "IDEMPOTENCY_CONFLICT"
