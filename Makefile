.PHONY: help install dev test test-unit test-integration test-security lint format typecheck audit clean services services-down

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

install: ## Install runtime dependencies
	pip install -e .

dev: ## Install all dependencies (runtime + dev + voice)
	pip install -e ".[all]"
	pre-commit install

# ---------------------------------------------------------------------------
# Testing
# ---------------------------------------------------------------------------

test: ## Run all unit tests
	pytest tests/unit/ -v --cov=clawssistant --cov-report=term-missing

test-unit: ## Run unit tests only (no external services needed)
	pytest tests/unit/ -v

test-integration: ## Run integration tests (requires docker services)
	pytest tests/integration/ -v -m integration

test-security: ## Run security-focused tests
	pytest tests/unit/test_security.py -v

test-all: ## Run entire test suite
	pytest tests/ -v --cov=clawssistant --cov-report=term-missing

# ---------------------------------------------------------------------------
# Code Quality
# ---------------------------------------------------------------------------

lint: ## Run linter
	ruff check .

format: ## Format code
	ruff format .

typecheck: ## Run type checker
	mypy clawssistant/

audit: ## Audit dependencies for known vulnerabilities
	pip-audit

check: lint typecheck test-security test ## Run all checks (lint + types + security + tests)

# ---------------------------------------------------------------------------
# Docker Services (for integration testing)
# ---------------------------------------------------------------------------

services: ## Start test services (MQTT, HA, Redis)
	docker compose -f docker-compose.test.yml up -d

services-down: ## Stop test services
	docker compose -f docker-compose.test.yml down

services-logs: ## Tail test service logs
	docker compose -f docker-compose.test.yml logs -f

# ---------------------------------------------------------------------------
# Development
# ---------------------------------------------------------------------------

run: ## Run the assistant (development mode)
	python -m clawssistant

clean: ## Remove build artifacts and caches
	rm -rf build/ dist/ *.egg-info .pytest_cache .mypy_cache .ruff_cache htmlcov/ .coverage coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
