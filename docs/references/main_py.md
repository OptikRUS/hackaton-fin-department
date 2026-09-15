# Reference: src/main.py

## Process lifecycle

[main.py](../../src/main.py) связывает FastAPI, Uvicorn и Dishka:

```python
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from src.config.settings import settings
from src.infra.api.app import create_app


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    container = app.state.dishka_container
    yield
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
```

Локальный запуск из корня: `uv run python -m src.main`.
С файлом настроек: `uv run --env-file .env python -m src.main`.
В [Dockerfile](../../Dockerfile) используется `python src/main.py` через uv;
`PYTHONPATH=/project/` обеспечивает импорты `src`.

`create_app()` создаёт контейнер, lifespan закрывает его после завершения обработки запросов.
Миграции и Kafka при старте не запускаются. Тестовая app fixture активирует тот же lifespan;
см. [Tests](tests.md).
