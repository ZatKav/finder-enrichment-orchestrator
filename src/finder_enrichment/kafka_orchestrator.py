"""
Kafka-based enrichment orchestrator that processes messages from Kafka topics.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from .orchestrator.base_orchestrator import BaseEnrichmentOrchestrator
from .kafka import KafkaManager, KafkaConsumer, KafkaProducer
from .logger_config import setup_logger

logger = setup_logger(__name__)


class KafkaEnrichmentOrchestrator(BaseEnrichmentOrchestrator):
    """
    Kafka-based enrichment orchestrator.
    
    Polls Kafka topics for new property discovery messages and processes them
    through the enrichment pipeline. This is the original processing mode.
    """
    
    def __init__(
        self,
        kafka_manager: Optional[KafkaManager] = None,
        max_workers: int = 4,
        enable_parallel_processing: bool = True
    ):
        """
        Initialize the Kafka enrichment orchestrator.
        
        Args:
            kafka_manager: Kafka manager instance
            max_workers: Maximum number of worker threads for parallel processing
            enable_parallel_processing: Whether to enable parallel processing of enrichments
        """
        super().__init__(max_workers, enable_parallel_processing)
        self.kafka_manager = kafka_manager or KafkaManager()
        
        # Consumer and producer instances
        self.consumer: Optional[KafkaConsumer] = None
        self.producer: Optional[KafkaProducer] = None
        
        self.message_handlers = {
            "finder.harvester.property.discovered": self._handle_property_discovered,
        }
        
    def process_messages_from_topics(self, consumer_topics: List[str]):
        """
        Connects to Kafka, consumes all available messages from the specified topics,
        processes them, and then disconnects. This is a one-shot operation.

        Args:
            consumer_topics: List of Kafka topics to consume from.
        """
        if not self.enriched_db_client or not self.listings_db_client:
            raise RuntimeError("Enriched DB client and Listings DB client must be configured before starting.")

        try:
            # 1. Setup
            self._create_orchestration_set()

            # Generate a unique group_id for each batch run to ensure we re-read the topic
            batch_timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            group_id = f"enrichment-orchestrator-batch-{batch_timestamp}"

            self.consumer = self.kafka_manager.get_consumer(
                topics=consumer_topics,
                group_id=group_id
            )
            self.producer = self.kafka_manager.get_producer()
            self.is_running = True  # Set to true during processing
            logger.info(f"Kafka enrichment orchestrator started for batch processing from topics: {consumer_topics}")

            # 2. Consume all messages
            messages = self.consumer.consume_all_available_messages()
            logger.info(f"Found {len(messages)} messages to process.")

            # 3. Process all messages
            for msg in messages:
                self._process_message(msg["topic"], msg["data"])
            
            logger.info("Finished processing all messages.")

        except Exception as e:
            logger.error(f"Failed during Kafka enrichment processing: {e}", exc_info=True)
            self.error_count += 1
        finally:
            # 4. Teardown
            self.is_running = False
            self.orchestration_set_id = None
            if self.consumer:
                self.consumer.close()
            if self.producer:
                self.producer.close()
            logger.info("Kafka enrichment orchestrator stopped.")
            
    def _process_message(self, topic: str, message_data: Dict[str, Any]):
        """
        Process a single message from a Kafka topic.
        """
        if topic in self.message_handlers:
            handler = self.message_handlers[topic]
            handler(message_data)
        else:
            logger.warning(f"Unknown topic: {topic}")
            
    def _handle_property_discovered(self, message_data: Dict[str, Any]):
        """
        Handle a property discovered message from Kafka.
        """
        property_id = message_data.get("property_id")
        if property_id:
            self.process_single_listing(property_id)
        else:
            logger.warning("Received property_discovered message without a property_id.")
            
    def get_kafka_stats(self) -> Dict[str, Any]:
        """
        Get Kafka-specific statistics.
        
        Returns:
            Dictionary containing Kafka and processing statistics
        """
        stats = self.get_stats()
        
        # Add Kafka-specific stats
        stats['kafka_manager_configured'] = self.kafka_manager is not None
        stats['consumer_active'] = self.consumer is not None
        stats['producer_active'] = self.producer is not None
        
        # Check Kafka health if possible
        if self.kafka_manager:
            try:
                stats['kafka_cluster_healthy'] = self.kafka_manager.health_check()
            except Exception as e:
                logger.warning(f"Could not check Kafka health: {e}")
                stats['kafka_cluster_healthy'] = 'error_checking'
        else:
            stats['kafka_cluster_healthy'] = 'manager_not_configured'
            
        return stats 