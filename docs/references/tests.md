# Reference: общая тестовая инфраструктура

## Layout

```text
src/tests/
  __init__.py
  conftest.py
  fixtures.py
  helpers/
    __init__.py
    api.py
  api/
    __init__.py
    test_health.py
```

[conftest.py](../../src/tests/conftest.py) — единственный conftest проекта.
Он управляет реальным приложением и его lifespan, фабрикой HTTP-клиента и клиентом:

```python
from collections.abc import AsyncGenerator, Callable

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx2 import ASGITransport, AsyncClient

from src.infra.api.app import create_app
from src.main import lifespan


@pytest_asyncio.fixture
async def app() -> AsyncGenerator[FastAPI]:
    app = create_app(lifespan=lifespan)
    async with app.router.lifespan_context(app):
        yield app


@pytest.fixture
def api_client_factory(
    app: FastAPI,
) -> Callable[..., AsyncClient]:
    def create_client(*, headers: dict[str, str] | None = None) -> AsyncClient:
        return AsyncClient(
            transport=ASGITransport(app=app, client=("testclient", 50000)),
            base_url="http://testserver",
            headers={"accept-encoding": "gzip, deflate", **(headers or {})},
        )

    return create_client


@pytest_asyncio.fixture
async def client(
    api_client_factory: Callable[..., AsyncClient],
) -> AsyncGenerator[AsyncClient]:
    async with api_client_factory() as client:
        yield client
```

Auth tokens, базы, миграции, test broker и mock DI providers отсутствуют.
`ASGITransport` вызывает приложение в процессе теста, без открытого TCP-порта.
Клиент закрывается через async context manager; завершение app fixture закрывает DI-container.

## Class mixin и helper

[fixtures.py](../../src/tests/fixtures.py):

```python
import pytest_asyncio
from httpx2 import AsyncClient as HTTPAsyncClient

from src.tests.helpers.api import APIHelper


class APIFixture:
    api: APIHelper

    @pytest_asyncio.fixture(autouse=True)
    async def _api_setup(
        self,
        client: HTTPAsyncClient,
    ) -> None:
        self.api = APIHelper(client=client)
```

[APIHelper](../../src/tests/helpers/api.py) хранит URL `/health` и выполняет запрос через
`await client.get(...)`. Единственный test class — `TestHealthAPI(APIFixture)`.
`FactoryFixture`, `ContainerFixture`, `KafkaFixture`, database helpers и role-aware clients
в текущем каркасе отсутствуют.

## Выбор test level

| Контракт | Reference | Статус |
| --- | --- | --- |
| HTTP status/body | [API tests](testing_api.md) | Реализован health-тест |
| SQL и schema | [Integration tests](testing_integration.md) | Будущий паттерн |
| Service/client/library adapter | [Unit tests](testing_unit.md) | Будущий паттерн |
| Fake/mock | [Test doubles](testing_doubles.md) | Будущий паттерн |
| Business behavior | [BDD](bdd.md) | Будущий паттерн |

Не добавлять тесты, которые только сравнивают DI-container или повторяют тривиальные settings.
Shared resources принадлежат conftest, а настройка конкретного SUT — class-local setup fixture.
Результат действия сохраняется локально; ожидаемый HTTP-контракт проверяется явными значениями.
