"""
Finder Enrichment Orchestrators

Property listing enrichment orchestrators that process listings through various
analysis services including:
- Listings description analysis
- Floorplan analysis  
- Image analysis
- AI-powered curation and profiling

Two orchestrator types are available:
- KafkaEnrichmentOrchestrator: Real-time processing from Kafka topics
- DatabaseEnrichmentOrchestrator: Batch processing from database listings
"""

__version__ = "0.1.0"

# Import main components for easy access
from .kafka import KafkaManager, KafkaConsumer, KafkaProducer
from .orchestrator.base_orchestrator import BaseEnrichmentOrchestrator
from .kafka_orchestrator import KafkaEnrichmentOrchestrator
from .orchestrator.database_orchestrator import DatabaseEnrichmentOrchestrator

__all__ = [
    "KafkaManager",
    "KafkaConsumer", 
    "KafkaProducer",
    "BaseEnrichmentOrchestrator",
    "KafkaEnrichmentOrchestrator",
    "DatabaseEnrichmentOrchestrator",
] 