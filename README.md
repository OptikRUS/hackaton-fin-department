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

## Создание питомца

```bash
curl -X POST http://127.0.0.1:8080/api/pets \
  -H 'Content-Type: application/json' \
  -d '{"name":"Barsik","temper":"playful"}'
```

Успешный запрос возвращает HTTP 201 и `{"id":"<uuid.hex>"}`. Начальный баланс
питомца равен `100`.

## Docker

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

## Деплой

CI (GitHub Actions) собирает образ в Harbor на каждый push в `main`
(секреты: `HARBOR_USERNAME`, `HARBOR_TOKEN`). Деплой — FluxCD, без ручных шагов.
Настройка и схема: репозиторий `fin-department-k8s`, файл `AGENTS.md`.
