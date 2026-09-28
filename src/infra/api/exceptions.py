from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Request, status
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response

from src.core.analytics.enums import FactDetailType
from src.core.analytics.exceptions import (
    AnalyticsFactConflictError,
    AnalyticsGameRunNotRegisteredError,
    AnalyticsIdempotencyConflictError,
    AnalyticsStaleError,
    AssessmentNotReadyError,
    InvalidAnalyticsError,
    InvalidAnalyticsRequestError,
    UnsupportedAnalyticsSchemaError,
)
from src.core.exceptions import BaseExceptionError
from src.core.profiles.exceptions import (
    InvalidRegistrationError,
    ProfileConflictError,
    RegistrationIdempotencyConflictError,
)
from src.core.rewards.exceptions import (
    GameRunConflictError,
    GameRunNotRegisteredError,
    InvalidRewardCursorError,
    InvalidRewardError,
    InvalidRewardReceiptError,
    InvalidRewardRequestError,
    ParentAccessDeniedError,
    ProfileAccessDeniedError,
    RewardIdempotencyConflictError,
    RewardReceiptConflictError,
    UnknownAccessoryError,
)
from src.core.snapshots.exceptions import (
    InvalidSnapshotError,
    InvalidSnapshotRequestError,
    SnapshotGameRunConflictError,
    SnapshotIdempotencyConflictError,
    SnapshotNotFoundError,
    SnapshotRevisionConflictError,
)

type ExceptionHandler = Callable[[Request, Any], Coroutine[Any, Any, Response]]
type ExceptionHandlers = dict[int | type[Exception], ExceptionHandler]


async def internal_server_error_exception_handler(_: Request, _exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "INTERNAL SERVER ERROR"},
    )


def domain_exception_handler(status_code: int) -> ExceptionHandler:
    async def handler(_: Request, exc: BaseExceptionError) -> JSONResponse:
        return JSONResponse(status_code=status_code, content={"code": exc.detail})

    return handler


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> Response:
    if request.url.path.startswith("/v1/") or request.url.path == "/api/pets":
        unsupported_schema = any(
            (error["type"] == "literal_error" and error["loc"][-1] == "schemaVersion")
            or (error["type"] in {"literal_error", "enum"} and isinstance(error.get("input"), str))
            or (
                error["loc"][-1:] == ("detail",)
                and isinstance(error.get("input"), dict)
                and isinstance(error["input"].get("_type"), str)
                and error["input"].get("_type") not in FactDetailType
            )
            for error in exc.errors()
        )
        return JSONResponse(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_CONTENT
                if unsupported_schema
                else status.HTTP_400_BAD_REQUEST
            ),
            content={"code": "UNSUPPORTED_SCHEMA" if unsupported_schema else "INVALID_REQUEST"},
        )
    return await request_validation_exception_handler(request, exc)


exception_handlers: ExceptionHandlers = {
    status.HTTP_500_INTERNAL_SERVER_ERROR: internal_server_error_exception_handler,
    BaseExceptionError: internal_server_error_exception_handler,
    InvalidRegistrationError: domain_exception_handler(status.HTTP_400_BAD_REQUEST),
    ProfileConflictError: domain_exception_handler(status.HTTP_409_CONFLICT),
    RegistrationIdempotencyConflictError: domain_exception_handler(status.HTTP_409_CONFLICT),
    InvalidSnapshotRequestError: domain_exception_handler(status.HTTP_400_BAD_REQUEST),
    SnapshotNotFoundError: domain_exception_handler(status.HTTP_404_NOT_FOUND),
    SnapshotRevisionConflictError: domain_exception_handler(status.HTTP_409_CONFLICT),
    SnapshotGameRunConflictError: domain_exception_handler(status.HTTP_409_CONFLICT),
    SnapshotIdempotencyConflictError: domain_exception_handler(status.HTTP_409_CONFLICT),
    InvalidSnapshotError: domain_exception_handler(status.HTTP_422_UNPROCESSABLE_CONTENT),
    InvalidAnalyticsRequestError: domain_exception_handler(status.HTTP_400_BAD_REQUEST),
    UnsupportedAnalyticsSchemaError: domain_exception_handler(
        status.HTTP_422_UNPROCESSABLE_CONTENT
    ),
    InvalidAnalyticsError: domain_exception_handler(status.HTTP_422_UNPROCESSABLE_CONTENT),
    AnalyticsIdempotencyConflictError: domain_exception_handler(status.HTTP_409_CONFLICT),
    AnalyticsFactConflictError: domain_exception_handler(status.HTTP_409_CONFLICT),
    AnalyticsStaleError: domain_exception_handler(status.HTTP_409_CONFLICT),
    AssessmentNotReadyError: domain_exception_handler(status.HTTP_409_CONFLICT),
    AnalyticsGameRunNotRegisteredError: domain_exception_handler(status.HTTP_409_CONFLICT),
    ParentAccessDeniedError: domain_exception_handler(status.HTTP_403_FORBIDDEN),
    ProfileAccessDeniedError: domain_exception_handler(status.HTTP_403_FORBIDDEN),
    GameRunNotRegisteredError: domain_exception_handler(status.HTTP_409_CONFLICT),
    GameRunConflictError: domain_exception_handler(status.HTTP_409_CONFLICT),
    RewardIdempotencyConflictError: domain_exception_handler(status.HTTP_409_CONFLICT),
    RewardReceiptConflictError: domain_exception_handler(status.HTTP_409_CONFLICT),
    InvalidRewardRequestError: domain_exception_handler(status.HTTP_400_BAD_REQUEST),
    InvalidRewardError: domain_exception_handler(status.HTTP_422_UNPROCESSABLE_CONTENT),
    UnknownAccessoryError: domain_exception_handler(status.HTTP_422_UNPROCESSABLE_CONTENT),
    InvalidRewardCursorError: domain_exception_handler(status.HTTP_422_UNPROCESSABLE_CONTENT),
    InvalidRewardReceiptError: domain_exception_handler(status.HTTP_422_UNPROCESSABLE_CONTENT),
    RequestValidationError: validation_exception_handler,
}
