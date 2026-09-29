import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress

import uvicorn
from fastapi import FastAPI

from src.config.settings import settings
from src.infra.api.app import create_app
from src.infra.observability.aggregation import Aggregator
from src.infra.observability.business_metrics import BusinessMetrics


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    container = app.state.dishka_container
    metrics = await container.get(BusinessMetrics)
    aggregator = Aggregator(
        metrics=metrics,
        interval_seconds=settings.AGGREGATION.INTERVAL_SECONDS,
    )
    stop = asyncio.Event()
    aggregation_task = asyncio.create_task(
        aggregator.run_forever(stop),
        name="business-metrics-aggregation",
    )
    try:
        yield
    finally:
        stop.set()
        aggregation_task.cancel()
        with suppress(asyncio.CancelledError):
            await aggregation_task
        await container.close()


def start_service() -> None:
    uvicorn.run(
        app=create_app(lifespan=lifespan),
        host=settings.APP.ADDRESS,
        port=settings.APP.PORT,
        access_log=True,
    )


if __name__ == "__main__":
    start_service()
