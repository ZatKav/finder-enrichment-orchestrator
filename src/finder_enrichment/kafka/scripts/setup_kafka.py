#!/usr/bin/env python3
"""
Setup script for Kafka infrastructure for the Finder project.
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ..kafka_manager import KafkaManager
from ...logger_config import setup_logger

logger = setup_logger(__name__)


def main():
    """Set up Kafka topics for the Finder project."""
    try:
        logger.info("Initializing Kafka setup for Finder project...")
        
        # Initialize Kafka manager
        kafka_manager = KafkaManager()
        
        # Health check
        if not kafka_manager.health_check():
            logger.error("Kafka cluster is not accessible. Please ensure Kafka is running.")
            logger.info("To start Kafka, run: brew services start kafka")
            return False
        
        logger.info("Kafka cluster is accessible")
        
        # Create topics
        logger.info("Creating Kafka topics...")
        kafka_manager.create_topics()
        
        logger.info("Kafka setup completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Failed to set up Kafka: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 