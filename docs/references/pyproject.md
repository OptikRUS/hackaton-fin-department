# Reference: tooling configuration

## pyproject.toml

[pyproject.toml](../../pyproject.toml) задаёт Python `>=3.14,<3.15`, имя пакета
`hackaton-fin-department` и версию `0.1.0`. Имя приложения — `hackaton-fin-department`.
Зависимости: Dishka, FastAPI, httpx2, Pydantic Settings, Uvicorn. Dev-инструменты:
pytest, pytest-asyncio, pytest-cov, Ruff, ty. Зафиксированные версии — в [uv.lock](../../uv.lock).

```toml
[tool.pytest.ini_options]
pythonpath = ["."]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
testpaths = ["src/tests"]

```

Ty: `all = "error"`, `missing-override-decorator = "ignore"`, Python 3.14,
`strict-literal-narrowing = true`; отдельных overrides нет.
Ruff: `py314`, длина строки 100, `select = ["ALL"]`, двойные кавычки.
Точный список ignore — в pyproject; per-file ignores есть только для `src/tests/*`.

## Make targets

Текущий [Makefile](../../Makefile):

```makefile
.PHONY: tests
tests:
	uv run pytest -vv -x

.PHONY: tests-coverage
tests-coverage:
	uv run coverage run -m pytest && \
	uv run coverage report

.PHONY: lint
lint:
	uv run ruff check src --config pyproject.toml

.PHONY: types
types:
	uv run ty check

.PHONY: fix
fix:
	uv run ruff format --config pyproject.toml . && uv run ruff check --fix src --config pyproject.toml

.PHONY: quality
quality: lint types fix tests
```

`make quality` включает форматирование с записью. Для проверки без исправлений:

```bash
uv run ruff check src --config pyproject.toml
uv run ruff format --check src
uv run ty check
uv run pytest -vv -x
```

Behave, migration targets, `make plan` и Ralphex не подключены.
Для documentation-only изменений достаточно сверки snippets, ссылок и `git diff --check`;
тесты production-кода нужны при изменении его поведения.
