.PHONY: help install dev-install test lint format typecheck run migrate seed clean docker-build docker-up docker-down

# Default target
help:
	@echo "GlobalRisk AI - Available commands:"
	@echo ""
	@echo "  install       Install production dependencies"
	@echo "  dev-install   Install development dependencies"
	@echo "  test          Run tests"
	@echo "  test-cov      Run tests with coverage"
	@echo "  lint          Run linter (ruff)"
	@echo "  format        Format code (ruff)"
	@echo "  typecheck     Run type checker (mypy)"
	@echo "  run           Run API server (development)"
	@echo "  run-prod      Run API server (production)"
	@echo "  migrate       Run database migrations"
	@echo "  migrate-create Create new migration"
	@echo "  seed          Seed demo data"
	@echo "  clean         Clean build artifacts"
	@echo "  docker-build  Build Docker images"
	@echo "  docker-up     Start Docker containers"
	@echo "  docker-down   Stop Docker containers"
	@echo "  docker-logs   View Docker logs"
	@echo ""

# Installation
install:
	pip install -e .

dev-install:
	pip install -e ".[dev]"

# Testing
test:
	pytest -v

test-cov:
	pytest --cov=app --cov-report=term-missing --cov-report=html

test-watch:
	pytest-watch

# Code Quality
lint:
	ruff check .

format:
	ruff format .

typecheck:
	mypy app/

check: lint typecheck

# Running
run:
	uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000

run-prod:
	uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --workers 4

# Database
migrate:
	alembic upgrade head

migrate-create:
	@read -p "Migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

migrate-history:
	alembic history

migrate-current:
	alembic current

# Data
seed:
	python scripts/seed_demo_data.py

ingest:
	@read -p "Directory: " dir; \
	read -p "Company: " company; \
	read -p "Year: " year; \
	python scripts/ingest_reports.py "$$dir" "$$company" "$$year"

pipeline:
	@read -p "Report ID: " rid; \
	python scripts/run_pipeline.py "$$rid"

evaluate:
	@read -p "Report ID (optional): " rid; \
	read -p "Output file (optional): " out; \
	python scripts/evaluate_pipeline.py ${rid:+--report-id $$rid} ${out:+--output $$out}

# Cleaning
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	rm -rf dist/ build/ .coverage htmlcov/ .pytest_cache/ .mypy_cache/ .ruff_cache/

# Docker
docker-build:
	docker-compose -f docker/docker-compose.yml build

docker-up:
	docker-compose -f docker/docker-compose.yml up -d

docker-down:
	docker-compose -f docker/docker-compose.yml down

docker-logs:
	docker-compose -f docker/docker-compose.yml logs -f

docker-restart: docker-down docker-up

docker-shell:
	docker-compose -f docker/docker-compose.yml exec api bash

# Documentation
docs-serve:
	mkdocs serve -f docs/mkdocs.yml

docs-build:
	mkdocs build -f docs/mkdocs.yml

# Pre-commit
pre-commit-install:
	pre-commit install

pre-commit-run:
	pre-commit run --all-files

# Development workflow
dev: dev-install migrate seed run

ci: install lint typecheck test

# Release
version-patch:
	bump2version patch

version-minor:
	bump2version minor

version-major:
	bump2version major