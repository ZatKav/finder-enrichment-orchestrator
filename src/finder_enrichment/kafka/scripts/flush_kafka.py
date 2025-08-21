#!/usr/bin/env python3
"""
Script to flush Kafka topics for the Finder project.
Useful for testing and development.
"""
import argparse
import sys
import os
from typing import List, Optional

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from confluent_kafka.admin import AdminClient, NewTopic
from confluent_kafka import KafkaException

from ..kafka_manager import KafkaManager
from ..kafka_config import KafkaConfig, Topics
from ...logger_config import setup_logger

logger = setup_logger(__name__)


class KafkaFlusher:
    """Utility to flush Kafka topics."""
    
    def __init__(self):
        """Initialize Kafka flusher."""
        self.kafka_manager = KafkaManager()
        self.admin_client = self.kafka_manager.admin_client
        
    def list_topics(self) -> List[str]:
        """List all available topics."""
        try:
            metadata = self.admin_client.list_topics(timeout=10)
            topics = list(metadata.topics.keys())
            # Filter out internal topics
            finder_topics = [topic for topic in topics if topic.startswith('finder.')]
            return finder_topics
        except Exception as e:
            logger.error(f"Failed to list topics: {e}")
            return []
    
    def flush_topic(self, topic_name: str) -> bool:
        """
        Flush a specific topic by deleting and recreating it.
        
        Args:
            topic_name: Name of the topic to flush
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Flushing topic: {topic_name}")
            
            # Get topic metadata to preserve partitions and replication factor
            metadata = self.admin_client.list_topics(timeout=10)
            if topic_name not in metadata.topics:
                logger.warning(f"Topic {topic_name} does not exist")
                return False
            
            topic_metadata = metadata.topics[topic_name]
            num_partitions = len(topic_metadata.partitions)
            
            # Delete the topic
            logger.debug(f"Deleting topic {topic_name}")
            delete_future = self.admin_client.delete_topics([topic_name], operation_timeout=30)
            
            # Wait for deletion
            for topic, future in delete_future.items():
                try:
                    future.result()
                    logger.debug(f"Topic {topic} deleted successfully")
                except Exception as e:
                    logger.error(f"Failed to delete topic {topic}: {e}")
                    return False
            
            # Recreate the topic
            logger.debug(f"Recreating topic {topic_name}")
            new_topic = NewTopic(topic_name, num_partitions=num_partitions, replication_factor=1)
            create_future = self.admin_client.create_topics([new_topic])
            
            # Wait for creation
            for topic, future in create_future.items():
                try:
                    future.result()
                    logger.info(f"Topic {topic} recreated successfully")
                    return True
                except Exception as e:
                    logger.error(f"Failed to recreate topic {topic}: {e}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to flush topic {topic_name}: {e}")
            return False
    
    def flush_all_finder_topics(self) -> bool:
        """Flush all Finder project topics."""
        topics = self.list_topics()
        if not topics:
            logger.info("No Finder topics found to flush")
            return True
        
        logger.info(f"Flushing all Finder topics: {topics}")
        success = True
        
        for topic in topics:
            if not self.flush_topic(topic):
                success = False
        
        return success
    
    def flush_topics_by_pattern(self, pattern: str) -> bool:
        """
        Flush topics matching a pattern.
        
        Args:
            pattern: Pattern to match (e.g., 'harvester', 'image', 'search')
        """
        topics = self.list_topics()
        matching_topics = [topic for topic in topics if pattern.lower() in topic.lower()]
        
        if not matching_topics:
            logger.info(f"No topics found matching pattern: {pattern}")
            return True
        
        logger.info(f"Flushing topics matching '{pattern}': {matching_topics}")
        success = True
        
        for topic in matching_topics:
            if not self.flush_topic(topic):
                success = False
        
        return success


def main():
    """Main function for the flush script."""
    parser = argparse.ArgumentParser(description='Flush Kafka topics for the Finder project')
    parser.add_argument(
        '--topic', '-t',
        help='Specific topic to flush'
    )
    parser.add_argument(
        '--pattern', '-p',
        help='Flush topics matching this pattern (e.g., "harvester", "image")'
    )
    parser.add_argument(
        '--all', '-a',
        action='store_true',
        help='Flush all Finder topics'
    )
    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='List all available Finder topics'
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
    if args.list:
        topics = flusher.list_topics()
        if topics:
            print("\nAvailable Finder topics:")
            for topic in topics:
                print(f"  - {topic}")
        else:
            print("No Finder topics found")
        return True
    
    # Validate arguments
    if not any([args.topic, args.pattern, args.all]):
        parser.print_help()
        print("\nError: Must specify --topic, --pattern, --all, or --list")
        return False
    
    # Determine topics to flush
    topics_to_flush = []
    if args.all:
        topics_to_flush = flusher.list_topics()
    elif args.pattern:
        topics_to_flush = [topic for topic in flusher.list_topics() if args.pattern.lower() in topic.lower()]
    elif args.topic:
        topics_to_flush = [args.topic]
    
    if not topics_to_flush:
        logger.info("No topics to flush.")
        return True

    logger.info(f"Flushing topics: {topics_to_flush}")
    success = True
    
    for topic in topics_to_flush:
        if not flusher.flush_topic(topic):
            success = False
    
    if success:
        logger.info("Flush operation completed successfully")
    else:
        logger.error("Flush operation completed with errors")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 