# Reference: test doubles

## Статус в проекте

Health-тест использует production container и реальный HTTP handler. Mock/fake providers, FactoryFixture и ContainerHelper отсутствуют.

Ниже сохранён переносимый паттерн из исходного набора references. Это пример для будущего
расширения, а не существующие классы, пути или обязательство добавить подсистему. Imports могут
быть опущены; вспомогательные типы и методы нужно определить под выбранный контракт.
`Entity*` в разных документах показывает роли, а не единую готовую модель проекта.

## REUSABLE PATTERN: stateful Entity fake

```python
@dataclass(kw_only=True)
class FakeEntityStorage(EntityStorage):
    entities: dict[int, Entity] = field(default_factory=dict)

    async def get_by_id(self, *, entity_id: int) -> Entity:
        try:
            return self.entities[entity_id]
        except KeyError as error:
            raise EntityNotFoundError from error


entity_storage_fake = FakeEntityStorage()
entity_storage = AsyncMock(spec=EntityStorage, wraps=entity_storage_fake)
```

Fake реализует domain semantics, mock фиксирует interaction, stub возвращает заранее заданное
значение, external API mock моделирует wire boundary. Конкретный double выбирается по проверяемому
контракту, а не ради удобства setup.
