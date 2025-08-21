"""
Main entry point for the Finder Enrichment Orchestrator.

This module provides the main entry point for running the orchestrator.
"""

import os
import sys
from typing import Optional

from dotenv import load_dotenv

from finder_enrichment.agentic_services.description_analyser.description_analyser_agent import DescriptionAnalyserAgent
from finder_enrichment.logger_config import setup_logger

from .config import get_config, EnrichmentConfig
from .orchestrator import EnrichmentOrchestrator
from .kafka import KafkaManager
from .kafka.kafka_config import KafkaConfig
from finder_enrichment_db_client import FinderEnrichmentDBAPIClient
from listings_db_api_client.listings_db_api_client import ListingsDBAPIClient

def main():
    """Main entry point."""
    # Set up logging first to capture all messages
    config = get_config()
    logger = setup_logger('finder_enrichment_orchestrator')
    load_dotenv()

    try:
        logger.info("Starting Finder Enrichment processing run.")
        logger.debug(f"Configuration: {config}")
        
        # Create Kafka manager
        kafka_config_obj = KafkaConfig(
            bootstrap_servers=config.kafka_bootstrap_servers
        )
        kafka_manager = KafkaManager(config=kafka_config_obj)
        
        # Create orchestrator
        orchestrator = EnrichmentOrchestrator(
            kafka_manager=kafka_manager,
            max_workers=config.max_workers,
            enable_parallel_processing=config.enable_parallel_processing
        )
        
        # Initialize and inject service clients
        # This would be done after the service clients are available
        orchestrator.set_service_clients(
            listings_db_client=ListingsDBAPIClient(api_key=os.getenv("LISTINGS_DB_API_KEY"), base_url=os.getenv("LISTINGS_DB_BASE_URL")),
            description_analyser_client=DescriptionAnalyserAgent(),
            floorplan_analyser_client=None,
            image_analyser_client=None,
            enriched_db_client=FinderEnrichmentDBAPIClient(api_key=os.getenv("ENRICHMENT_DB_API_KEY"), base_url=os.getenv("ENRICHMENT_DB_BASE_URL"))
        )
        
        logger.info("Service clients initialized. Starting message processing.")
        
        # Run the orchestrator to process all available messages
        orchestrator.process_messages_from_topics(["finder.harvester.property.discovered"])
        
        logger.info("Enrichment processing run completed successfully.")
        
    except Exception as e:
        logger.error(f"An error occurred during the enrichment process: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main() 