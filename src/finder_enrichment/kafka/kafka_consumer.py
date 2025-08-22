"""
Kafka consumer wrapper for the Finder project.
"""
import json
import asyncio
from typing import Dict, Any, Optional, Callable, List
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError

from .kafka_config import KafkaConfig, get_kafka_config
from ..logger_config import setup_logger

logger = setup_logger(__name__)


class KafkaConsumer:
    """Kafka consumer wrapper."""
    
    def __init__(self, topics: List[str], group_id: Optional[str] = None, config: Optional[KafkaConfig] = None):
        """
        Initialize Kafka consumer.
        
        Args:
            topics: List of topics to subscribe to
            group_id: Consumer group ID (overrides config default)
            config: Kafka configuration
        """
        self.config = config or get_kafka_config()
        self.topics = topics
        
        # Override group_id if provided
        consumer_config = self.config.consumer_config.copy()
        if group_id:
            consumer_config['group_id'] = group_id
            
        # Ensure that new consumer groups read from the start of the topic
        consumer_config['auto_offset_reset'] = 'earliest'
        
        # Convert confluent-kafka config keys to aiokafka format
        aiokafka_config = self._convert_config(consumer_config)
            
        self.consumer = AIOKafkaConsumer(*topics, **aiokafka_config)
        
        logger.info(f"Kafka consumer initialized for topics: {topics}")
    
    def _convert_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Convert confluent-kafka config keys to aiokafka format."""
        config_mapping = {
            'bootstrap.servers': 'bootstrap_servers',
            'group.id': 'group_id',
            'auto.offset.reset': 'auto_offset_reset',
            'enable.auto.commit': 'enable_auto_commit',
            'auto.commit.interval.ms': 'auto_commit_interval_ms',
            'session.timeout.ms': 'session_timeout_ms',
            'heartbeat.interval.ms': 'heartbeat_interval_ms',
        }
        
        converted = {}
        for old_key, new_key in config_mapping.items():
            if old_key in config:
                converted[new_key] = config[old_key]
        
        return converted
    
    async def start(self):
        """Start the consumer."""
        await self.consumer.start()
    
    async def consume_messages(self, message_handler: Callable[[str, Dict[str, Any]], None], 
                              timeout: float = 1.0) -> None:
        """
        Consume messages from subscribed topics.
        
        Args:
            message_handler: Function to handle received messages (topic, message_dict)
            timeout: Polling timeout in seconds
        """
        try:
            await self.start()
            
            async for message in self.consumer:
                try:
                    # Deserialize message
                    message_data = json.loads(message.value.decode('utf-8'))
                    topic = message.topic
                    
                    # Handle message
                    message_handler(topic, message_data)
                    
                    logger.debug(f"Processed message from topic {topic}")
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode message from topic {message.topic}: {e}")
                except Exception as e:
                    logger.error(f"Error handling message from topic {message.topic}: {e}")
                    
        except KeyboardInterrupt:
            logger.info("Consumer interrupted by user")
        except Exception as e:
            logger.error(f"Consumer error: {e}")
            raise
        finally:
            await self.close()
    
    async def consume_all_available_messages(self, poll_timeout: float = 5.0) -> List[Dict[str, Any]]:
        """
        Consumes all available messages from the subscribed topics and returns them as a list.

        This method will poll until no new messages are received within the timeout period,
        ensuring the topic queue is drained before returning.

        Args:
            poll_timeout: The time in seconds to wait for messages in a single poll.

        Returns:
            A list of messages, where each message is a dictionary containing the topic and data.
        """
        messages = []
        
        try:
            await self.start()
            
            # Poll for messages with timeout
            message_batch = await self.consumer.getmany(timeout_ms=int(poll_timeout * 1000), max_records=100)
            
            for tp, records in message_batch.items():
                for record in records:
                    try:
                        message_data = json.loads(record.value.decode('utf-8'))
                        messages.append({"topic": record.topic, "data": message_data})
                    except (json.JSONDecodeError, UnicodeDecodeError) as e:
                        logger.error(f"Error decoding message from topic {record.topic}: {e}")
                
                # Continue polling for remaining messages
                while True:
                    remaining_batch = await self.consumer.getmany(timeout_ms=100, max_records=100)
                    if not remaining_batch:
                        break
                        
                    for tp, records in remaining_batch.items():
                        for record in records:
                            try:
                                message_data = json.loads(record.value.decode('utf-8'))
                                messages.append({"topic": record.topic, "data": message_data})
                            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                                logger.error(f"Error decoding message from topic {record.topic}: {e}")

        except Exception as e:
            logger.error(f"An unexpected error occurred while consuming all messages: {e}", exc_info=True)
            # We will not re-raise here, but return any messages found so far
        
        logger.info(f"No more messages found in topic(s). Total messages: {len(messages)}")
        return messages

    async def close(self) -> None:
        """Close the consumer."""
        await self.consumer.stop() 