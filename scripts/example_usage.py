#!/usr/bin/env python3
"""
Example usage of the Finder Enrichment Orchestrators.

This script demonstrates how to use both orchestrator types:
1. KafkaEnrichmentOrchestrator - for processing messages from Kafka topics
2. DatabaseEnrichmentOrchestrator - for processing all listings from database

Choose the appropriate orchestrator based on your use case:
- Kafka: Real-time processing of new/updated properties
- Database: Batch processing of existing data, reprocessing, testing
"""

import os
import sys
import time
from pathlib import Path

# Add src to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from finder_enrichment.orchestrator import EnrichmentOrchestrator  # Original (Kafka-based)
from finder_enrichment.kafka_orchestrator import KafkaEnrichmentOrchestrator
from finder_enrichment.orchestrator.database_orchestrator import DatabaseEnrichmentOrchestrator
from finder_enrichment.kafka import KafkaManager
from finder_enrichment.agentic_services.description_analyser.description_analyser_agent import DescriptionAnalyserAgent
from finder_enrichment.logger_config import setup_logger

# Import the db client
from finder_enrichment_db_client import FinderEnrichmentDBAPIClient
from listings_db_api_client.listings_db_api_client import ListingsDBAPIClient


ENRICHMENT_DB_BASE_URL = os.getenv("ENRICHMENT_DB_BASE_URL", "http://localhost:8200")
LISTINGS_DB_BASE_URL = os.getenv("LISTINGS_DB_BASE_URL", "http://localhost:8000")
ENRICHMENT_DB_API_KEY = os.getenv("ENRICHMENT_DB_API_KEY")
LISTINGS_DB_API_KEY = os.getenv("LISTINGS_DB_API_KEY")

logger = setup_logger(__name__)

def setup_service_clients():
    """Setup and return configured service clients."""
    logger.info("🔧 Setting up service clients...")
    
    # Database clients (replace URLs with your actual endpoints)
    listings_db_client = ListingsDBAPIClient(
        base_url=LISTINGS_DB_BASE_URL,
        api_key=LISTINGS_DB_API_KEY
    )
    
    enriched_db_client = FinderEnrichmentDBAPIClient(
        base_url=ENRICHMENT_DB_BASE_URL,
        api_key=ENRICHMENT_DB_API_KEY
    )
    
    # AI service clients
    description_analyser = DescriptionAnalyserAgent()
    
    # TODO: Add real image and floorplan analysers when available
    # image_analyser = ImageAnalyserClient()
    # floorplan_analyser = FloorplanAnalyserClient()
    
    return {
        'listings_db_client': listings_db_client,
        'enriched_db_client': enriched_db_client,
        'description_analyser': description_analyser,
        'image_analyser': None,  # TODO: Replace with real client
        'floorplan_analyser': None  # TODO: Replace with real client
    }


def example_kafka_orchestrator():
    """Example using Kafka orchestrator for real-time processing."""
    logger = setup_logger(__name__)
    logger.info("\n🔄 Example 1: Kafka Orchestrator (Real-time Processing)")
    logger.info("-" * 60)
    
    try:
        # Initialize Kafka orchestrator
        kafka_manager = KafkaManager()  # Uses default Kafka config
        orchestrator = KafkaEnrichmentOrchestrator(
            kafka_manager=kafka_manager,
            max_workers=4,
            enable_parallel_processing=True
        )
        
        # Setup service clients
        clients = setup_service_clients()
        orchestrator.set_service_clients(
            listings_db_client=clients['listings_db_client'],
            description_analyser_client=clients['description_analyser'],
            image_analyser_client=clients['image_analyser'],
            floorplan_analyser_client=clients['floorplan_analyser'],
            enriched_db_client=clients['enriched_db_client']
        )
        
        # Process messages from Kafka topics
        topics = ["finder.harvester.property.discovered"]
        logger.info(f"📡 Processing messages from Kafka topics: {topics}")
        
        orchestrator.process_messages_from_topics(topics)
        
        # Show statistics
        stats = orchestrator.get_kafka_stats()
        logger.info(f"📊 Kafka Processing Statistics: {stats}")
        
    except Exception as e:
        logger.error(f"❌ Kafka orchestrator example failed: {e}")
        logger.exception("Kafka example failed")


def example_database_orchestrator():
    """Example using Database orchestrator for batch processing."""
    logger = setup_logger(__name__)
    logger.info("\n💾 Example 2: Database Orchestrator (Batch Processing)")
    logger.info("-" * 60)
    
    try:
        # Initialize Database orchestrator
        orchestrator = DatabaseEnrichmentOrchestrator(
            max_workers=4,
            enable_parallel_processing=True,
            batch_size=50  # Process 50 listings at a time
        )
        
        # Setup service clients
        clients = setup_service_clients()
        orchestrator.set_service_clients(
            listings_db_client=clients['listings_db_client'],
            description_analyser_client=clients['description_analyser'],
            image_analyser_client=clients['image_analyser'],
            floorplan_analyser_client=clients['floorplan_analyser'],
            enriched_db_client=clients['enriched_db_client']
        )
        
        # Option 1: Process all listings in database
        logger.info("🔄 Processing all listings from database...")
        orchestrator.process_all_listings(limit=10)  # Limit for demo
        
        # Show statistics
        stats = orchestrator.get_database_stats()
        logger.info(f"📊 Database Processing Statistics: {stats}")
        
    except Exception as e:
        logger.error(f"❌ Database orchestrator example failed: {e}")
        logger.exception("Database example failed")


def example_specific_listings():
    """Example processing specific listings by ID."""
    logger = setup_logger(__name__)
    logger.info("\n🎯 Example 3: Processing Specific Listings")
    logger.info("-" * 60)
    
    try:
        # Initialize Database orchestrator for specific listings
        orchestrator = DatabaseEnrichmentOrchestrator(batch_size=10)
        
        # Setup service clients
        clients = setup_service_clients()
        orchestrator.set_service_clients(
            listings_db_client=clients['listings_db_client'],
            description_analyser_client=clients['description_analyser'],
            enriched_db_client=clients['enriched_db_client']
        )
        
        # Process specific listings (replace with actual listing IDs)
        specific_ids = ["listing_123", "listing_456", "listing_789"]
        logger.info(f"🔄 Processing specific listings: {specific_ids}")
        
        orchestrator.process_listings_by_ids(specific_ids)
        
        stats = orchestrator.get_database_stats()
        logger.info(f"📊 Specific Processing Statistics: {stats}")
        
    except Exception as e:
        logger.error(f"❌ Specific listings example failed: {e}")
        logger.exception("Specific listings example failed")


def main():
    """Main example function showing all orchestrator types."""
    logger.info("🚀 Finder Enrichment Orchestrators Examples")
    logger.info("=" * 60)
    logger.info("\nThis example demonstrates both orchestrator types:")
    logger.info("• Kafka Orchestrator: Real-time processing from message queue")
    logger.info("• Database Orchestrator: Batch processing from database")
    logger.info()
    
    logger = setup_logger(__name__)
    
    # Example 1: Kafka-based processing (for real-time scenarios)
    example_kafka_orchestrator()
    
    # Example 2: Database-based processing (for batch scenarios)
    example_database_orchestrator()
    
    # Example 3: Processing specific listings
    example_specific_listings()
    
    logger.info("\n🎉 All examples completed!")
    logger.info("\nChoose the right orchestrator for your use case:")
    logger.info("• Use KafkaEnrichmentOrchestrator for real-time processing")
    logger.info("• Use DatabaseEnrichmentOrchestrator for batch processing")
    logger.info("• The original EnrichmentOrchestrator is now an alias for KafkaEnrichmentOrchestrator")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n⏹️  Examples interrupted by user")
    except Exception as e:
        logger.error(f"❌ Examples failed: {e}")
        logger.exception("Examples failed")
        sys.exit(1) 