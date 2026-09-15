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
