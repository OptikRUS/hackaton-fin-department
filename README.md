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

## CI/CD

Workflow **Quality** запускается на push в `main`, PR в `main` и вручную.
Push в ветку PR не создаёт второй запуск тех же проверок.
Он проверяет Ruff, форматирование и ty, выполняет BDD и pytest с coverage на
изолированной PostgreSQL 17.11, затем собирает образ для Linux amd64.
Python — 3.14, uv — 0.12.14; зависимости устанавливаются строго по `uv.lock`.
XML- и HTML-отчёты coverage доступны в artifacts запуска в течение 14 дней.
Шаг `Publish coverage report` публикует coverage-комментарий в PR из этого
репозитория и сохраняет базовый отчёт после push в `main`. Для PR из forks
доступны artifacts без публикации комментария. Как и в `gym-master`, запуск
`make tests-coverage` и публикация отчёта находятся внутри job `tests`.

Только успешный **push в `main`** публикует образ в Docker Hub с тегами
`sha-<полный SHA коммита>` и `latest`. PR, другие ветки и ручной запуск Quality
не используют Docker Hub Secrets и не публикуют образы. Actions закреплены SHA.

### Настройка GitHub

В **Settings → Secrets and variables → Actions** добавьте repository Variables:

| Variable             | Значение                                             |
|----------------------|------------------------------------------------------|
| `DOCKERHUB_USERNAME` | Пользователь Docker Hub                              |
| `DOCKERHUB_REPONAME` | Имя репозитория образа без пользователя              |
| `APP_PORT`           | Необязательно: внешний порт API, по умолчанию `8080` |

Repository Secrets:

| Secret                   | Назначение                                                     |
|--------------------------|----------------------------------------------------------------|
| `DOCKERHUB_TOKEN`        | Docker Hub access token с правами pull/push                    |
| `SERVER_HOST`            | IP или DNS-имя VPS                                             |
| `SERVER_PORT`            | SSH-порт, например `22`                                        |
| `SERVER_USERNAME`        | SSH-пользователь с доступом к Docker                           |
| `SERVER_SSH_PRIVATE_KEY` | Закрытый SSH-ключ этого пользователя                           |
| `SSH_KNOWN_HOSTS`        | Проверенная запись ключа сервера в формате OpenSSH known_hosts |
| `POSTGRES_USER`          | Пользователь production-БД                                     |
| `POSTGRES_PASSWORD`      | Пароль production-БД                                           |
| `POSTGRES_NAME`          | Имя production-БД                                              |

Для нестандартного SSH-порта known_hosts должен содержать `[host]:port`.
Проверьте fingerprint ключа через доверенный доступ к VPS; workflow не принимает
неизвестные ключи автоматически. Значения настроек БД должны быть однострочными.
Текущий код формирует DSN строкой: выбирайте имя пользователя, имя БД и пароль
без URL-разделителей; для пароля подходит длинная случайная строка из букв,
цифр, `-` и `_`.

### Первый деплой

На VPS Linux amd64 установите Docker Engine и Compose v2 с поддержкой `--wait`.
SSH-пользователю нужны доступ к Docker и права записи в
`/opt/hackaton-fin-department`. Создайте этот каталог с владельцем — пользователем
деплоя и правами `0700`. Порты `5432` на loopback и выбранный порт API должны
быть свободны; для внешнего доступа разрешите порт API в firewall.

1. Настройте Variables и Secrets, затем дождитесь успешного Quality после push в `main`.
2. Откройте **Actions → Deploy → Run workflow**, выберите ветку `main`.
3. Оставьте `commit_sha` пустым для текущего `main` или укажите полный SHA ранее
   опубликованного коммита из истории `main`.

До SSH workflow проверяет успешный запуск Quality и шаг публикации выбранного
коммита. Compose берётся из этого же коммита; тег образа разрешается в digest,
и сервер запускает именно `repository@sha256:…`. Образ и коммит видны в summary.

Настройки передаются по SSH в `.env` с правами `0600`. Docker Hub token
используется через stdin и временный Docker config, который удаляется после
деплоя. Приложение подключается к `hackaton-fin-postgres:5432`; PostgreSQL
публикуется только на loopback VPS, данные хранятся в постоянном volume проекта
`hackaton-fin-department`.

Сервер скачивает образ, ждёт готовности PostgreSQL, выполняет `make migrate`
одноразовым контейнером и обновляет API без сборки. Успех требует прохождения
`/health` за 180 секунд. Этот endpoint проверяет доступность HTTP-сервиса;
миграции отдельно проверяют доступность БД. Ошибка миграции останавливает
обновление API, ошибка healthcheck делает деплой неуспешным.

Деплои не прерывают друг друга: GitHub допускает один активный и один ожидающий
запуск в concurrency group; новый ожидающий запуск может заменить предыдущий.
Для диагностики на сервере:

```bash
cd /opt/hackaton-fin-department
docker compose -p hackaton-fin-department --env-file .env ps
docker compose -p hackaton-fin-department --env-file .env logs --tail=100 hackaton-fin-department
```

Повторный запуск Deploy с предыдущим SHA возвращает предыдущий образ, если он
доступен в Docker Hub и совместим с текущей схемой БД. Автоматического отката
схемы нет. Миграции должны сохранять совместимость с работающей версией API.
Изменение PostgreSQL Secrets не меняет пароль или имя уже созданной БД внутри
существующего volume: такие изменения требуют отдельной процедуры в PostgreSQL.
Настройка GitHub/VPS и первый production-деплой выполняются отдельно от локальной
проверки конфигурации.

## Структура

- `src/config` — настройки приложения, CORS и путей.
- `src/core` — доменные enum, params, storage-контракты и use cases.
- `src/di` — контейнер Dishka и общие providers.
- `src/infra/api` — создание FastAPI-приложения, маршруты и HTTP-ошибки.
- `src/infra/storages/postgres` — SQLAlchemy models и storage.
- `src/infra/migrations` — Alembic configuration, commands и revisions.
- `src/main.py` — запуск Uvicorn и lifecycle контейнера.
- `src/tests` — API-тесты, фикстуры и HTTP-helper.
