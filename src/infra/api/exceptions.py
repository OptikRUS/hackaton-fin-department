from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Request, status
from fastapi.responses import JSONResponse, Response

type ExceptionHandler = Callable[[Request, Any], Coroutine[Any, Any, Response]]
type ExceptionHandlers = dict[int | type[Exception], ExceptionHandler]


async def internal_server_error_exception_handler(_: Request, _exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "INTERNAL SERVER ERROR"},
    )


exception_handlers: ExceptionHandlers = {
    status.HTTP_500_INTERNAL_SERVER_ERROR: internal_server_error_exception_handler,
}
