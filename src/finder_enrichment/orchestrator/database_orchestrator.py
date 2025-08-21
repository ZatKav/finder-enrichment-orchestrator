"""
Database-based enrichment orchestrator that processes all listings from the database.
"""

from typing import List, Optional

from listings_db_contracts.schemas import ApiResponse, Listing

from finder_enrichment.orchestrator.base_orchestrator import BaseEnrichmentOrchestrator
from finder_enrichment.logger_config import setup_logger

logger = setup_logger(__name__)


class DatabaseEnrichmentOrchestrator(BaseEnrichmentOrchestrator):
    """
    Database-based enrichment orchestrator.
    
    Fetches all listings from the database and processes them through
    the enrichment pipeline. This is an alternative to Kafka-based processing
    for scenarios where you want to process existing data.
    """
    
    def __init__(
        self,
        max_workers: int = 4,
        enable_parallel_processing: bool = True,
        batch_size: int = 100
    ):
        """
        Initialize the database enrichment orchestrator.
        
        Args:
            max_workers: Maximum number of worker threads for parallel processing
            enable_parallel_processing: Whether to enable parallel processing of enrichments
            batch_size: Number of listings to fetch per batch from database
        """
        super().__init__(max_workers, enable_parallel_processing)
        self.batch_size = batch_size
        
    def process_all_listings(self, limit: Optional[int] = None) -> None:
        """
        Process all listings from the database.
        
        Args:
            limit: Optional limit on the number of listings to process (for testing)
        """
        if not self.enriched_db_client or not self.listings_db_client:
            raise RuntimeError("Both enriched DB client and listings DB client must be configured before starting.")

        try:
            # 1. Setup - Create orchestration set
            self._create_orchestration_set()
            self.is_running = True
            logger.info("Database enrichment orchestrator started")

            # 2. Fetch and process all listings
            total_processed = 0
            skip = 0
            
            while True:
                # Determine how many to fetch in this batch
                current_batch_size = self.batch_size
                if limit is not None:
                    remaining = limit - total_processed
                    if remaining <= 0:
                        break
                    current_batch_size = min(self.batch_size, remaining)

                logger.info(f"Fetching batch of {current_batch_size} listings (skip={skip})")
                
                # Fetch batch of listings
                try:
                    listings: List[Listing] = self.listings_db_client.get_listings(
                        skip=skip, 
                        limit=current_batch_size
                    )
                    
                    if not listings:
                        logger.info("No more listings found in database")
                        break
                        
                        
                    logger.info(f"Retrieved {len(listings)} listings from database")
                    
                    if len(listings) == 0:
                        logger.info("Empty batch received, stopping")
                        break
                        
                except Exception as e:
                    logger.error(f"Failed to fetch listings batch (skip={skip}, limit={current_batch_size}): {e}")
                    raise

                # Process each listing in the batch
                for listing in listings:
                    try:
                        success = self.process_single_listing(listing.id)
                        if success:
                            total_processed += 1
                            logger.info(f"Successfully processed listing {listing.id} ({total_processed} total)")
                        else:
                            logger.warning(f"Failed to process listing {listing.id}")
                    except Exception as e:
                        logger.error(f"Error processing listing {listing.id}: {e}", exc_info=True)
                        self.error_count += 1

                # Update skip for next batch
                skip += len(listings)
                
                # If we got fewer results than requested, we've reached the end
                if len(listings) < current_batch_size:
                    logger.info("Received fewer listings than requested, reached end of database")
                    break

            logger.info(f"Database processing completed. Processed {total_processed} listings total")

        except Exception as e:
            logger.error(f"Failed during database enrichment processing: {e}", exc_info=True)
            self.error_count += 1
            raise
        finally:
            # Cleanup
            self.is_running = False
            self.orchestration_set_id = None
            logger.info("Database enrichment orchestrator stopped.")
            
    def process_listings_by_ids(self, listing_ids: List[str]) -> None:
        """
        Process specific listings by their IDs.
        
        Args:
            listing_ids: List of listing IDs to process
        """
        if not self.enriched_db_client or not self.listings_db_client:
            raise RuntimeError("Both enriched DB client and listings DB client must be configured before starting.")

        try:
            # Setup - Create orchestration set
            self._create_orchestration_set()
            self.is_running = True
            logger.info(f"Database enrichment orchestrator started for {len(listing_ids)} specific listings")

            # Process each listing
            for listing_id in listing_ids:
                try:
                    success = self.process_single_listing(listing_id)
                    if success:
                        logger.info(f"Successfully processed listing {listing_id}")
                    else:
                        logger.warning(f"Failed to process listing {listing_id}")
                except Exception as e:
                    logger.error(f"Error processing listing {listing_id}: {e}", exc_info=True)
                    self.error_count += 1

            logger.info(f"Completed processing {len(listing_ids)} specific listings")

        except Exception as e:
            logger.error(f"Failed during specific listings enrichment processing: {e}", exc_info=True)
            self.error_count += 1
            raise
        finally:
            # Cleanup
            self.is_running = False
            self.orchestration_set_id = None
            logger.info("Database enrichment orchestrator stopped.")
            
    def get_database_stats(self) -> dict:
        """
        Get statistics about the database and processing.
        
        Returns:
            Dictionary containing database and processing statistics
        """
        stats = self.get_stats()
        
        # Add database-specific stats
        try:
            if self.listings_db_client:
                # Get total count of listings in database
                listings_response = self.listings_db_client.get_listings(skip=0, limit=1)
                if listings_response and hasattr(listings_response, 'total_count'):
                    stats['total_listings_in_database'] = listings_response.total_count
                else:
                    stats['total_listings_in_database'] = 'unknown'
            else:
                stats['total_listings_in_database'] = 'client_not_configured'
        except Exception as e:
            logger.warning(f"Could not fetch database statistics: {e}")
            stats['total_listings_in_database'] = 'error_fetching'
            
        stats['batch_size'] = self.batch_size
        return stats 