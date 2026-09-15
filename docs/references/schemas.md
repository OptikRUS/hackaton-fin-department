# Reference: Domain и boundary schemas

## Статус в проекте

`/health` возвращает пустой Response; request/response domain schemas и BoundaryModel отсутствуют. Pydantic Settings применяется только в [config](config.md).

Ниже сохранён переносимый паттерн из исходного набора references. Это пример для будущего
расширения, а не существующие классы, пути или обязательство добавить подсистему. Imports могут
быть опущены; вспомогательные типы и методы нужно определить под выбранный контракт.
`Entity*` в разных документах показывает роли, а не единую готовую модель проекта.

## REUSABLE PATTERN: Entity request/response

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class Entity:
    id: int
    name: str


@dataclass(frozen=True, slots=True, kw_only=True)
class CreateEntityParams:
    name: str


class CreateEntityRequest(BoundaryModel):
    name: str

    def to_domain(self) -> CreateEntityParams:
        return CreateEntityParams(name=self.name)


class EntityResponse(BoundaryModel):
    id: int
    name: str

    @classmethod
    def from_domain(cls, *, entity: Entity) -> Self:
        return cls(id=entity.id, name=entity.name)
```

`BoundaryModel` в примере требует отдельной реализации и решения об aliases/serialization.
Domain dataclasses не должны получать HTTP- или Kafka-serialization ради адаптера.
