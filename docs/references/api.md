# Reference: FastAPI boundary

## Composition и routes

[create_app()](../../src/infra/api/app.py) создаёт FastAPI с именем и версией из settings,
общим обработчиком ошибок и переданным lifespan. Подключает CORS, единственный `root_router`
и контейнер Dishka. Feature-router подключается через [routers.py](../../src/infra/api/routers.py).

```python
from fastapi import APIRouter

from src.infra.api.common import endpoints as common

root_router = APIRouter()
root_router.include_router(router=common.router, include_in_schema=False)
```

## Health

Живой [endpoint](../../src/infra/api/common/endpoints.py):

```python
from fastapi import APIRouter, Response, status

router = APIRouter(prefix="", tags=["default"])


@router.get(path="/health")
async def health() -> Response:
    return Response(status_code=status.HTTP_200_OK)
```

`GET /health` не требует авторизации и не обращается к use case или внешним сервисам.
Ответ — HTTP 200 с пустым телом. `include_in_schema=False` скрывает его из OpenAPI.
Стандартные `/docs`, `/redoc` и `/openapi.json` доступны через FastAPI.

## Error mapping

[exceptions.py](../../src/infra/api/exceptions.py) регистрирует только общий HTTP 500 handler:
ответ `{"detail": "INTERNAL SERVER ERROR"}`. Domain exceptions и их 4xx registry пока отсутствуют.

Контракт HTTP проверяют [TestHealthAPI](../../src/tests/api/test_health.py) и
[APIHelper](../../src/tests/helpers/api.py); подробности — [API tests](testing_api.md).

## REUSABLE PATTERN: Entity endpoint

`/api/entities` ниже — только переносимый placeholder, не маршрут текущего проекта.

```python
router = APIRouter(prefix="/api/entities", tags=["entities"], route_class=DishkaRoute)


@router.get(path="/{entity_id}", status_code=status.HTTP_200_OK)
async def get_entity(
    entity_id: int,
    _: AuthenticatedPrincipalDeps,
    use_case: FromDishka[GetEntityUseCase],
) -> EntityResponse:
    entity = await use_case.execute(entity_id=entity_id)
    return EntityResponse.from_domain(entity=entity)
```

`AuthenticatedPrincipalDeps`, `GetEntityUseCase`, `EntityResponse` и `DishkaRoute` в примере
не подключены к текущему API. При добавлении бизнес-endpoint нужно согласовать router prefix,
auth-контракт, именованные аргументы use case, response conversion и HTTP-тест.
Паттерн identity описан в [server_generated_value.md](server_generated_value.md).
