# Reference: API tests

Общие ресурсы описаны в [Tests](tests.md). Тест вызывает реальное приложение через
`httpx2.AsyncClient` и `ASGITransport`; авторизация и use-case doubles не нужны для `/health`.

## Живой HTTP-контракт

[test_health.py](../../src/tests/api/test_health.py):

```python
from httpx2 import codes

from src.tests.fixtures import APIFixture


class TestHealthAPI(APIFixture):
    async def test_health_returns_ok(self) -> None:
        response = await self.api.get_health()

        assert response.is_success
        assert response.status_code == codes.OK
        assert response.content == b""
```

[APIHelper](../../src/tests/helpers/api.py):

```python
from dataclasses import dataclass

from httpx2 import AsyncClient, Response


@dataclass(kw_only=True, slots=True)
class APIHelper:
    client: AsyncClient

    async def get_health(self) -> Response:
        return await self.client.get(url="/health")
```

Запуск из корня:

```bash
uv run pytest -vv -x src/tests/api/test_health.py::TestHealthAPI::test_health_returns_ok
```

Проверяются HTTP 200 и пустое тело без Authorization. Клиент берётся через `APIFixture`.
Для будущего бизнес-endpoint проверка boundary должна фиксировать wire JSON, точный вызов
use case и собственный error mapping. Framework-generated 422 достаточно проверять по status
и отсутствию downstream-вызова; его внутренний Pydantic detail не следует фиксировать.

## REUSABLE PATTERN: Entity API

```python
class TestGetEntityAPI(APIFixture, ContainerFixture, FactoryFixture):
    @pytest.fixture(autouse=True)
    async def setup(self) -> None:
        self.use_case = await self.container_helper.override_use_case(
            use_case_type=GetEntityUseCase,
        )

    async def test_returns_entity(self) -> None:
        self.use_case.execute.return_value = self.factory.entity(entity_id=1)

        response = await self.api.get_entity(entity_id=1)

        assert response.status_code == codes.OK
        assert response.json() == {"id": 1, "name": "Первая сущность"}
        self.use_case.execute.assert_awaited_once_with(entity_id=1)
```

`get_entity()` и response fields адаптируются к реальному route/wire contract; это не текущий API.

`ContainerFixture`, `FactoryFixture`, `GetEntityUseCase` и `get_entity()` — только роли примера.
Их нет в каркасе; вводить их нужно вместе с соответствующим бизнес-контрактом.
