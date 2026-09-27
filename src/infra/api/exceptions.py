from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Request, status
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response

from src.core.exceptions import BaseExceptionError
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


def snapshot_exception_handler(status_code: int) -> ExceptionHandler:
    async def handler(_: Request, exc: BaseExceptionError) -> JSONResponse:
        return JSONResponse(status_code=status_code, content={"code": exc.detail})

    return handler


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> Response:
    if (
        request.method == "PUT"
        and request.url.path.startswith("/v1/profiles/")
        and request.url.path.endswith("/snapshot")
    ):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"code": "INVALID_REQUEST"},
        )
    return await request_validation_exception_handler(request, exc)


exception_handlers: ExceptionHandlers = {
    status.HTTP_500_INTERNAL_SERVER_ERROR: internal_server_error_exception_handler,
    InvalidSnapshotRequestError: snapshot_exception_handler(status.HTTP_400_BAD_REQUEST),
    SnapshotNotFoundError: snapshot_exception_handler(status.HTTP_404_NOT_FOUND),
    SnapshotRevisionConflictError: snapshot_exception_handler(status.HTTP_409_CONFLICT),
    SnapshotGameRunConflictError: snapshot_exception_handler(status.HTTP_409_CONFLICT),
    SnapshotIdempotencyConflictError: snapshot_exception_handler(status.HTTP_409_CONFLICT),
    InvalidSnapshotError: snapshot_exception_handler(status.HTTP_422_UNPROCESSABLE_CONTENT),
    RequestValidationError: validation_exception_handler,
}
