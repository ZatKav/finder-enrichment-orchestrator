# Finder Enrichment Orchestrator

A Kafka-based enrichment orchestrator that processes property listings through various analysis services to enhance property data with AI-powered insights.

## Overview

The Finder Enrichment Orchestrator is a central coordination service that manages the enrichment of property listings through multiple specialized analysis services:

- **Description Analysis**: AI-powered analysis of property descriptions for sentiment, features, and quality
- **Floorplan Analysis**: Computer vision analysis of property floorplans 
- **Image Analysis**: Computer vision analysis of property images
- **Enriched Data Storage**: Coordinated storage of analysis results

## Architecture

```
┌─────────────────┐    ┌──────────────────────────────────────────────────────────────┐
│ Enrichment      │────▶│                     Enrichment                               │
│ topic           │    │                                                              │
└─────────────────┘    └──────────────────────────────────────────────────────────────┘
                                                │
                       ┌────────────────────────┼────────────────────────┐
                       ▼                        ▼                        ▼
            ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
            │ Listings-db-    │    │ Listings        │    │ Floorplan       │    │ Image           │    │ Enriched-db-    │
            │ api             │    │ description     │    │ analyser        │    │ analyser        │    │ api             │
            └─────────────────┘    │ analyser        │    └─────────────────┘    └─────────────────┘    └─────────────────┘
                       │           └─────────────────┘                                                             ▲
                       ▼                                                                                            │
            ┌─────────────────┐                                                                                     │
            │ Listings Db     │                                                                          ┌─────────────────┐
            └─────────────────┘                                                                          │ Enriched Db     │
                                                                                                         └─────────────────┘
```

## Features

- **Asynchronous Processing**: Kafka-based message passing for scalable, asynchronous processing
- **Parallel Enrichment**: Configurable parallel processing of multiple enrichment types
- **Service Integration**: Clean integration points for external analysis services
- **Error Handling**: Comprehensive error handling and retry mechanisms
- **Monitoring**: Built-in health checks and processing statistics
- **Configuration**: Environment-based configuration with validation

## Requirements

- Python 3.13+
- Apache Kafka
- Access to analysis service endpoints
- Database access for listings and enriched data

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd finder-enrichment
```

2. Set up the development environment:
```bash
make setup           # Create virtual environment
make install-dev     # Install dependencies
# OR use the combined command:
make dev            # Does both setup and install-dev
```

3. Activate the virtual environment:
```bash
source venv/bin/activate
```

4. Set up environment variables (see Configuration section)

## Configuration

The application is configured via environment variables:

### Kafka Configuration
```bash
export KAFKA_BOOTSTRAP_SERVERS="localhost:9092"
export KAFKA_GROUP_ID="enrichment-orchestrator"
```

### Service Endpoints
```bash
export LISTINGS_DB_HOST="localhost"
export LISTINGS_DB_PORT="8001"
export DESCRIPTION_ANALYSER_HOST="localhost"
export DESCRIPTION_ANALYSER_PORT="8002"
export FLOORPLAN_ANALYSER_HOST="localhost"
export FLOORPLAN_ANALYSER_PORT="8003"
export IMAGE_ANALYSER_HOST="localhost"
export IMAGE_ANALYSER_PORT="8004"
export ENRICHED_DB_HOST="localhost"
export ENRICHED_DB_PORT="8005"
```

### AI Configuration
```bash
export AI_PROVIDER="google"
export GOOGLE_GEMINI_API_KEY="your-api-key"
export AI_MODEL="gemini-2.0-flash"
```

### Processing Configuration
```bash
export MAX_WORKERS="4"
export ENABLE_PARALLEL_PROCESSING="true"
export PROCESSING_TIMEOUT="300"
export RETRY_ATTEMPTS="3"
```

### Logging Configuration
```bash
export LOG_LEVEL="INFO"
export ENABLE_FILE_LOGGING="true"
export LOG_FILE_PATH="logs/enrichment_orchestrator.log"
```

## Usage

### Basic Usage

Run the orchestrator with default configuration:
```bash
python -m finder_enrichment
```

### Advanced Usage

```bash
# Custom worker count
python -m finder_enrichment --max-workers 8

# Custom Kafka servers
python -m finder_enrichment --kafka-servers localhost:9092,localhost:9093

# Debug logging
python -m finder_enrichment --log-level DEBUG

# Create Kafka topics (first-time setup)
python -m finder_enrichment --create-topics

# Health check
python -m finder_enrichment --health-check

# Consume specific topics
python -m finder_enrichment --topics finder.harvester.property.discovered finder.harvester.property.updated
```

### Docker Usage

```bash
# Build image
docker build -t finder-enrichment .

# Run container
docker run -d \
  --name finder-enrichment \
  -e KAFKA_BOOTSTRAP_SERVERS="kafka:9092" \
  -e GOOGLE_GEMINI_API_KEY="your-key" \
  finder-enrichment
```

## Development

### Setup Development Environment

```bash
# Initial setup (creates venv and installs dependencies)
make dev

# Or step by step:
make setup           # Create virtual environment
make install-dev     # Install dependencies

# Activate the environment
source venv/bin/activate
```

### Dependency Management

```bash
# When local dependencies are problematic:
make reinstall       # Clean and reinstall dependencies

# For serious issues:
make full-reset      # Nuclear option: delete everything and start fresh

# Check environment status
make status          # Show venv and dependency status
make check-deps      # Verify local dependencies are installed
```

### Run Tests

```bash
make test
```

### Code Formatting

```bash
make format
```

### Linting

```bash
make lint
```

### Type Checking

```bash
make type-check
```

### Cleaning Up

```bash
make clean           # Clean build artifacts (keeps venv)
make deep-clean      # Remove everything including virtual environment
```

## Project Structure

```
finder-enrichment/
├── src/
│   └── finder_enrichment/
│       ├── __init__.py           # Main package
│       ├── __main__.py           # CLI entry point
│       ├── orchestrator.py       # Main orchestrator class
│       ├── config.py             # Configuration management
│       ├── kafka/                # Kafka integration
│       │   ├── __init__.py
│       │   ├── kafka_manager.py
│       │   ├── kafka_consumer.py
│       │   ├── kafka_producer.py
│       │   └── kafka_config.py
│       ├── agents_sdk_poc/       # AI agent proof-of-concept
│       └── tests/                # Test suite
├── pyproject.toml               # Project configuration
├── requirements.txt             # Dependencies
├── Makefile                     # Development tasks
└── README.md                    # Documentation
```

## API Integration

The orchestrator expects service clients to implement the following interfaces:

### Description Analyser Client
```python
class DescriptionAnalyserClient:
    def analyse_description(self, description: str) -> Dict[str, Any]:
        """Analyse property description and return insights."""
        pass
```

### Floorplan Analyser Client
```python
class FloorplanAnalyserClient:
    def analyse_floorplan_url(self, url: str) -> Dict[str, Any]:
        """Analyse floorplan from URL."""
        pass
    
    def analyse_floorplan_data(self, data: bytes) -> Dict[str, Any]:
        """Analyse floorplan from raw data."""
        pass
```

### Image Analyser Client
```python
class ImageAnalyserClient:
    def analyse_images(self, image_urls: List[str]) -> Dict[str, Any]:
        """Analyse property images."""
        pass
```

### Database Clients
```python
class EnrichedDbClient:
    def store_enrichment_result(self, result: EnrichmentResult) -> None:
        """Store enrichment results."""
        pass
    
    def store_image_analysis(self, property_id: str, data: Dict[str, Any]) -> None:
        """Store image analysis results."""
        pass
```

## Kafka Message Formats

### Property Discovered
```json
{
  "property_id": "prop123",
  "title": "Beautiful 3-bed house",
  "description": "A lovely property...",
  "image_urls": ["http://example.com/img1.jpg"],
  "floorplan_url": "http://example.com/plan.pdf",
  "timestamp": 1234567890
}
```

### Property Updated
```json
{
  "property_id": "prop123",
  "updated_fields": ["description", "images"],
  "description": "Updated description...",
  "image_urls": ["http://example.com/new_img.jpg"],
  "timestamp": 1234567890
}
```

### Enrichment Completion
```json
{
  "property_id": "prop123",
  "enrichment_type": "description_analysis",
  "status": "completed",
  "processing_time": 1.5,
  "timestamp": 1234567890
}
```

## Monitoring

The orchestrator provides several monitoring capabilities:

### Health Checks
```bash
python -m finder_enrichment --health-check
```

### Statistics API
```python
orchestrator = EnrichmentOrchestrator()
stats = orchestrator.get_stats()
# Returns: {"is_running": True, "processed_count": 100, "error_count": 2, "success_rate": 0.98}
```

### Logging
- Console logging with configurable levels
- File logging with rotation
- Structured logging for monitoring integration

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite: `make test`
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For questions or issues, please:

1. Check the documentation
2. Search existing issues
3. Create a new issue with detailed information
4. Contact the development team

## Roadmap

- [ ] Service client implementations
- [ ] Enhanced monitoring and metrics
- [ ] Configuration file support
- [ ] Kubernetes deployment manifests
- [ ] Performance optimization
- [ ] Additional enrichment types 