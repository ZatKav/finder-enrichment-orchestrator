"""
Kafka configuration for the Finder project services.
"""
import os
from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class KafkaConfig:
    """Kafka configuration settings."""
    
    # Broker settings
    bootstrap_servers: str = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    
    # Producer settings
    producer_config: Dict[str, Any] = None
    
    # Consumer settings
    consumer_config: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize default configurations."""
        if self.producer_config is None:
            self.producer_config = {
                'bootstrap.servers': self.bootstrap_servers,
                'client.id': 'finder-producer',
                'acks': 'all',  # Wait for all replicas to acknowledge
                'retries': 3,
                'retry.backoff.ms': 1000,
                'compression.type': 'snappy',
                'batch.size': 16384,
                'linger.ms': 10,  # Small delay to allow batching
            }
        
        if self.consumer_config is None:
            self.consumer_config = {
                'bootstrap.servers': self.bootstrap_servers,
                'group.id': 'finder-consumers',
                'auto.offset.reset': 'latest',
                'enable.auto.commit': True,
                'auto.commit.interval.ms': 5000,
                'session.timeout.ms': 30000,
                'heartbeat.interval.ms': 3000,
            }


# Topic definitions for different services
class Topics:
    """Kafka topic names for different message types."""
    
    # Harvester topics
    PROPERTY_DISCOVERED = 'finder.harvester.property.discovered'
    PROPERTY_UPDATED = 'finder.harvester.property.updated'
    HARVESTING_STATUS = 'finder.harvester.status'
    
    # Image processing topics
    IMAGE_DOWNLOAD_REQUESTED = 'finder.images.download.requested'
    IMAGE_PROCESSED = 'finder.images.processed'
    
    # Search topics
    SEARCH_REQUESTED = 'finder.search.requested'
    SEARCH_RESULTS = 'finder.search.results'
    
    # System topics
    SYSTEM_HEALTH = 'finder.system.health'
    SYSTEM_ERRORS = 'finder.system.errors'


def get_kafka_config() -> KafkaConfig:
    """Get Kafka configuration instance."""
    return KafkaConfig() 