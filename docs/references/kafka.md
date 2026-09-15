# Reference: Kafka transport

## Статус в проекте

Kafka/FastStream отсутствуют в зависимостях. Broker, consumer, topics, schemas и Kafka-тесты не созданы.

Ниже сохранён переносимый паттерн из исходного набора references. Это пример для будущего
расширения, а не существующие классы, пути или обязательство добавить подсистему. Imports могут
быть опущены; вспомогательные типы и методы нужно определить под выбранный контракт.
`Entity*` в разных документах показывает роли, а не единую готовую модель проекта.

## REUSABLE PATTERN: Entity event

```python
class EntityMessage(BoundaryModel):
    entity_id: int
    name: str

    def to_domain(self) -> Entity:
        return Entity(id=self.entity_id, name=self.name)


@router.subscriber("entities")
async def entities_handler(
    body: list[EntityMessage],
    use_case: FromDishka[ProcessEntitiesUseCase],
) -> None:
    await use_case.execute(entities=[message.to_domain() for message in body])
```

Batching, topic, group ID, ack policy и exact named arguments сначала согласуются с producer.
Batch-пример требует соответствующей регистрации router; сам по себе handler брокер не создаёт.
В [main.py](main_py.md) пока нет broker lifecycle.
