# Reference: Services and adapters

## Статус в проекте

Core service ports, внешние клиенты и library adapters отсутствуют.

Ниже приведён паттерн для будущего расширения, а не существующие классы, пути
или обязательство добавить подсистему. Imports могут
быть опущены; вспомогательные типы и методы нужно определить под выбранный контракт.
`Entity*` в разных документах показывает роли, а не единую готовую модель проекта.

## REUSABLE PATTERN: Entity service

```python
class EntityService(metaclass=ABCMeta):
    @abstractmethod
    async def publish(self, *, entity: Entity) -> None:
        raise NotImplementedError


@dataclass(kw_only=True)
class ExternalEntityService(EntityService):
    client: ExternalEntityClient

    async def publish(self, *, entity: Entity) -> None:
        await self.client.publish(
            request=PublishEntityRequest.from_domain(entity=entity),
        )
```

Отдельный service нужен, когда core use case должен зависеть от стабильного domain port, а wire
client остаётся infrastructure detail. Если библиотека уже естественно реализует port и не требует
адаптации, дополнительный слой не добавляет пользы.
