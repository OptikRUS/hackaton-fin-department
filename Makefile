.PHONY: tests
tests:
	uv run behave --tags=-skip --stop && uv run pytest -vv -x

.PHONY: tests-coverage
tests-coverage:
	uv run coverage run -m behave --tags=-skip && \
	uv run coverage run -a -m pytest && \
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

.PHONY: migrate
migrate:
	uv run alembic -c src/infra/migrations/alembic.ini upgrade heads

.PHONY: downgrade
downgrade:
	uv run alembic -c src/infra/migrations/alembic.ini downgrade -1

.PHONY: migrations
migrations:
	uv run alembic -c src/infra/migrations/alembic.ini revision --autogenerate -m "$(message)"
