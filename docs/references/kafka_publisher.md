# Reference: Kafka publisher

## Статус в проекте

Kafka не подключена: ни consumer, ни publisher, ни broker lifecycle в каркасе нет.

Ниже приведён паттерн для будущего расширения, а не существующие классы, пути
или обязательство добавить подсистему. Imports могут
быть опущены; вспомогательные типы и методы нужно определить под выбранный контракт.
`Entity*` в разных документах показывает роли, а не единую готовую модель проекта.

## REUSABLE PATTERN: Entity event publisher

`Entity*`, topic, Kafka key, event fields, exception detail и provider binding — placeholders. Перед
адаптацией их нужно заменить подтверждёнными domain names и literal wire contract целевого
проекта. Полная цепочка:

```text
EntityEventDispatcher / EntityEventPublicationError
  → EntityEventMessage.from_domain()
  → entity_events_publisher = router.publisher(...)
  → KafkaEntityEventDispatcher
  → EventDispatchersProvider
  → TestKafkaBroker success/error tests
```

### Core port and error

Core знает только domain event и ошибку port. Он не импортирует FastStream или `KafkaError`.

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class EntityEvent:
    event_id: str
    entity_id: str
    occurred_at: str


class EntityEventPublicationError(BaseExceptionError):
    detail: str = "ENTITY_EVENT_PUBLICATION_ERROR"


class EntityEventDispatcher(metaclass=ABCMeta):
    @abstractmethod
    async def publish_entity_event(self, *, event: EntityEvent) -> None:
        raise NotImplementedError
```

### Boundary schema

Transport serialization остаётся в `infra/api_kafka`. Пример предполагает ещё не реализованный `BoundaryModel` с camelCase serialization.

```python
class EntityEventMessage(BoundaryModel):
    event_id: str
    entity_id: str
    occurred_at: str

    @classmethod
    def from_domain(cls, *, event: EntityEvent) -> Self:
        return cls(
            event_id=event.event_id,
            entity_id=event.entity_id,
            occurred_at=event.occurred_at,
        )
```

### Publisher router and additive broker inclusion

Schema передаётся в `router.publisher()`; dispatcher не собирает raw dict. Topic и key —
часть literal producer/consumer contract, поэтому `target-service.entities` и `event.entity_id` нельзя
копировать без проверки consumer. Новый publisher router подключается **дополнительно**: все уже
зарегистрированные subscriber/publisher routers целевого проекта остаются в `create_broker()` в
исходном порядке. В примере `existing_subscriber_router` обозначает возможный subscriber будущей системы;
в текущем проекте его нет. `entity_events_publisher_router` — router нового publisher module.

```python
entity_events_publisher_router = KafkaRouter()

entity_events_publisher = entity_events_publisher_router.publisher(
    topic="target-service.entities",
    schema=EntityEventMessage,
)


def create_broker() -> KafkaBroker:
    kafka_broker = KafkaBroker(bootstrap_servers=settings.KAFKA.BOOTSTRAP_SERVER)
    kafka_broker.include_router(existing_subscriber_router)
    kafka_broker.include_router(entity_events_publisher_router)
    return kafka_broker
```

Если в целевом проекте уже подключено несколько routers, сохраняются все эти вызовы
`include_router(...)`, а новый publisher router добавляется рядом с ними. Нельзя заменять им
существующий broker topology.

### Dispatcher and narrow SDK error mapping

Adapter создаёт boundary model, передаёт literal key и переводит только ожидаемую
Kafka library family в domain error. Ошибки программирования не маскируются через
широкий `except Exception`.

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class KafkaEntityEventDispatcher(EntityEventDispatcher):
    publisher: DefaultPublisher

    async def publish_entity_event(self, *, event: EntityEvent) -> None:
        try:
            await self.publisher.publish(
                message=EntityEventMessage.from_domain(event=event),
                key=event.entity_id,
            )
        except KafkaError as error:
            raise EntityEventPublicationError from error
```

### DI binding

```python
class EventDispatchersProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def get_entity_event_dispatcher(self) -> EntityEventDispatcher:
        return KafkaEntityEventDispatcher(publisher=entity_events_publisher)
```

Provider регистрируется в production container только вместе с фактическим consumer этого port.
Узкий provider не создаёт новый broker и не дублирует publisher.

### Project-native TestKafkaBroker success and error tests

Для подключения этого паттерна потребуется общая broker fixture с `create_broker()`,
Dishka/FastStream wiring, `TestKafkaBroker` и `TestApp`. `KafkaFixture`, `FactoryFixture`,
KafkaHelper и методы ниже пока отсутствуют. Если к моменту добавления publisher общая fixture
уже появится, её следует переиспользовать, сохранив существующие routers. Imports и SDK error
types нужно проверить по выбранной версии библиотеки перед реализацией.

```python
class TestKafkaEntityEventDispatcher(FactoryFixture, KafkaFixture):
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.event_dispatcher = KafkaEntityEventDispatcher(publisher=entity_events_publisher)
        self.kafka.reset_mock(called=entity_events_publisher)

    async def test_publishes_literal_message(self) -> None:
        await self.event_dispatcher.publish_entity_event(
            event=self.factory.entity_event(
                event_id="event-9",
                entity_id="entity-7",
                occurred_at="2026-08-25T12:00:00.000Z",
            ),
        )

        self.kafka.assert_called_once_with(
            called=entity_events_publisher,
            message={
                "eventId": "event-9",
                "entityId": "entity-7",
                "occurredAt": "2026-08-25T12:00:00.000Z",
            },
        )
        self.kafka.assert_called_once(called=entity_events_publisher)
        assert entity_events_publisher.topic == "target-service.entities"

    async def test_maps_kafka_error(self) -> None:
        entity_events_publisher.mock.side_effect = KafkaUnavailableError

        with pytest.raises(EntityEventPublicationError):
            await self.event_dispatcher.publish_entity_event(
                event=self.factory.entity_event(
                    event_id="event-9",
                    entity_id="entity-7",
                    occurred_at="2026-08-25T12:00:00.000Z",
                ),
            )

        self.kafka.assert_called_once(called=entity_events_publisher)
```

Broker-backed assertion фиксирует decoded payload и topic через реальный для теста
`entity_events_publisher`. Нельзя подменять проверяемый publisher на `AsyncMock(spec=DefaultPublisher)`
и выдавать это за publisher test. Если Kafka key требует отдельного runtime-доказательства, сначала
подтверждается project-native способ наблюдать raw record или producer command; такой тест не
изобретается внутри адаптации этого шаблона.

При применении этого шаблона нужно одновременно подтвердить core event, topic, key,
wire fields and aliases, error detail, аддитивное broker router inclusion, сохранение существующего
Dishka/FastStream test wiring, DI registration, producer/consumer coupling и literal transport test.
Нельзя добавлять только `router.publisher()` без остальной цепочки.
