# hackaton-fin-department

HTTP-сервис на Python 3.14, FastAPI, Dishka, SQLAlchemy и PostgreSQL. Версия
приложения — `0.1.0`.

## Локальный запуск

Требуются Python 3.14 и uv.

```bash
uv sync --frozen
uv run python -m src.main
```

По умолчанию приложение слушает `127.0.0.1:8080`. Настройки задаются переменными
окружения `APP_NAME`, `APP_ADDRESS`, `APP_PORT`, `CORS_ALLOW_ORIGINS`,
`CORS_ALLOW_METHODS` и `CORS_ALLOW_HEADERS`. CORS-списки передаются в формате JSON.

Для запуска с настройками из файла:

```bash
cp .env.example .env
docker compose up -d hackaton-fin-postgres
POSTGRES_HOST=localhost uv run --env-file .env make migrate
POSTGRES_HOST=localhost uv run --env-file .env python -m src.main
```

`.env` автоматически не загружается при обычном запуске Python.
Миграции и приложение используют одинаковые `POSTGRES_*` переменные.

```bash
curl -i http://127.0.0.1:8080/health
```

`GET /health` возвращает HTTP 200 с пустым телом, доступен без авторизации
и не отображается в OpenAPI. Внешние сервисы не требуются.
Swagger UI доступен по `/docs`.

## Наблюдаемость

Трейсы — OpenTelemetry SDK, экспорт OTLP gRPC в Jaeger (в кластере:
`http://jaeger-collector.jaeger.svc.cluster.local:4317`, span'ы запросов
FastAPI и SQL-запросов SQLAlchemy). `/health` и `/metrics` из трейсов
исключены. Недоступный коллектор приложению не мешает — экспортер просто
логирует ошибки.

Метрики — OTel SDK с Prometheus-ридером, `GET /metrics` в формате Prometheus.
В кластере их собирает PodMonitor `hackaton-fin-department`
(репозиторий `fin-department-k8s`).

Настройки (префикс `OTEL_`):

- `OTEL_ENDPOINT` — OTLP gRPC endpoint, по умолчанию `http://localhost:4317`
- `OTEL_TIMEOUT` — таймаут экспорта в секундах, по умолчанию `10`

## Создание питомца

```bash
curl -X POST http://127.0.0.1:8080/api/pets \
  -H 'Content-Type: application/json' \
  -d '{"name":"Barsik","temper":"playful"}'
```

Успешный запрос возвращает HTTP 201 и `{"id":"<uuid.hex>"}`. Начальный баланс
питомца равен `100`.

## Docker (только локальная разработка)

Прод-деплой — не отсюда: образ собирает CI в Harbor, катит FluxCD
(см. «Деплой» ниже). Compose — для локального прогона:

```bash
cp .env.example .env
docker compose up --build -d
docker compose ps
docker compose exec hackaton-fin-department make migrate
curl -i http://127.0.0.1:8080/health
docker compose down
```

Compose запускает один сервис `hackaton-fin-department` и проверяет `/health`.
Имя образа можно задать через `HACKATON_FIN_DEPARTMENT_IMAGE`, путь к файлу
окружения — через `ENV_FILE`.

## Проверки

```bash
make tests
make tests-coverage
make lint
make types
uv run ruff format --check src
```

`make fix` исправляет форматирование и замечания Ruff.
`make quality` выполняет lint, types, fix и tests.
Тесты PostgreSQL используют DSN из `POSTGRES_*`. Перед запуском эти переменные
должны указывать на изолированную тестовую БД:

```bash
POSTGRES_HOST=localhost uv run --env-file .env make tests
```

Session fixture применяет миграции перед тестами и откатывает схему до `base`
после завершения.

## CI/CD

CI — GitHub Actions (`.github/workflows/ci.yml`), три job'а:

1. **Quality** — `lint` (ruff), `types` (mypy), `tests` (pytest + coverage,
   Postgres 17 как service-контейнер, миграции применяются в фикстуре).
2. **image** — только после зелёных проверок и только для push в `main`:
   сборка и публикация образа в Harbor с тегом

   ```
   registry.mortypython.ru/fin/hackaton-fin-department:main-<UTC YYYYMMDDhhmmss>-<sha12>
   ```

   Таймстамп обязателен: деплой-контроллер выбирает тег численной сортировкой
   по `<ts>`, а `sha` хронологию не даёт.

CD — FluxCD в кластере (репозиторий `fin-department-k8s`):

- `ImageRepository`/`ImagePolicy` следят за Harbor и выбирают свежий `main-*` тег
- `ImageUpdateAutomation` коммитит тег в манифесты → Flux перекатывает под
- миграции (`make migrate`) выполняются в init-контейнере до старта приложения

Ручных шагов деплоя нет: смержил PR в `main` → через пару минут новая версия
на `https://api.mortypython.ru`.

Настройки репозитория: secrets/vars `HARBOR_USERNAME`, `HARBOR_TOKEN`
(robot-аккаунт Harbor проекта `fin` с правами Pull+Push).
Полная инфраструктурная схема — `fin-department-k8s/AGENTS.md`.