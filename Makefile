.PHONY: dev stop migrate test lint format install

install:
	pip install -e ".[dev]"

dev:
	docker compose up -d

stop:
	docker compose down

migrate:
	alembic upgrade head

test:
	pytest tests/ -v --cov=oar

lint:
	ruff check src/ tests/
	mypy src/

format:
	ruff format src/ tests/
	ruff check --fix src/ tests/
