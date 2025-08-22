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
	$(LIBRDKAFKA_FLAGS) uv sync --python .venv/bin/python
	@echo "✅ Production dependencies installed!"

install-dev: ## Install development dependencies using uv
	@echo "📦 Installing development dependencies with uv..."
	$(LIBRDKAFKA_FLAGS) uv sync --python .venv/bin/python --extra dev
	@echo "✅ Development dependencies installed!"

uv-cache-clean:  ## Clear uv cache
	@echo "🗑️  Clearing uv cache..."
	uv cache clean
	@echo "✅ uv cache cleared successfully!"

# Kafka Scripts
SCRIPTS_DIR = src/finder_enrichment/kafka/scripts

setup-kafka:  ## Sets up the required Kafka topics.
	@echo "Setting up Kafka topics..."
	$(LIBRDKAFKA_FLAGS) uv run python -m src.finder_enrichment.kafka.scripts.setup_kafka

setup-kafka-ui:  ## Starts the Kafka UI.
	@echo "Starting Kafka UI..."
	$(LIBRDKAFKA_FLAGS) uv run python -m src.finder_enrichment.kafka.scripts.setup_kafka_ui

reprocess-listings:  ## Fetches all listings and sends them to Kafka.
	@echo "Reprocessing all listings and sending to Kafka..."
	$(LIBRDKAFKA_FLAGS) uv run python -m src.finder_enrichment.kafka.scripts.reprocess_listings

flush-kafka:  ## Flushes all messages from Kafka topics.
	@echo "Flushing Kafka topics..."
	$(LIBRDKAFKA_FLAGS) uv run python -m src.finder_enrichment.kafka.scripts.flush_kafka --all

run-orchestrator:
	$(LIBRDKAFKA_FLAGS) uv run python -m src.finder_enrichment

# API Server
server:  ## Run the Finder Enrichment API server on localhost:3100
	@echo "🚀 Starting Finder Enrichment API server on localhost:3100..."
	@echo "📖 API documentation will be available at: http://localhost:3100/docs"
	@echo "🔧 Press Ctrl+C to stop the server"
	$(LIBRDKAFKA_FLAGS) uv run python scripts/run_api_server.py

test: install-dev  ## Test the API server (requires server to be running)
	@echo "🧪 Testing API endpoints..."
	$(LIBRDKAFKA_FLAGS) uv run pytest src/finder_enrichment/tests/test_description_analyser_api.py
	$(LIBRDKAFKA_FLAGS) uv run pytest src/finder_enrichment/tests/test_image_analyser_api.py
	$(LIBRDKAFKA_FLAGS) uv run pytest src/finder_enrichment/tests/test_auth.py

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
