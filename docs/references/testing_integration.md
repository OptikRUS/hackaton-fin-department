# Reference: integration tests

## Статус в проекте

Database fixtures, миграции и storage tests отсутствуют. Общая действующая инфраструктура — [Tests](tests.md).

Ниже приведён паттерн для будущего расширения, а не существующие классы, пути
или обязательство добавить подсистему. Imports могут
быть опущены; вспомогательные типы и методы нужно определить под выбранный контракт.
`Entity*` в разных документах показывает роли, а не единую готовую модель проекта.

## REUSABLE PATTERN: Entity round trip

```python
async def test_returns_entity(self) -> None:
    await self.postgres_helper.insert_entity(entity=self.factory.entity(entity_id=1))

    result = await self.storage.get_by_id(entity_id=1)

    assert result == self.factory.entity(entity_id=1)
```

Метод примера размещается в `class Test*` с необходимыми mixins. Для реальной проверки
нужны отдельная тестовая БД, migration fixture, cleanup и согласованные factory/helper methods.
Mock client не считается доказательством интеграции с БД.
