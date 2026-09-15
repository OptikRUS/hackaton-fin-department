# Reference: Dishka DI и lifecycle

## Production composition root

[create_container()](../../src/di/container.py):

```python
from dishka import AsyncContainer, make_async_container
from dishka.integrations.fastapi import FastapiProvider

from src.di.providers.general import GeneralProvider


def create_container() -> AsyncContainer:
    return make_async_container(
        FastapiProvider(),
        GeneralProvider(),
    )
```

[create_app()](../../src/infra/api/app.py) создаёт контейнер и подключает его к FastAPI.
`FastapiProvider` обеспечивает интеграцию; [GeneralProvider](../../src/di/providers/general.py)
поставляет UUID и timezone-aware UTC datetime в `Scope.REQUEST`:

```python
from datetime import UTC, datetime
from uuid import UUID, uuid4

from dishka import Provider, Scope, provide


class GeneralProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def get_uuid(self) -> UUID:
        return uuid4()

    @provide(scope=Scope.REQUEST)
    def get_current_datetime(self) -> datetime:
        return datetime.now(tz=UTC)
```

Контейнер закрывается в [lifespan](../../src/main.py). Внешних resource providers нет.
`/health` не запрашивает UUID/datetime и не имеет DI-зависимостей.

## Test lifecycle

[app fixture](../../src/tests/conftest.py) вызывает `create_app(lifespan=lifespan)` и входит в
`app.router.lifespan_context(app)`. Тест использует тот же production container; подмены через
`setup_dishka`, mock providers и отдельной container fixture нет. Завершение fixture закрывает
контейнер. Общая структура — [Tests](tests.md).

## REUSABLE PATTERN: provider binding

```python
class EntityProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def get_create_entity_use_case(self, storage: EntityStorage) -> CreateEntityUseCase:
        return CreateEntityUseCase(entity_storage=storage)
```

Это role example. Имя provider, constructor arguments и scope подтверждаются composition root и
resource lifecycle целевого проекта до применения.

`EntityProvider` и его domain types пока отсутствуют; применять этот пример нужно только вместе
с реальным потребителем use case и регистрацией provider в `create_container()`.
