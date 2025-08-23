# Main Finder Project Makefile
.PHONY: help setup install install-dev test clean uv-cache-clean requirements requirements-dev requirements-all

help:  ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

setup: ## Create virtual environment and install dependencies
	@echo "🔧 Creating virtual environment with uv..."
	@if ! command -v uv >/dev/null 2>&1; then \
		echo "uv command not found, please install uv"; \
		exit 1; \
	else \
		uv venv --python 3.12; \
	fi
	@echo "✅ Virtual environment created successfully!"
	@echo "💡 To activate: source .venv/bin/activate"

install: ## Install production dependencies using uv
	@echo "📦 Installing production dependencies with uv..."
	uv sync --python .venv/bin/python
	@echo "✅ Production dependencies installed!"

install-dev: ## Install development dependencies using uv
	@echo "📦 Installing development dependencies with uv..."
	uv sync --python .venv/bin/python --extra dev
	@echo "✅ Development dependencies installed!"

uv-cache-clean:  ## Clear uv cache
	@echo "🗑️  Clearing uv cache..."
	uv cache clean
	@echo "✅ uv cache cleared successfully!"

# API Server
server:  ## Run the Finder Enrichment API server on localhost:3100
	@echo "🚀 Starting Finder Enrichment API server on localhost:3100..."
	@echo "📖 API documentation will be available at: http://localhost:3100/docs"
	@echo "🔧 Press Ctrl+C to stop the server"
	uv run python scripts/run_api_server.py

# Test targets organized by category
test: test-unit test-api test-integration  ## Run all tests (unit, API, and integration)

test-unit: install-dev  ## Run unit tests (fast, no external dependencies)
	@echo "🧪 Running unit tests..."
	uv run pytest src/finder_enrichment/tests/test_synchronous_enrichment_service.py -v
	uv run pytest src/finder_enrichment/tests/test_enrichment_models.py -v
	uv run pytest src/finder_enrichment/tests/test_orchestrator_api_client.py -v

test-api: install-dev  ## Run API tests (requires server running, mocks external services)
	@echo "🧪 Running API tests..."
	uv run pytest src/finder_enrichment/tests/test_enrichment_api.py -v

test-integration: install-dev  ## Run integration tests (requires all external services)
	@echo "🧪 Running integration tests..."
	@echo "⚠️  Integration tests require running services and API keys"
	@echo "   Run 'uv run python scripts/test_integration_setup.py' first to validate setup"
	uv run pytest src/finder_enrichment/tests/test_description_analyser_api.py -v
	uv run pytest src/finder_enrichment/tests/test_image_analyser_api.py -v
	uv run pytest src/finder_enrichment/tests/test_auth.py -v
	uv run pytest src/finder_enrichment/tests/test_synchronous_enrichment_api.py -v
	uv run pytest src/finder_enrichment/tests/test_synchronous_orchestration_api.py -v
	uv run pytest src/finder_enrichment/tests/test_individual_analysis_integration.py -v

# Individual test targets for specific components
test-sync-service: install-dev  ## Test synchronous enrichment service
	uv run pytest src/finder_enrichment/tests/test_synchronous_enrichment_service.py -v

test-sync-api: install-dev  ## Test synchronous enrichment API endpoints
	uv run pytest src/finder_enrichment/tests/test_synchronous_enrichment_api.py -v

test-sync-orchestration: install-dev  ## Test synchronous orchestration integration
	uv run pytest src/finder_enrichment/tests/test_synchronous_orchestration_api.py -v

test-models: install-dev  ## Test data models
	uv run pytest src/finder_enrichment/tests/test_enrichment_models.py -v

test-individual-analysis: install-dev  ## Test individual analysis endpoints (integration)
	@echo "🧪 Running individual analysis integration tests..."
	@echo "⚠️  These tests require running services and API keys"
	uv run pytest src/finder_enrichment/tests/test_individual_analysis_integration.py -v

# Quick test validation
test-validate-setup: install-dev  ## Validate test environment setup
	@echo "🔍 Validating test environment..."
	uv run python scripts/test_integration_setup.py

# Development test targets
test-fast: install-dev  ## Run only fast unit tests (no integration)
	@echo "⚡ Running fast unit tests only..."
	uv run pytest src/finder_enrichment/tests/test_synchronous_enrichment_service.py -v
	uv run pytest src/finder_enrichment/tests/test_enrichment_models.py -v
	uv run pytest src/finder_enrichment/tests/test_orchestrator_api_client.py -v

test-coverage: install-dev  ## Run tests with coverage report
	@echo "📊 Running tests with coverage..."
	uv run pytest src/finder_enrichment/tests/ --cov=src/finder_enrichment --cov-report=html --cov-report=term-missing

test-synchronous: test-unit test-api  ## Test only synchronous enrichment components
	@echo "🔄 Testing synchronous enrichment components..."
	@echo "   Unit tests, API tests, and models"
	$(MAKE) test-unit
	$(MAKE) test-api
	$(MAKE) test-models

.PHONY: requirements
requirements:
	@echo "Generating requirements.txt from pyproject.toml..."
	uv export --format requirements-txt --no-hashes --no-editable --no-emit-project --output-file requirements.txt
	@echo "requirements.txt generated successfully."

.PHONY: requirements-dev
requirements-dev:
	@echo "Generating requirements-dev.txt from pyproject.toml..."
	uv export --format requirements-txt --no-hashes --no-editable --no-emit-project --extra dev --output-file requirements-dev.txt
	@echo "requirements-dev.txt generated successfully."

.PHONY: requirements-all
requirements-all:
	@echo "Generating all requirements files from pyproject.toml..."
	$(MAKE) requirements
	$(MAKE) requirements-dev
	@echo "All requirements files generated successfully."

# ------------------------------------------------------------------------------
# PyPI Publishing
# ------------------------------------------------------------------------------

.PHONY: build-client
build-client:
	@echo "🏗️ Building finder_enrichment_ai_client package..."
	cd src/finder_enrichment_ai_client && uv pip install -e . && uv build
	@echo "✅ Package built in src/finder_enrichment_ai_client/dist/"

.PHONY: publish-client
publish-client: build-client
	@echo "🧪 Publishing finder_enrichment_ai_client to PyPI..."
	@echo "📦 Uploading package to PyPI..."
	@source .env && cd src/finder_enrichment_ai_client && TWINE_USERNAME=__token__ TWINE_PASSWORD=$$PYPI_TOKEN uv run twine upload dist/*
	@echo "✅ Package published to PyPI successfully!"
