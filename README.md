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
даёт `409 IDEMPOTENCY_CONFLICT`. Повторная регистрация того же `deviceId` с новым
ключом обновляет зарегистрированные поля питомца и сохраняет историю профиля.
Актуальные игровые данные питомца приходят со snapshot. Идентификатор устройства —
непустая строка.

## Родительский отчёт

`GET /api/parents/{petId}` принимает зарегистрированный `deviceId` как `petId`.
Неизвестный идентификатор возвращает `404 {"code":"PARENT_REPORT_NOT_FOUND"}`.
Данные питомца берутся из последнего принятого snapshot, а до первого snapshot —
из регистрации. Тогда `balance` и `visualState` равны `null`; `temper` тоже может
быть `null`. Баланс архива — сумма `availableBalance` и `savingsBalance`.

Статусы навыков берутся из сохранённой серверной оценки для `gameRunId`
последнего snapshot. Пока её нет, все 12 статусов равны `NO_DATA`. Аналитика нового
прохождения не меняет отчёт до принятия его snapshot. `isDemo` всегда `false`.

Каждый из 12 навыков FIN-01…FIN-12 получает опубликованные материалы для разговора
родителя с ребёнком: `materialsAvailable=true`, а поля заполняются из общего каталога
версии `2026-09-29-v1` независимо от статуса навыка (`MASTERED`, `PRACTICING`,
`NO_DATA`, `HAS_PROBLEM`).
Если каталог не опубликован, `materialsAvailable=false`, строки и массивы пусты.
Все поля обязательны и возвращаются в camelCase:

| Поле                     | Тип          | Содержание                                        |
|--------------------------|--------------|---------------------------------------------------|
| `materialsAvailable`     | boolean      | Доступны ли опубликованные материалы              |
| `learningGoal`           | строка       | Цель обучения                                     |
| `story`                  | строка       | Пример истории для разговора                      |
| `replaceWithParentStory` | строка       | Подсказка для выбора собственной истории родителя |
| `conversationStarters`   | массив строк | Пять реплик для начала разговора                  |
| `parentTakeaway`         | строка       | Главная мысль для родителя                        |
| `researchBasis`          | строка       | Исследовательское обоснование                     |
| `researchSources`        | массив строк | Ссылки на исследования                            |

Пример ответа ниже — фрагмент с одним навыком. Полный ответ содержит все 12
навыков с таким же набором полей.

```json
{
  "pet": {
    "id": "9f1c2d3e4a5b6078",
    "name": "Рыжик",
    "temper": null,
    "balance": 100,
    "selectedLookId": "PLAIN",
    "visualState": "NORMAL"
  },
  "skills": [
    {
      "id": "FIN-01",
      "title": "Сравнивает денежные суммы",
      "status": "MASTERED",
      "isMastered": true,
      "materialsAvailable": true,
      "learningGoal": "Ребенок привыкает сравнивать стоимость нескольких вариантов до принятия решения и понимать, имеет ли разница в цене значение в конкретной ситуации.",
      "story": "Я как-то очень хотел купить одну вещь и взял ее в первом же магазине. А через пару дней увидел точно такую же намного дешевле. Было обидно: я ведь мог сначала посмотреть несколько вариантов. Но потом задумался, что ехать через весь город ради совсем небольшой скидки тоже не всегда имеет смысл.",
      "replaceWithParentStory": "Вспомните случай, когда вы купили что-то, а позже увидели дешевле, нашли более выгодный вариант или, наоборот, сознательно выбрали более дорогой вариант.",
      "conversationStarters": [
        "У тебя было такое, что ты что-то купил, а потом увидел дешевле?",
        "Как думаешь, я мог что-нибудь сделать до покупки, чтобы потом не расстраиваться?",
        "А если в другом магазине дешевле совсем чуть-чуть — ты бы стал искать другой магазин?",
        "Как думаешь, самый дешевый вариант всегда самый хороший?",
        "Если бы ты сейчас выбирал дорогую игрушку или игру, что бы ты сравнил перед покупкой?"
      ],
      "parentTakeaway": "Не сводите разговор к вычислению разницы между ценами. Цель — сформировать привычку замечать альтернативы и сравнивать их перед решением.",
      "researchBasis": "CFPB связывает финансовую компетентность в middle childhood с базовыми финансовыми знаниями и осознанным принятием решений. OECD/EU включает сравнение стоимости, цен и вариантов в область Money and transactions.",
      "researchSources": [
        "https://www.consumerfinance.gov/consumer-tools/educator-tools/youth-financial-education/learn/financial-knowledge-decision-making-skills/",
        "https://www.oecd.org/en/publications/financial-competence-framework-for-children-and-youth-in-the-european-union_bf059471-en.html"
      ]
    }
  ],
  "isDemo": false
}
```

`NO_DATA` отличается от `PRACTICING`: отсутствие наблюдений не означает, что
ребёнок не усвоил навык. Поэтому `isMastered` в этом случае равен `null`.

## Материалы для родителя

`GET /v1/parent-materials` возвращает общий каталог без `deviceId`, регистрации
и готовой оценки навыков. Каталог не содержит питомца или статусов освоения.
Текущий ответ — HTTP 200 с опубликованными материалами для всех 12 навыков.
Ниже показан фрагмент с одной записью:

```json
{
  "schemaVersion": 1,
  "contentVersion": "2026-09-29-v1",
  "publicationStatus": "PUBLISHED",
  "skills": [
    {
      "skillId": "FIN-01",
      "learningGoal": "Ребенок привыкает сравнивать стоимость нескольких вариантов до принятия решения и понимать, имеет ли разница в цене значение в конкретной ситуации.",
      "story": "Я как-то очень хотел купить одну вещь и взял ее в первом же магазине. А через пару дней увидел точно такую же намного дешевле. Было обидно: я ведь мог сначала посмотреть несколько вариантов. Но потом задумался, что ехать через весь город ради совсем небольшой скидки тоже не всегда имеет смысл.",
      "replaceWithParentStory": "Вспомните случай, когда вы купили что-то, а позже увидели дешевле, нашли более выгодный вариант или, наоборот, сознательно выбрали более дорогой вариант.",
      "conversationStarters": [
        "У тебя было такое, что ты что-то купил, а потом увидел дешевле?",
        "Как думаешь, я мог что-нибудь сделать до покупки, чтобы потом не расстраиваться?",
        "А если в другом магазине дешевле совсем чуть-чуть — ты бы стал искать другой магазин?",
        "Как думаешь, самый дешевый вариант всегда самый хороший?",
        "Если бы ты сейчас выбирал дорогую игрушку или игру, что бы ты сравнил перед покупкой?"
      ],
      "parentTakeaway": "Не сводите разговор к вычислению разницы между ценами. Цель — сформировать привычку замечать альтернативы и сравнивать их перед решением.",
      "researchBasis": "CFPB связывает финансовую компетентность в middle childhood с базовыми финансовыми знаниями и осознанным принятием решений. OECD/EU включает сравнение стоимости, цен и вариантов в область Money and transactions.",
      "researchSources": [
        "https://www.consumerfinance.gov/consumer-tools/educator-tools/youth-financial-education/learn/financial-knowledge-decision-making-skills/",
        "https://www.oecd.org/en/publications/financial-competence-framework-for-children-and-youth-in-the-european-union_bf059471-en.html"
      ]
    }
  ]
}
```

Источник — `src/infra/api/parents/data/materials.json`. Тексты опубликованы
в версии `2026-09-29-v1`.
`UNPUBLISHED` требует пустого `skills`. `PUBLISHED` требует ровно по одной записи
FIN-01…FIN-12, идентификатор `skillId`, все перечисленные выше текстовые поля
материалов без пустых значений, ровно пять непустых `conversationStarters` и
непустой список HTTPS-ссылок `researchSources`. `contentVersion` не может быть
пустым. Для совместимости отсутствие `publicationStatus` в заполненном каталоге
означает `PUBLISHED`; ответы всегда содержат этот статус явно.

Каталог загружается и проверяется при запросе, поэтому отсутствие файла означает
неопубликованные материалы и не мешает запуску сервиса. Повреждённый JSON,
неверная структура или ошибка чтения дают HTTP 503 с
`{"detail":"PARENT_MATERIALS_UNAVAILABLE"}` в обоих родительских методах;
`/health` и остальные API продолжают работать. После исправления файла следующий
запрос читает новый каталог без перезапуска.

## Снапшоты мира

`PUT /v1/profiles/snapshot` сохраняет текущий мир или legacy-архив в PostgreSQL, а
`POST /v1/profiles/snapshot/download` возвращает последнюю подтверждённую версию.
Оба запроса передают `deviceId` в JSON-теле. Успешный PUT
возвращает `200` при первой записи, обновлении и повторе. Ответ содержит
`uploadId`, `gameRunId`, `serverRevision` и `checksum`. Точный формат тела
запроса и ответа доступен в `/docs`.

При загрузке обязательный заголовок `Idempotency-Key` равен `uploadId`.
Идентичный повтор возвращает прежний результат без изменения ревизии, другой
запрос с тем же ID получает `409 IDEMPOTENCY_CONFLICT`. Клиент передаёт
`expectedServerRevision=null` для первой записи, затем последнюю полученную
ревизию. Устаревшая ревизия даёт `409 SNAPSHOT_REVISION_CONFLICT`. Текущий игровой
клиент передаёт полный архив `formatVersion=5` без `payloadKind`; переход к новому
прохождению проверяется через `archivedRuns` и цепочку `nextRunId`. Backend также
поддерживает компактный мир с `payloadKind="CURRENT_WORLD"`, внутренним
`worldFormatVersion=1` и `predecessors`; полный журнал для него не нужен.
Произвольная замена прохождения даёт
`409 GAME_RUN_CONFLICT`. Если архива нет, скачивание возвращает
`404 SNAPSHOT_NOT_FOUND`.

Некорректная форма PUT-запроса и значения, которые PostgreSQL не может сохранить,
дают `400 INVALID_REQUEST`. `uploadId` ограничен 255 байтами UTF-8; в строковых
полях не допускается NUL. Повреждённый JSON архива или несовпадение его
верхних метаданных с оболочкой даёт `422 SNAPSHOT_INVALID`.

Поддерживаются текущий мир `worldFormatVersion=1`, legacy-форматы 1–5 и
версия оболочки `schemaVersion=1`. Сервер разбирает `snapshotJson` как JSON
и сверяет версию соответствующего формата, `runId`, `historySequence` и
`checksum` с оболочкой. Строка архива хранится и выдаётся
без изменений. Полный алгоритм HistoryCodec, включая пересчёт checksum и проверку
истории, пока не перенесён. В этом этапе доступ определяется строковым `deviceId`;
авторизации и Bearer-токенов контракт не предусматривает.

## Аналитика и восстановление

Аналитика зарегистрированного устройства принимается отдельно от backup:
родительский режим может обновлять её до загрузки мира или впереди его границы.
`historyStartSequence` отмечает отсутствующий префикс после восстановления;
ранее сохранённые факты и проекции сохраняются, повторы не удваивают наблюдения.
Миграция `0007` добавляет границы диапазонов и последовательности исходных фактов.

После приёма аналитики сервер рассчитывает и сохраняет все 12 оценок навыков
по политике `skills-mvp-v1`. `skills/query` также обрабатывает старые принятые
данные без повторной отправки с устройства. Правила и ограничения — в
[описании MVP навыков](docs/skill-assessment-mvp.md); форматы запросов — в
[мобильном контракте](docs/mobile-contract.md).

## Мобильные методы

| Метод  | Путь                             | Назначение                        |
|--------|----------------------------------|-----------------------------------|
| `GET`  | `/v1/parent-materials`           | Каталог материалов для родителя   |
| `POST` | `/api/pets`                      | Регистрация питомца и `deviceId`  |
| `PUT`  | `/v1/profiles/snapshot`          | Отправка архива                   |
| `POST` | `/v1/profiles/snapshot/download` | Получение архива                  |
| `POST` | `/v1/profiles/analytics`         | Передача фактов и навыков         |
| `POST` | `/v1/profiles/skills/query`      | Получение оценок навыков          |
| `POST` | `/v1/profiles/rewards/pull`      | Получение подарков                |
| `POST` | `/v1/profiles/rewards/ack`       | Подтверждение применения подарков |
| `POST` | `/v1/parent-profiles/rewards`    | Выдача подарка                    |

`deviceId` передаётся в JSON-теле методов игрового профиля; общему GET-каталогу
материалов идентификатор не нужен. Регистрация, отправка архива
и аналитики, подтверждение и выдача подарка требуют `Idempotency-Key`.
Текущие версии, ответы и правила перезапуска описаны в
[контракте мобильного API](docs/mobile-contract.md).

## Docker (только локальная разработка)

Прод-деплой — не отсюда: образ собирает CI в Harbor, катит FluxCD (см. «Деплой» ниже). Compose — для
локального прогона:

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
