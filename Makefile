.PHONY: setup test lint fmt registry sickle labels

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

registry:  ## FTW polygons -> data/processed/fields.parquet + stats table
	uv run python scripts/build_field_registry.py

sickle:  ## SICKLE per-plot S1 series, regional weather, M1 feature table and baselines
	uv run python scripts/sickle_extract_check.py
	uv run python scripts/sickle_weather_pull.py
	uv run python scripts/sickle_m1_baselines.py

labels:  ## P1b: pull chips/NDVI and build the labelling page (use --pilot first)
	uv run python scripts/odisha_label_pull.py
	uv run python scripts/odisha_label_tool.py
