#!/usr/bin/env python3
"""
Example usage of the Database Enrichment Orchestrator.

This script demonstrates how to use the DatabaseEnrichmentOrchestrator
to process all listings from a database in batch mode.
"""

import sys
import os

# Add the src directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from finder_enrichment.orchestrator.database_orchestrator import DatabaseEnrichmentOrchestrator
from finder_enrichment.agentic_services.description_analyser.description_analyser_agent import DescriptionAnalyserAgent
from finder_enrichment.logger_config import setup_logger

# Import the db clients
from finder_enrichment_db_client import FinderEnrichmentDBAPIClient
from listings_db_api_client.listings_db_api_client import ListingsDBAPIClient

ENRICHMENT_DB_BASE_URL = os.getenv("ENRICHMENT_DB_BASE_URL", "http://localhost:8200")
ENRICHMENT_DB_API_KEY = os.getenv("ENRICHMENT_DB_API_KEY")

LISTINGS_DB_BASE_URL = os.getenv("LISTINGS_DB_BASE_URL", "http://localhost:8000")
LISTINGS_DB_API_KEY = os.getenv("LISTINGS_DB_API_KEY")


def main():
    """Main execution function."""
    logger = setup_logger(__name__)
    
    logger.info("Starting Database Enrichment Orchestrator example")
    
    try:
        # Initialize the database orchestrator
        orchestrator = DatabaseEnrichmentOrchestrator(
            max_workers=4,
            enable_parallel_processing=True,
            batch_size=50  # Process 50 listings at a time
        )
        
        # Setup service clients
        # Note: You'll need to configure these with your actual database URLs and credentials
        listings_db_client = ListingsDBAPIClient(
            base_url=LISTINGS_DB_BASE_URL,
            api_key=LISTINGS_DB_API_KEY
        )
        
        enriched_db_client = FinderEnrichmentDBAPIClient(
            base_url=ENRICHMENT_DB_BASE_URL,
            api_key=ENRICHMENT_DB_API_KEY
        )
        
        # Initialize description analyser
        description_analyser = DescriptionAnalyserAgent()
        
        # Configure the orchestrator with service clients
        orchestrator.set_service_clients(
            listings_db_client=listings_db_client,
            description_analyser_client=description_analyser,
            enriched_db_client=enriched_db_client
        )
        
        # Example 1: Process all listings in the database
        logger.info("Example 1: Processing all listings from database")
        orchestrator.process_all_listings()
        
        # Get and display statistics
        stats = orchestrator.get_database_stats()
        logger.info(f"Processing complete. Statistics: {stats}")
        
    except KeyboardInterrupt:
        logger.info("Processing interrupted by user")
    except Exception as e:
        logger.error(f"Error during processing: {e}", exc_info=True)
        sys.exit(1)


def example_process_specific_listings():
    """Example of processing specific listings by ID."""
    logger = setup_logger(__name__)
    
    logger.info("Example: Processing specific listings by ID")
    
    try:
        # Initialize orchestrator
        orchestrator = DatabaseEnrichmentOrchestrator(batch_size=10)
        
        # Setup service clients (same as above)
        listings_db_client = ListingsDBAPIClient(
            base_url=LISTINGS_DB_BASE_URL,
            api_key=LISTINGS_DB_API_KEY
        )
        enriched_db_client = FinderEnrichmentDBAPIClient(
            base_url=ENRICHMENT_DB_BASE_URL,
            api_key=ENRICHMENT_DB_API_KEY
        )
        description_analyser = DescriptionAnalyserAgent()
        
        orchestrator.set_service_clients(
            listings_db_client=listings_db_client,
            description_analyser_client=description_analyser,
            enriched_db_client=enriched_db_client
        )
        
        # Process specific listings
        listing_ids = ["listing_1", "listing_2", "listing_3"]  # Replace with actual IDs
        orchestrator.process_listings_by_ids(listing_ids)
        
        stats = orchestrator.get_database_stats()
        logger.info(f"Specific listings processing complete. Statistics: {stats}")
        
    except Exception as e:
        logger.error(f"Error during specific listings processing: {e}", exc_info=True)


def example_limited_processing():
    """Example of processing a limited number of listings (useful for testing)."""
    logger = setup_logger(__name__)
    
    logger.info("Example: Processing limited number of listings (testing)")
    
    try:
        # Initialize orchestrator
        orchestrator = DatabaseEnrichmentOrchestrator(
            batch_size=5  # Small batch size for testing
        )
        
        # Setup service clients
        listings_db_client = ListingsDBAPIClient(
            base_url=LISTINGS_DB_BASE_URL,
            api_key=LISTINGS_DB_API_KEY
        )
        enriched_db_client = FinderEnrichmentDBAPIClient(
            base_url=ENRICHMENT_DB_BASE_URL,
            api_key=ENRICHMENT_DB_API_KEY
        )
        description_analyser = DescriptionAnalyserAgent()
        
        orchestrator.set_service_clients(
            listings_db_client=listings_db_client,
            description_analyser_client=description_analyser,
            enriched_db_client=enriched_db_client
        )
        
        # Process only first 10 listings for testing
        logger.info("Processing first 10 listings for testing...")
        orchestrator.process_all_listings(limit=10)
        
        stats = orchestrator.get_database_stats()
        logger.info(f"Limited processing complete. Statistics: {stats}")
        
    except Exception as e:
        logger.error(f"Error during limited processing: {e}", exc_info=True)


if __name__ == "__main__":
    # Run the main example
    main()
    
    # Uncomment to run other examples:
    # example_process_specific_listings()
    # example_limited_processing() 