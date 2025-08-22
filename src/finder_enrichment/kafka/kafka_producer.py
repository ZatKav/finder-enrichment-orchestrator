"""
Kafka producer wrapper for the Finder project.
"""
import json
from typing import Dict, Any, Optional
from aiokafka import AIOKafkaProducer

from .kafka_config import KafkaConfig, get_kafka_config
from ..logger_config import setup_logger

logger = setup_logger(__name__)


class KafkaProducer:
    """Kafka producer wrapper."""
    
    def __init__(self, config: Optional[KafkaConfig] = None):
        """Initialize Kafka producer."""
        self.config = config or get_kafka_config()
        
        # Convert confluent-kafka config keys to aiokafka format
        aiokafka_config = self._convert_config(self.config.producer_config)
        
        self.producer = AIOKafkaProducer(**aiokafka_config)
        
    def _convert_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Convert confluent-kafka config keys to aiokafka format."""
        config_mapping = {
            'bootstrap.servers': 'bootstrap_servers',
            'client.id': 'client_id',
            'acks': 'acks',
            'retries': 'retries',
            'retry.backoff.ms': 'retry_backoff_ms',
            'compression.type': 'compression_type',
            'batch.size': 'batch_size',
            'linger.ms': 'linger_ms',
        }
        
        converted = {}
        for old_key, new_key in config_mapping.items():
            if old_key in config:
                converted[new_key] = config[old_key]
        
        return converted
    
    async def start(self):
        """Start the producer."""
        await self.producer.start()
        
    async def produce_message(self, topic: str, message: Dict[str, Any], key: Optional[str] = None) -> None:
        """
        Produce a message to a Kafka topic.
        
        Args:
            topic: Kafka topic name
            message: Message payload as dictionary
            key: Optional message key for partitioning
        """
        try:
            # Ensure producer is started
            if not self.producer._sender.sender_task:
                await self.start()
            
            # Serialize message to JSON
            message_bytes = json.dumps(message).encode('utf-8')
            key_bytes = key.encode('utf-8') if key else None
            
            # Produce message
            record_metadata = await self.producer.send_and_wait(
                topic=topic,
                value=message_bytes,
                key=key_bytes
            )
            
            logger.debug(f"Message delivered to {record_metadata.topic} [{record_metadata.partition}] at offset {record_metadata.offset}")
            
        except Exception as e:
            logger.error(f"Error producing message to topic {topic}: {e}")
            raise
    
    async def flush(self, timeout: float = 10.0) -> None:
        """Wait for all messages to be delivered."""
        await self.producer.flush(timeout=timeout)
    
    async def close(self) -> None:
        """Close the producer."""
        await self.producer.stop() 