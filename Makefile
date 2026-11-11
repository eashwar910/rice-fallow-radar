.PHONY: setup test lint fmt

setup:  ## install env + git hooks
	uv sync
	uv run pre-commit install

test:
	uv run pytest -q

lint:
	uv run ruff check .
	uv run ruff format --check .

fmt:
	uv run ruff check --fix .
	uv run ruff format .
