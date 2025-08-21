"""
Kafka consumer wrapper for the Finder project.
"""
import json
from typing import Dict, Any, Optional, Callable, List
from confluent_kafka import Consumer, KafkaError

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
            consumer_config['group.id'] = group_id
            
        # Ensure that new consumer groups read from the start of the topic
        consumer_config['auto.offset.reset'] = 'earliest'
            
        self.consumer = Consumer(consumer_config)
        self.consumer.subscribe(topics)
        
        logger.info(f"Kafka consumer initialized for topics: {topics}")
    
    def consume_messages(self, message_handler: Callable[[str, Dict[str, Any]], None], 
                        timeout: float = 1.0) -> None:
        """
        Consume messages from subscribed topics.
        
        Args:
            message_handler: Function to handle received messages (topic, message_dict)
            timeout: Polling timeout in seconds
        """
        try:
            while True:
                msg = self.consumer.poll(timeout)
                
                if msg is None:
                    continue
                    
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        logger.debug(f"Reached end of partition {msg.partition()}")
                        continue
                    else:
                        logger.error(f"Consumer error: {msg.error()}")
                        continue
                
                try:
                    # Deserialize message
                    message_data = json.loads(msg.value().decode('utf-8'))
                    topic = msg.topic()
                    
                    # Handle message
                    message_handler(topic, message_data)
                    
                    logger.debug(f"Processed message from topic {topic}")
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode message from topic {msg.topic()}: {e}")
                except Exception as e:
                    logger.error(f"Error handling message from topic {msg.topic()}: {e}")
                    
        except KeyboardInterrupt:
            logger.info("Consumer interrupted by user")
        except Exception as e:
            logger.error(f"Consumer error: {e}")
            raise
        finally:
            self.close()
    
    def consume_all_available_messages(self, poll_timeout: float = 5.0) -> List[Dict[str, Any]]:
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
        
        # Set a very low timeout for subsequent polls to quickly drain the queue
        fast_poll_timeout = 0.1 
        
        # First poll with a longer timeout to wait for messages to arrive
        current_timeout = poll_timeout

        try:
            while True:
                msg = self.consumer.poll(current_timeout)
                
                if msg is None:
                    # No message received, stop polling.
                    logger.info("No more messages found in topic(s).")
                    break
                
                # After the first message, switch to a fast poll to drain remaining messages quickly
                current_timeout = fast_poll_timeout

                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        # End of partition, this is informational, not an error.
                        continue
                    else:
                        logger.error(f"Kafka error: {msg.error()}")
                        continue
                
                try:
                    message_data = json.loads(msg.value().decode('utf-8'))
                    messages.append({"topic": msg.topic(), "data": message_data})
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    logger.error(f"Error decoding message from topic {msg.topic()}: {e}")

        except Exception as e:
            logger.error(f"An unexpected error occurred while consuming all messages: {e}", exc_info=True)
            # We will not re-raise here, but return any messages found so far
        
        return messages

    def close(self) -> None:
        """Close the consumer."""
        self.consumer.close() 