# Reference: Redis adapter

## Статус в проекте

Redis dependency, runtime consumer, cache port и production provider отсутствуют.

Ниже сохранён переносимый паттерн из исходного набора references. Это пример для будущего
расширения, а не существующие классы, пути или обязательство добавить подсистему. Imports могут
быть опущены; вспомогательные типы и методы нужно определить под выбранный контракт.
`Entity*` в разных документах показывает роли, а не единую готовую модель проекта.

## REUSABLE PATTERN: Entity cache

### Полная цепочка

`EntityCache` port → `RedisEntityCache` adapter → DI lifecycle → integration test.

### Core port

```python
class EntityCacheUnavailableError(BaseExceptionError):
    detail: str = "ENTITY_CACHE_UNAVAILABLE"


class EntityCacheDataError(BaseExceptionError):
    detail: str = "ENTITY_CACHE_DATA_ERROR"
```

```python
class EntityCache(metaclass=ABCMeta):
    @abstractmethod
    async def get(self, *, entity_id: int) -> Entity | None:
        raise NotImplementedError

    @abstractmethod
    async def put(self, *, entity: Entity, ttl_seconds: int) -> None:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, *, entity_id: int) -> None:
        raise NotImplementedError
```

Cache port не скрывает domain not-found semantics: `None` означает cache miss, а не domain error.

### Adapter responsibilities

Cache payload является infrastructure schema и не добавляет serialization methods в domain
dataclass:

```python
class EntityCachePayload(BaseModel):
    id: int
    name: str
    description: str
    status: EntityStatusEnum
    amount: Decimal

    @classmethod
    def from_domain(cls, *, entity: Entity) -> "EntityCachePayload":
        return cls(
            id=entity.id,
            name=entity.name,
            description=entity.description,
            status=entity.status,
            amount=entity.amount,
        )

    def to_domain(self) -> Entity:
        return Entity(**self.model_dump())
```

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class RedisEntityCache(EntityCache):
    client: Redis
    key_prefix: str

    async def get(self, *, entity_id: int) -> Entity | None:
        try:
            payload = await self.client.get(f"{self.key_prefix}:{entity_id}")
        except RedisError as error:
            raise EntityCacheUnavailableError from error
        if payload is None:
            return None
        try:
            return EntityCachePayload.model_validate_json(payload).to_domain()
        except ValidationError as error:
            raise EntityCacheDataError from error

    async def put(self, *, entity: Entity, ttl_seconds: int) -> None:
        try:
            await self.client.set(
                f"{self.key_prefix}:{entity.id}",
                EntityCachePayload.from_domain(entity=entity).model_dump_json(),
                ex=ttl_seconds,
            )
        except RedisError as error:
            raise EntityCacheUnavailableError from error

    async def delete(self, *, entity_id: int) -> None:
        try:
            await self.client.delete(f"{self.key_prefix}:{entity_id}")
        except RedisError as error:
            raise EntityCacheUnavailableError from error
```

В реальном проекте `EntityCacheUnavailableError`, serialization, key format, TTL и cache failure
policy сначала фиксируются в domain/infrastructure contract. Adapter переводит library error в
ошибку port, но не содержит fallback business orchestration.

### DI lifecycle

```python
class RedisSettings(BaseSettings):
    DSN: SecretStr = SecretStr("redis://localhost:6379/0")

    model_config = SettingsConfigDict(env_prefix="REDIS_")


class RedisProvider(Provider):
    @provide(scope=Scope.APP)
    async def get_redis_client(self) -> AsyncIterator[Redis]:
        client = Redis.from_url(settings.REDIS.DSN.get_secret_value())
        try:
            yield client
        finally:
            await client.aclose()

    @provide(scope=Scope.REQUEST)
    def get_entity_cache(self, client: Redis) -> EntityCache:
        return RedisEntityCache(client=client, key_prefix="entity")
```

Конкретная async Redis library и ping/health policy должны быть подтверждены dependency и живым
кодом до копирования этого примера.

### Integration test

```python
class TestRedisEntityCache(FactoryFixture):
    async def test_round_trip(self, redis_client: Redis) -> None:
        cache = RedisEntityCache(client=redis_client, key_prefix="entity")

        await cache.put(entity=self.factory.entity(entity_id=1), ttl_seconds=60)
        result = await cache.get(entity_id=1)

        assert result == self.factory.entity(entity_id=1)

    async def test_cache_miss_returns_none(self, redis_client: Redis) -> None:
        cache = RedisEntityCache(client=redis_client, key_prefix="entity")

        assert await cache.get(entity_id=999) is None
```

Error mapping проверяется отдельно от integration round trip:

```python
class TestRedisEntityCacheErrors:
    async def test_maps_client_error(self) -> None:
        client = AsyncMock(spec=Redis)
        client.get.side_effect = RedisError("unavailable")
        cache = RedisEntityCache(client=client, key_prefix="entity")

        with pytest.raises(EntityCacheUnavailableError):
            await cache.get(entity_id=1)

        client.get.assert_awaited_once_with("entity:1")
```

Не выдавать Redis mock за integration test. Для serialization/error mapping допустим отдельный unit
test с strict stub, но он не заменяет проверку реального TTL/key/value contract.
