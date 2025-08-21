"""
High-level Kafka manager for the Finder project.
"""
from typing import List, Optional
from confluent_kafka.admin import AdminClient, NewTopic
from confluent_kafka import KafkaException

from .kafka_config import KafkaConfig, Topics, get_kafka_config
from .kafka_producer import KafkaProducer
from .kafka_consumer import KafkaConsumer
from ..logger_config import setup_logger

logger = setup_logger(__name__)


class KafkaManager:
    """High-level Kafka manager for the Finder project."""
    
    def __init__(self, config: Optional[KafkaConfig] = None):
        """Initialize Kafka manager."""
        self.config = config or get_kafka_config()
        self.admin_client = AdminClient({'bootstrap.servers': self.config.bootstrap_servers})
        
    def create_topics(self) -> None:
        """Create all required topics for the Finder project."""
        topics_to_create = [
            NewTopic(Topics.PROPERTY_DISCOVERED, num_partitions=3, replication_factor=1),
            NewTopic(Topics.PROPERTY_UPDATED, num_partitions=3, replication_factor=1),
            NewTopic(Topics.HARVESTING_STATUS, num_partitions=1, replication_factor=1),
            NewTopic(Topics.IMAGE_DOWNLOAD_REQUESTED, num_partitions=2, replication_factor=1),
            NewTopic(Topics.IMAGE_PROCESSED, num_partitions=2, replication_factor=1),
            NewTopic(Topics.SEARCH_REQUESTED, num_partitions=2, replication_factor=1),
            NewTopic(Topics.SEARCH_RESULTS, num_partitions=2, replication_factor=1),
            NewTopic(Topics.SYSTEM_HEALTH, num_partitions=1, replication_factor=1),
            NewTopic(Topics.SYSTEM_ERRORS, num_partitions=1, replication_factor=1),
        ]
        
        # Create topics
        future_map = self.admin_client.create_topics(topics_to_create)
        
        # Wait for topics to be created
        for topic, future in future_map.items():
            try:
                future.result()
                logger.info(f"Topic {topic} created successfully")
            except Exception as e:
                if "already exists" in str(e).lower():
                    logger.info(f"Topic {topic} already exists")
                else:
                    logger.error(f"Failed to create topic {topic}: {e}")
    
    def get_producer(self) -> KafkaProducer:
        """Get a Kafka producer instance."""
        return KafkaProducer(self.config)
    
    def get_consumer(self, topics: List[str], group_id: Optional[str] = None) -> KafkaConsumer:
        """Get a Kafka consumer instance."""
        return KafkaConsumer(topics, group_id, self.config)
    
    def health_check(self) -> bool:
        """Check if Kafka cluster is healthy."""
        try:
            # Listing topics is a lightweight way to check for broker connectivity.
            # A timeout is added to prevent hanging indefinitely.
            metadata = self.admin_client.list_topics(timeout=5.0)
            return metadata is not None and len(metadata.brokers) > 0
        except KafkaException as e:
            # Handle specific Kafka exceptions, e.g., if all brokers are down.
            logger.error(f"Kafka health check failed: {e}")
            return False
        except Exception as e:
            # Catch any other unexpected exceptions.
            logger.error(f"An unexpected error occurred during Kafka health check: {e}")
            return False 