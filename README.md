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

### Бизнес-метрики

В дополнение к инфраструктурным метрикам сервис экспортирует бизнес-метрики
с префиксом `fin_` (игровая аналитика: загрузки снапшотов, факты аналитики
по типам, покупки/накопления/запасы, награды, распределения миров по главам
и балансам). Метрики двух видов:

- счётчики, увеличиваются в use cases при обработке запросов
  (`fin_snapshot_uploads_total`, `fin_analytics_facts_total{detail_type,actor,mode}`,
  `fin_interactions_total{name}`, `fin_optional_purchases_total`, …);
- мгновенные распределения и гейджи по сохранённым мирам — их пересчитывает
  фоновая задача `Aggregator` раз в `AGGREGATION_INTERVAL_SECONDS` секунд
  (по умолчанию 60): `fin_players_by_story_act{act}`, `fin_pet_balance_*`,
  `fin_plan_*`, `fin_goal_projects_completed{goal}`, `fin_skill_episodes_avg`, …
  Свежесть агрегата — `fin_aggregation_last_success_unixtime`, ошибки —
  `fin_aggregation_errors_total` / `fin_aggregation_parse_errors_total`.

Акт (глава) истории восстанавливается из `state.story.currentDayId` снапшота:
`figma-chapter-1-day-v1` → `act-1`, `campaign-choice-v1:act-N:day` → `act-N`.

Дашборд Grafana — `game-analytics` в `fin-department-k8s`
(`infrastructure/base/controllers/monitoring/dashboards/`).

Настройка (префикс `AGGREGATION_`):

- `AGGREGATION_INTERVAL_SECONDS` — период пересчёта агрегатов, по умолчанию `60`

## Регистрация устройства и питомца

```bash
curl -X POST http://127.0.0.1:8080/api/pets \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: registration-1' \
  -d '{"deviceId":"9f1c2d3e4a5b6078","pet":{"name":"Рыжик","age":"CUB","color":"COPPER","temperament":"Curious","selectedLookId":"PLAIN"},"schemaVersion":1}'
```

Успешный запрос возвращает HTTP 201 и `{"deviceId":"9f1c2d3e4a5b6078"}`.
Идентичный повтор ключа возвращает тот же ответ. Другой запрос с прежним ключом
даёт `409 IDEMPOTENCY_CONFLICT`; попытка изменить уже зарегистрированного
питомца — `409 PROFILE_CONFLICT`. Идентификатор устройства — непустая строка.

## Родительский отчёт (заглушка)

`GET /api/parents/{petId}` принимает строковый идентификатор и возвращает фиксированный
демонстрационный отчёт. Сейчас эндпоинт не читает питомца из базы и не оценивает
действия ребёнка. `pet.id` повторяет переданный идентификатор; остальные поля питомца и
статусы навыков пока заданы в коде.

```json
{
  "pet": {
    "id": "12345678123456781234567812345678",
    "name": "Рыжик",
    "temper": "playful",
    "balance": 100,
    "selectedLookId": "BACKPACK",
    "visualState": "NORMAL"
  },
  "skills": [
    {"id": "FIN-01", "title": "Сравнивает денежные суммы", "status": "MASTERED", "isMastered": true},
    {"id": "FIN-02", "title": "Планирует бюджет на период", "status": "NO_DATA", "isMastered": null},
    {"id": "FIN-03", "title": "Учитывает обязательные нужды перед желаниями", "status": "PRACTICING", "isMastered": false},
    {"id": "FIN-04", "title": "Следит, чтобы денег хватало до следующего дохода", "status": "NO_DATA", "isMastered": null},
    {"id": "FIN-05", "title": "Последовательно собирает на выбранную цель", "status": "MASTERED", "isMastered": true},
    {"id": "FIN-06", "title": "Откладывает желанную покупку ради приоритета", "status": "NO_DATA", "isMastered": null},
    {"id": "FIN-07", "title": "Создаёт запас на непредвиденные расходы", "status": "NO_DATA", "isMastered": null},
    {"id": "FIN-08", "title": "Перестраивает действия после неожиданной траты", "status": "PRACTICING", "isMastered": false},
    {"id": "FIN-09", "title": "Сопоставляет денежные и другие затраты", "status": "NO_DATA", "isMastered": null},
    {"id": "FIN-10", "title": "Планирует дополнительный заработок", "status": "NO_DATA", "isMastered": null},
    {"id": "FIN-11", "title": "Разбирает финансовые последствия и меняет решение", "status": "NO_DATA", "isMastered": null},
    {"id": "FIN-12", "title": "Понимает свои доходы и расходы", "status": "NO_DATA", "isMastered": null}
  ],
  "isDemo": true
}
```

`NO_DATA` отличается от `PRACTICING`: отсутствие наблюдений не означает, что
ребёнок не усвоил навык. Поэтому `isMastered` в этом случае равен `null`.

## Снапшоты мира

`PUT /v1/profiles/snapshot` сохраняет полный архив в PostgreSQL, а
`POST /v1/profiles/snapshot/download` возвращает последнюю подтверждённую версию.
Оба запроса передают `deviceId` в JSON-теле. Успешный PUT
возвращает `200` при первой записи, обновлении и повторе. Ответ содержит
`uploadId`, `gameRunId`, `serverRevision` и `checksum`. Точный формат тела
запроса и ответа доступен в `/docs`.

При загрузке обязательный заголовок `Idempotency-Key` равен `uploadId`.
Идентичный повтор возвращает прежний результат без изменения ревизии, другой
запрос с тем же ID получает `409 IDEMPOTENCY_CONFLICT`. Клиент передаёт
`expectedServerRevision=null` для первой записи, затем последнюю полученную
ревизию. Устаревшая ревизия даёт `409 SNAPSHOT_REVISION_CONFLICT`. Новый
`gameRunId` принимается в формате 5, если `archivedRuns` сохраняет прежний
журнал как неизменный префикс и цепочка `nextRunId` ведёт к новому прохождению.
Произвольная замена прохождения или удаление прежнего архива даёт
`409 GAME_RUN_CONFLICT`. Если архива нет, скачивание возвращает
`404 SNAPSHOT_NOT_FOUND`.

Некорректная форма PUT-запроса и значения, которые PostgreSQL не может сохранить,
дают `400 INVALID_REQUEST`. `uploadId` ограничен 255 байтами UTF-8; в строковых
полях не допускается NUL. Повреждённый JSON архива или несовпадение его
верхних метаданных с оболочкой даёт `422 SNAPSHOT_INVALID`.

Поддерживаются форматы снапшота 1–5 и версия оболочки `schemaVersion=1`.
Сервер разбирает `snapshotJson` как JSON и сверяет его `formatVersion`, `runId`,
`historySequence` и `checksum` с оболочкой. Строка архива хранится и выдаётся
без изменений. Полный алгоритм HistoryCodec, включая пересчёт checksum и проверку
истории, пока не перенесён. В этом этапе доступ определяется строковым `deviceId`;
авторизации и Bearer-токенов контракт не предусматривает.

## Мобильные методы

| Метод | Путь | Назначение |
| --- | --- | --- |
| `POST` | `/api/pets` | Регистрация питомца и `deviceId` |
| `PUT` | `/v1/profiles/snapshot` | Отправка архива |
| `POST` | `/v1/profiles/snapshot/download` | Получение архива |
| `POST` | `/v1/profiles/analytics` | Передача фактов и навыков |
| `POST` | `/v1/profiles/skills/query` | Получение оценок навыков |
| `POST` | `/v1/profiles/rewards/pull` | Получение подарков |
| `POST` | `/v1/profiles/rewards/ack` | Подтверждение применения подарков |
| `POST` | `/v1/parent-profiles/rewards` | Выдача подарка |

`deviceId` передаётся в JSON-теле каждого метода. Регистрация, отправка архива
и аналитики, подтверждение и выдача подарка требуют `Idempotency-Key`.
Текущие версии, ответы и правила перезапуска описаны в
[контракте мобильного API](docs/mobile-contract.md).

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
