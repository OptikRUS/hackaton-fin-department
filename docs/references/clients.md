# Reference: External HTTP clients

## Статус в проекте

httpx2 используется в [API-тестах](testing_api.md). Production BaseClient, external settings и client providers отсутствуют.

Ниже приведён паттерн для будущего расширения, а не существующие классы, пути
или обязательство добавить подсистему. Imports могут
быть опущены; вспомогательные типы и методы нужно определить под выбранный контракт.
`Entity*` в разных документах показывает роли, а не единую готовую модель проекта.

## REUSABLE PATTERN: Entity wire operation

```python
class PublishEntityRequest(BoundaryModel):
    id: int
    name: str

    @classmethod
    def from_domain(cls, *, entity: Entity) -> Self:
        return cls(id=entity.id, name=entity.name)


class ExternalEntityClient(BaseClient):
    service_url = settings.EXTERNAL_SERVICE.HOST

    async def publish(self, *, request: PublishEntityRequest) -> None:
        await self.post(url="/internal/entities", json=request.to_dict())
```

`BaseClient`, `BoundaryModel`, `settings.EXTERNAL_SERVICE`, `/internal/entities` не существуют
в текущем проекте. Перед реализацией определить timeout, HTTP error mapping, wire payload
и DI lifecycle с закрытием клиента. HTTP-контракт проверять transport double.
