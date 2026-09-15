# Reference: PostgreSQL и ClickHouse migrations

## Статус в проекте

Alembic, database settings, ORM metadata и migration layers отсутствуют. [main.py](main_py.md) запускает только HTTP-приложение.

Ниже сохранён переносимый паттерн из исходного набора references. Это пример для будущего
расширения, а не существующие классы, пути или обязательство добавить подсистему. Imports могут
быть опущены; вспомогательные типы и методы нужно определить под выбранный контракт.
`Entity*` в разных документах показывает роли, а не единую готовую модель проекта.

## REUSABLE PATTERN: revision shape

```python
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("entities", ...)


def downgrade() -> None:
    op.drop_table("entities")
```

`entities` — placeholder. Реальная migration должна совпасть с живой ORM/domain/wire chain и иметь
следующий доступный revision конкретного migration layer.

Одноразовый перенос legacy данных описывает historical models непосредственно внутри migration, а не
в runtime `models.py`. Они отражают ровно schema предыдущей revision и применяются через
`Session(bind=op.get_bind())`; production ORM не импортируется в migration.

В исходном паттерне каждый migration layer ведёт свою последовательность четырёхзначных
revisions (`0001`, `0002`, ...). При добавлении БД потребуются driver, metadata, Alembic config,
DSN и команды запуска; готовых `make migrate`/`make clickhouse-migrate` сейчас нет.
