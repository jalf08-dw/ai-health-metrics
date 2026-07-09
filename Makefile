.PHONY: help up down logs test clean lint format restart

help:
	@echo "AI-Queryable Health Data System - Available Commands"
	@echo ""
	@echo "  make up          - Start all services (docker compose up)"
	@echo "  make down        - Stop all services (docker compose down)"
	@echo "  make logs        - Show logs from all services"
	@echo "  make test        - Run test suite"
	@echo "  make test-watch  - Run tests in watch mode"
	@echo "  make restart     - Restart all services"
	@echo "  make clean       - Remove containers, volumes, and temporary files"
	@echo "  make lint        - Run code linting"
	@echo "  make format      - Format code with black"
	@echo "  make docs        - Open Swagger UI in browser"
	@echo "  make shell-db    - Open psql shell to database"
	@echo "  make shell-api   - Open shell in API container"

up:
	docker compose up

down:
	docker compose down

logs:
	docker compose logs -f

test:
	docker compose -f docker-compose.test.yml up

test-watch:
	pytest tests/ -v --tb=short -x

clean:
	docker compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .coverage -exec rm -rf {} + 2>/dev/null || true

lint:
	pip install flake8 black
	flake8 src/ tests/
	black --check src/ tests/

format:
	pip install black
	black src/ tests/

restart:
	docker compose restart

docs:
	open http://localhost:8000/docs || xdg-open http://localhost:8000/docs || echo "Open http://localhost:8000/docs"

shell-db:
	docker exec -it health-metrics-db psql -U postgres -d health_metrics

shell-api:
	docker exec -it health-metrics-api bash

.DEFAULT_GOAL := help
