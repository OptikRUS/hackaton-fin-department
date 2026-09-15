# Карта проектных референсов

Референсы HTTP-каркаса `hackaton-fin-department`: навигация по живому коду
и библиотека паттернов для разработки.
Текущие code/config и инструкции пользователя имеют приоритет над примерами.

## Текущая реализация

| Задача | Reference | Живой код / тест |
| --- | --- | --- |
| HTTP endpoint, router, error mapping | [API](api.md) | [API](../../src/infra/api/app.py), [health](../../src/infra/api/common/endpoints.py) |
| Settings и пути | [Config](config.md) | [settings](../../src/config/settings.py), [constants](../../src/config/constants.py) |
| DI и scope | [DI](di.md) | [container](../../src/di/container.py), [GeneralProvider](../../src/di/providers/general.py) |
| Запуск и завершение | [main.py](main_py.md) | [main](../../src/main.py) |
| Общие тестовые ресурсы | [Tests](tests.md) | [conftest](../../src/tests/conftest.py), [fixtures](../../src/tests/fixtures.py) |
| HTTP-контракт | [API tests](testing_api.md) | [TestHealthAPI](../../src/tests/api/test_health.py), [APIHelper](../../src/tests/helpers/api.py) |
| Зависимости и проверки | [Tooling](pyproject.md) | [pyproject](../../pyproject.toml), [Makefile](../../Makefile) |

Единственный прикладной endpoint — `GET /health`: без авторизации, HTTP 200 с пустым телом,
скрыт из OpenAPI. `src/core` пока содержит только пустой пакет.

Имя FastAPI-приложения, пакета в `pyproject.toml` и Compose-сервиса —
`hackaton-fin-department`.

## REUSABLE PATTERN: будущие компоненты

| Задача | Reference | Текущий статус |
| --- | --- | --- |
| Domain schemas, ports, use cases | [Core](core.md) | Бизнес-логика отсутствует |
| Boundary conversion | [Schemas](schemas.md) | Domain/API/client schemas отсутствуют |
| Storage adapters | [Storages](storages.md) | БД и storage-слои не подключены |
| Service adapters | [Services](services.md) | Core service ports и adapters отсутствуют |
| External HTTP clients | [Clients](clients.md) | Production clients отсутствуют |
| Kafka consumer | [Kafka](kafka.md) | Kafka/FastStream не подключены |
| Database migrations | [Migrations](migrations.md) | Alembic и migration layers отсутствуют |
| Real database tests | [Integration tests](testing_integration.md) | Нет database fixtures/tests |
| Isolated adapter tests | [Unit tests](testing_unit.md) | Нет service/client tests |
| Mocks и fakes | [Test doubles](testing_doubles.md) | Health-тест использует реальное приложение |
| Business specifications | [BDD](bdd.md) | Behave и Gherkin-сценарии отсутствуют |
| Redis cache | [Redis](redis.md) | Redis не подключён |
| Kafka publisher | [Kafka publisher](kafka_publisher.md) | Broker/publisher отсутствуют |
| Server-generated identity | [Generated value](server_generated_value.md) | UUID-provider есть, endpoint его не использует |
| Database settings | [PostgresSettings](postgres_settings.md) | `settings.POSTGRES` отсутствует |

До применения будущего паттерна нужно определить конкретный domain/wire contract, зависимости,
DI lifecycle и тестовую границу. Пример не означает наличие соответствующих файлов или команд.
