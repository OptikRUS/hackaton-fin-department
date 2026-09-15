# Reference: isolated adapter tests

## Статус в проекте

Service/client/library adapters ещё не реализованы. Текущий test suite содержит только [health API test](testing_api.md).

Ниже приведён паттерн для будущего расширения, а не существующие классы, пути
или обязательство добавить подсистему. Imports могут
быть опущены; вспомогательные типы и методы нужно определить под выбранный контракт.
`Entity*` в разных документах показывает роли, а не единую готовую модель проекта.

## REUSABLE PATTERN: Entity adapter

```python
class TestExternalEntityService(FactoryFixture):
    async def test_publishes_wire_request(self) -> None:
        client = AsyncMock(spec=ExternalEntityClient)
        service = ExternalEntityService(client=client)

        await service.publish(entity=self.factory.entity(entity_id=1))

        client.publish.assert_awaited_once_with(
            request=PublishEntityRequest.from_domain(entity=self.factory.entity(entity_id=1)),
        )
```

AsyncMock проверяет узкую adapter delegation boundary. Для literal HTTP wire contract
нужен transport double; mock не доказывает доступность реального внешнего сервиса.
