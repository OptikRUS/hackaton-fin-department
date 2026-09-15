# Reference: Storages

## Статус в проекте

PostgreSQL, ClickHouse, ORM models, storage ports и transaction providers отсутствуют.

Ниже приведён паттерн для будущего расширения, а не существующие классы, пути
или обязательство добавить подсистему. Imports могут
быть опущены; вспомогательные типы и методы нужно определить под выбранный контракт.
`Entity*` в разных документах показывает роли, а не единую готовую модель проекта.

## REUSABLE PATTERN: Entity storage

```python
@dataclass
class PostgresEntityStorage(EntityStorage):
    session: AsyncSession

    async def get_by_id(self, *, entity_id: int) -> Entity:
        model = await self.session.scalar(
            select(EntityModel).where(EntityModel.id == entity_id),
        )
        if model is None:
            raise EntityNotFoundError
        return model.to_domain()
```

Storage возвращает domain object и не оркестрирует бизнес-операции. В этом паттерне
commit/rollback принадлежат request-scoped session provider; его ещё нужно реализовать.
Проверка с реальной БД описана в [Integration tests](testing_integration.md).
