#!/usr/bin/env python3
"""
Script to list Kafka topics for the Finder project.
Useful for testing and development.
Note: This script now only lists topics since topic creation/deletion is not supported.
"""
import argparse
import sys
import os
from typing import List

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError

from ..kafka_manager import KafkaManager
from ..kafka_config import KafkaConfig, Topics
from ...logger_config import setup_logger

logger = setup_logger(__name__)


class KafkaFlusher:
    """Utility to list Kafka topics (admin operations removed)."""
    
    def __init__(self):
        """Initialize Kafka flusher."""
        self.kafka_manager = KafkaManager()
        # Note: Admin functionality removed - this service should not create/delete topics
        
    async def list_topics(self) -> List[str]:
        """List all available topics."""
        try:
            # Use aiokafka consumer to get topic metadata
            consumer = AIOKafkaConsumer(
                bootstrap_servers=self.kafka_manager.config.bootstrap_servers,
                group_id='topic-lister-temp'
            )
            
            await consumer.start()
            
            # Get cluster metadata
            cluster_metadata = await consumer._coordinator._client.fetch_all_metadata()
            topics = list(cluster_metadata.topics.keys())
            
            await consumer.stop()
            
            # Filter out internal topics
            finder_topics = [topic for topic in topics if topic.startswith('finder.')]
            return finder_topics
            
        except Exception as e:
            logger.error(f"Failed to list topics: {e}")
            return []
    
    async def list_all_topics(self) -> List[str]:
        """List all available topics (including non-Finder ones)."""
        try:
            # Use aiokafka consumer to get topic metadata
            consumer = AIOKafkaConsumer(
                bootstrap_servers=self.kafka_manager.config.bootstrap_servers,
                group_id='topic-lister-temp'
            )
            
            await consumer.start()
            
            # Get cluster metadata
            cluster_metadata = await consumer._coordinator._client.fetch_all_metadata()
            topics = list(cluster_metadata.topics.keys())
            
            await consumer.stop()
            return topics
            
        except Exception as e:
            logger.error(f"Failed to list all topics: {e}")
            return []


async def main():
    """Main function for the flush script."""
    parser = argparse.ArgumentParser(description='List Kafka topics for the Finder project')
    parser.add_argument(
        '--all', '-a',
        action='store_true',
        help='List all topics (not just Finder ones)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(10)  # DEBUG level
    
    # Initialize flusher
    try:
        flusher = KafkaFlusher()
    except Exception as e:
        logger.error(f"Failed to initialize Kafka connection: {e}")
        logger.info("Make sure Kafka is running: make kafka-start")
        return False
    
    # List topics
    if args.all:
        topics = await flusher.list_all_topics()
        if topics:
            print("\nAll available topics:")
            for topic in sorted(topics):
                print(f"  - {topic}")
        else:
            print("No topics found")
    else:
        topics = await flusher.list_topics()
        if topics:
            print("\nAvailable Finder topics:")
            for topic in sorted(topics):
                print(f"  - {topic}")
        else:
            print("No Finder topics found")
    
    print("\nNote: Topic creation/deletion functionality has been removed.")
    print("This service should only consume from and produce to existing topics.")
    
    return True


if __name__ == "__main__":
    import asyncio
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 