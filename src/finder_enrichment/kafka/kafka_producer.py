"""
Kafka producer wrapper for the Finder project.
"""
import json
from typing import Dict, Any, Optional
from confluent_kafka import Producer, KafkaError

from .kafka_config import KafkaConfig, get_kafka_config
from ..logger_config import setup_logger

logger = setup_logger(__name__)


class KafkaProducer:
    """Kafka producer wrapper."""
    
    def __init__(self, config: Optional[KafkaConfig] = None):
        """Initialize Kafka producer."""
        self.config = config or get_kafka_config()
        self.producer = Producer(self.config.producer_config)
        
    def produce_message(self, topic: str, message: Dict[str, Any], key: Optional[str] = None) -> None:
        """
        Produce a message to a Kafka topic.
        
        Args:
            topic: Kafka topic name
            message: Message payload as dictionary
            key: Optional message key for partitioning
        """
        try:
            # Serialize message to JSON
            message_bytes = json.dumps(message).encode('utf-8')
            key_bytes = key.encode('utf-8') if key else None
            
            # Produce message
            self.producer.produce(
                topic=topic,
                value=message_bytes,
                key=key_bytes,
                callback=self._delivery_callback
            )
            
            # Trigger delivery callbacks
            self.producer.poll(0)
            
        except Exception as e:
            logger.error(f"Error producing message to topic {topic}: {e}")
            raise
    
    def _delivery_callback(self, err: Optional[KafkaError], msg) -> None:
        """Callback for message delivery confirmation."""
        if err:
            logger.error(f"Message delivery failed: {err}")
        else:
            logger.debug(f"Message delivered to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}")
    
    def flush(self, timeout: float = 10.0) -> None:
        """Wait for all messages to be delivered."""
        self.producer.flush(timeout)
    
    def close(self) -> None:
        """Close the producer."""
        self.producer.flush() 