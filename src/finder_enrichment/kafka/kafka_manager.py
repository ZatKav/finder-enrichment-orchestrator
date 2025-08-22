"""
High-level Kafka manager for the Finder project.
"""
from typing import List, Optional

from .kafka_config import KafkaConfig, get_kafka_config
from .kafka_producer import KafkaProducer
from .kafka_consumer import KafkaConsumer
from ..logger_config import setup_logger

logger = setup_logger(__name__)


class KafkaManager:
    """High-level Kafka manager for the Finder project."""
    
    def __init__(self, config: Optional[KafkaConfig] = None):
        """Initialize Kafka manager."""
        self.config = config or get_kafka_config()
        logger.info("Kafka manager initialized - admin functionality removed as this service should not create topics")
        
    def get_producer(self) -> KafkaProducer:
        """Get a Kafka producer instance."""
        return KafkaProducer(self.config)
    
    def get_consumer(self, topics: List[str], group_id: Optional[str] = None) -> KafkaConsumer:
        """Get a Kafka consumer instance."""
        return KafkaConsumer(topics, group_id, self.config)
    
    async def health_check(self) -> bool:
        """Check if Kafka cluster is healthy by attempting to create a test producer."""
        try:
            # Try to create a producer to test connectivity
            test_producer = KafkaProducer(self.config)
            await test_producer.start()
            await test_producer.close()
            logger.debug("Kafka health check passed - producer connection successful")
            return True
        except Exception as e:
            logger.error(f"Kafka health check failed: {e}")
            return False 