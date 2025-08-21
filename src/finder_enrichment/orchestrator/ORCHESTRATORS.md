# Finder Enrichment Orchestrators

This document explains the different orchestrator types available for processing property listings and when to use each one.

## Architecture Overview

The enrichment system has been refactored to separate concerns:

- **BaseEnrichmentOrchestrator**: Contains shared enrichment processing logic
- **KafkaEnrichmentOrchestrator**: Handles Kafka message retrieval + enrichment processing  
- **DatabaseEnrichmentOrchestrator**: Handles database listing retrieval + enrichment processing
- **EnrichmentOrchestrator**: Backwards-compatible alias for KafkaEnrichmentOrchestrator

## Orchestrator Types

### 1. KafkaEnrichmentOrchestrator

**Use for: Real-time processing of new/updated properties**

```python
from finder_enrichment import KafkaEnrichmentOrchestrator, KafkaManager

# Initialize
orchestrator = KafkaEnrichmentOrchestrator(
    kafka_manager=KafkaManager(),
    max_workers=4
)

# Setup clients
orchestrator.set_service_clients(
    listings_db_client=listings_client,
    description_analyser_client=description_analyser,
    enriched_db_client=enriched_client
)

# Process messages from Kafka topics
topics = ["finder.harvester.property.discovered"]
orchestrator.process_messages_from_topics(topics)
```

**Best for:**
- Real-time processing as properties are discovered
- Event-driven architecture
- Processing updates to existing listings
- Distributed systems with message queues

### 2. DatabaseEnrichmentOrchestrator  

**Use for: Batch processing of existing data**

```python
from finder_enrichment import DatabaseEnrichmentOrchestrator

# Initialize
orchestrator = DatabaseEnrichmentOrchestrator(
    batch_size=100,  # Process 100 listings at a time
    max_workers=4
)

# Setup clients
orchestrator.set_service_clients(
    listings_db_client=listings_client,
    description_analyser_client=description_analyser,
    enriched_db_client=enriched_client
)

# Option 1: Process all listings
orchestrator.process_all_listings()

# Option 2: Process specific listings
listing_ids = ["id1", "id2", "id3"]
orchestrator.process_listings_by_ids(listing_ids)

# Option 3: Process limited number (for testing)
orchestrator.process_all_listings(limit=50)
```

**Best for:**
- Bulk processing of existing data
- Re-processing after algorithm improvements
- Testing and development
- One-time data migrations
- Batch jobs and scheduled processing

## When to Use Which Orchestrator

| Scenario | Recommended Orchestrator | Reason |
|----------|-------------------------|---------|
| Real-time property enrichment | KafkaEnrichmentOrchestrator | Processes properties as they're discovered |
| Bulk reprocessing of existing data | DatabaseEnrichmentOrchestrator | Efficient batch processing with configurable batch sizes |
| Testing enrichment algorithms | DatabaseEnrichmentOrchestrator | Can limit processing to small sets for testing |
| Re-enriching after bug fixes | DatabaseEnrichmentOrchestrator | Can reprocess all or specific listings |
| Processing specific property sets | DatabaseEnrichmentOrchestrator | Supports processing by listing IDs |
| Event-driven microservices | KafkaEnrichmentOrchestrator | Integrates with message-driven architecture |

## Configuration

Both orchestrators support the same configuration options:

- `max_workers`: Number of parallel worker threads
- `enable_parallel_processing`: Whether to enable parallel enrichment processing

The DatabaseEnrichmentOrchestrator additionally supports:
- `batch_size`: Number of listings to fetch from database per batch

## Backwards Compatibility

The original `EnrichmentOrchestrator` class is now an alias for `KafkaEnrichmentOrchestrator`, so existing code will continue to work without changes.

## Error Handling

Both orchestrators provide comprehensive error handling and statistics:

```python
# Get processing statistics
stats = orchestrator.get_stats()  # Common stats

# Get orchestrator-specific stats
kafka_stats = kafka_orchestrator.get_kafka_stats()
db_stats = db_orchestrator.get_database_stats()
```

## Examples

See `scripts/example_usage.py` and `scripts/example_database_orchestrator.py` for complete working examples of both orchestrator types. 