# Reference: Core

## Статус в проекте

В [src/core](../../src/core) только пустой пакет. Domain schemas, ports, exceptions и use cases ещё не реализованы.

Ниже приведён паттерн для будущего расширения, а не существующие классы, пути
или обязательство добавить подсистему. Imports могут
быть опущены; вспомогательные типы и методы нужно определить под выбранный контракт.
`Entity*` в разных документах показывает роли, а не единую готовую модель проекта.

## REUSABLE PATTERN: Entity

Следующий код показывает роли, а не текущие symbols:

```python
class EntityStatusEnum(StrEnum):
    ACTIVE = "active"
    DRAFT = "draft"


@dataclass(frozen=True, slots=True, kw_only=True)
class Entity:
    id: int
    name: str
    status: EntityStatusEnum


@dataclass(frozen=True, slots=True, kw_only=True)
class CreateEntityParams:
    name: str
    status: EntityStatusEnum


class EntityStorage(metaclass=ABCMeta):
    @abstractmethod
    async def create(self, *, params: CreateEntityParams) -> Entity:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, *, entity_id: int) -> Entity:
        raise NotImplementedError


@dataclass(frozen=True, slots=True, kw_only=True)
class CreateEntityUseCase(UseCase):
    entity_storage: EntityStorage

    async def execute(self, *, params: CreateEntityParams) -> Entity:
        return await self.entity_storage.create(params=params)
```

Core остаётся независимым от FastAPI, HTTP, ORM и DI. `UseCase` в примере также не реализован;
выбранный домен определяет реальные имена, сигнатуры и ошибки.
