# hackaton-fin-department

HTTP-каркас на Python 3.14, FastAPI и Dishka, перенесённый из
`cpa-offers-catalog`. Версия приложения — `0.1.0`.

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
uv run --env-file .env python -m src.main
```

`.env` автоматически не загружается при обычном запуске Python.

```bash
curl -i http://127.0.0.1:8080/health
```

`GET /health` возвращает HTTP 200 с пустым телом, доступен без авторизации
и не отображается в OpenAPI. Внешние сервисы не требуются.
Swagger UI доступен по `/docs`.

## Docker

```bash
cp .env.example .env
docker compose up --build -d
docker compose ps
curl -i http://127.0.0.1:8080/health
docker compose down
```

Compose запускает один сервис `hackaton-fin-department` и проверяет `/health`.
Имя образа можно задать через `HACKATON_DIPFIN_IMAGE`, путь к файлу
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
`make quality` выполняет lint, types, fix и tests, как в референсе.

## Структура

- `src/config` — настройки приложения, CORS и путей.
- `src/core` — пакет для будущей доменной логики.
- `src/di` — контейнер Dishka и общие providers.
- `src/infra/api` — создание FastAPI-приложения, маршруты и HTTP-ошибки.
- `src/main.py` — запуск Uvicorn и lifecycle контейнера.
- `src/tests` — API-тесты, фикстуры и HTTP-helper.
