"""
Synchronous enrichment service for property listings.

This service provides synchronous processing of property listings,
optimized for serverless environments without background job processing.
"""

import json
import time
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from listings_db_contracts.schemas import Listing as OriginalListing, EstateAgent as OriginalEstateAgent
from finder_enrichment_db_contracts import (
    ListingCreate,
    ImageCreateNested,
    LocationCreate,
    AddressCreate,
    DescriptionAnalyticsRunCreate,
    ImageAnalyticsRunCreate,
    EnrichmentOrchestrationSetCreate,
    EnrichmentOrchestrationRunCreate
)

from finder_enrichment.agentic_services.model_response import ModelResponse
from finder_enrichment.agentic_services.image_analyser.image_analyser import ImageAnalyser
from finder_enrichment.orchestrator.estate_agent_utils import get_or_create_estate_agent
from finder_enrichment.logger_config import setup_logger

logger = setup_logger(__name__)


class EnrichmentResult:
    """Result model for individual listing enrichment."""

    def __init__(
        self,
        listing_id: str,
        status: str,  # "success", "failed", "timeout"
        enriched_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        processing_time_seconds: float = 0.0,
        image_count: int = 0,
        timestamp: Optional[datetime] = None
    ):
        self.listing_id = listing_id
        self.status = status
        self.enriched_data = enriched_data
        self.error_message = error_message
        self.processing_time_seconds = processing_time_seconds
        self.image_count = image_count
        self.timestamp = timestamp or datetime.now(timezone.utc)


class BatchEnrichmentResult:
    """Result model for batch listing enrichment."""

    def __init__(
        self,
        results: List[EnrichmentResult],
        total_processed: int = 0,
        total_failed: int = 0,
        total_successful: int = 0,
        processing_time_seconds: float = 0.0
    ):
        self.results = results
        self.total_processed = total_processed
        self.total_failed = total_failed
        self.total_successful = total_successful
        self.processing_time_seconds = processing_time_seconds


class SynchronousEnrichmentService:
    """
    Synchronous enrichment service for property listings.

    This service processes listings synchronously without background jobs,
    making it suitable for serverless environments.
    """

    def __init__(self):
        """Initialize the synchronous enrichment service."""
        self.listings_db_client = None
        self.description_analyser_agent = None
        self.image_analyser_client = None
        self.enriched_db_client = None

    def set_service_clients(
        self,
        listings_db_client=None,
        description_analyser_client=None,
        image_analyser_client=None,
        enriched_db_client=None
    ):
        """Set the service clients needed for enrichment."""
        self.listings_db_client = listings_db_client
        self.description_analyser_agent = description_analyser_client
        self.image_analyser_client = image_analyser_client
        self.enriched_db_client = enriched_db_client

        # Initialize the image analyser if we have the required clients
        if self.listings_db_client and self.enriched_db_client:
            self.image_analyser = ImageAnalyser()
            # Set the clients on the image analyser
            self.image_analyser.listings_db_client = self.listings_db_client
            self.image_analyser.enriched_db_client = self.enriched_db_client

    def enrich_listing(self, listing_id: str) -> EnrichmentResult:
        """
        Enrich a single listing synchronously.

        Args:
            listing_id: The ID of the listing to enrich

        Returns:
            EnrichmentResult with the processing outcome
        """
        start_time = time.time()
        timestamp = datetime.now(timezone.utc)

        try:
            logger.info(f"Starting synchronous enrichment for listing: {listing_id}")

            # Validate service clients
            if not all([self.listings_db_client, self.description_analyser_agent,
                       self.image_analyser_client, self.enriched_db_client]):
                raise RuntimeError("All service clients must be configured")

            # 1. Fetch original listing data
            original_listing = self.listings_db_client.get_listing(listing_id=listing_id)

            # 2. Get or create Estate Agent
            original_agent = original_listing.estate_agent
            enriched_estate_agent_id = get_or_create_estate_agent(original_agent)
            if not enriched_estate_agent_id:
                raise RuntimeError("Could not get or create estate agent")

            # 3. Run enrichments
            description_response = self._enrich_description(original_listing.description)
            image_responses = self._enrich_images(original_listing.id) if original_listing.images else []

            # 4. Create enriched listing
            enriched_listing_create = self._build_enriched_listing(
                original_listing,
                enriched_estate_agent_id,
                description_response,
                image_responses
            )

            enriched_listing = self.enriched_db_client.create_listing(enriched_listing_create)

            # 5. Create orchestration run record
            orchestration_run_create = self._build_orchestration_run(
                original_listing,
                enriched_listing.id,
                description_response,
                image_responses
            )

            self.enriched_db_client.create_orchestration_run(orchestration_run_create)

            processing_time = time.time() - start_time
            logger.info(".2f")

            return EnrichmentResult(
                listing_id=listing_id,
                status="success",
                enriched_data={
                    "enriched_listing_id": enriched_listing.id,
                    "description_analysis": description_response.response if description_response else None,
                    "image_count": len(image_responses)
                },
                processing_time_seconds=processing_time,
                image_count=len(original_listing.images) if original_listing.images else 0,
                timestamp=timestamp
            )

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Failed to enrich listing {listing_id}: {e}", exc_info=True)

            return EnrichmentResult(
                listing_id=listing_id,
                status="failed",
                error_message=str(e),
                processing_time_seconds=processing_time,
                timestamp=timestamp
            )

    def enrich_listings_batch(self, listing_ids: List[str]) -> BatchEnrichmentResult:
        """
        Enrich multiple listings synchronously, continuing on individual failures.

        Args:
            listing_ids: List of listing IDs to process

        Returns:
            BatchEnrichmentResult with all processing outcomes
        """
        start_time = time.time()
        results = []

        logger.info(f"Starting batch enrichment for {len(listing_ids)} listings")

        for listing_id in listing_ids:
            try:
                result = self.enrich_listing(listing_id)
                results.append(result)
            except Exception as e:
                logger.error(f"Error processing listing {listing_id}: {e}", exc_info=True)
                # Create failed result for unhandled exceptions
                results.append(EnrichmentResult(
                    listing_id=listing_id,
                    status="failed",
                    error_message=str(e),
                    processing_time_seconds=0.0
                ))

        processing_time = time.time() - start_time
        total_processed = len(results)
        total_successful = sum(1 for r in results if r.status == "success")
        total_failed = total_processed - total_successful

        logger.info(f"Batch enrichment completed. Processed: {total_processed}, "
                   f"Successful: {total_successful}, Failed: {total_failed}, "
                   ".2f")

        return BatchEnrichmentResult(
            results=results,
            total_processed=total_processed,
            total_successful=total_successful,
            total_failed=total_failed,
            processing_time_seconds=processing_time
        )

    def enrich_description(self, description: str) -> Dict[str, Any]:
        """
        Run the description analyser agent on a description.

        Args:
            description: The property description to analyze

        Returns:
            Analysis result from the description analyser
        """
        if not self.description_analyser_agent:
            raise RuntimeError("Description analyser agent not configured")

        if not description:
            logger.warning("Empty description provided")
            return {"analysis": "No description provided"}

        try:
            response = self.description_analyser_agent.run(description)
            return response.response if response else {"analysis": "No response from analyser"}
        except Exception as e:
            logger.error(f"Error in description analysis: {e}", exc_info=True)
            return {"error": str(e)}

    def enrich_images(self, listing_id: str) -> List[Dict[str, Any]]:
        """
        Run the image analyser on images for a listing.

        Args:
            listing_id: The listing ID to analyze images for

        Returns:
            List of analysis results from the image analyser
        """
        if not hasattr(self, 'image_analyser') or not self.image_analyser:
            logger.warning("Image analyser not configured")
            return []

        try:
            listing_id_int = int(listing_id)
            image_analytics_runs = self.image_analyser.run_single_listing(listing_id_int)

            if not image_analytics_runs:
                return []

            # Convert to dictionary format for compatibility
            results = []
            for image_run in image_analytics_runs:
                result = {
                    "image_id": image_run.original_image_id,
                    "analysis": image_run.image_analytics_output,
                    "model": image_run.model,
                    "prompt_id": image_run.prompt_id
                }
                results.append(result)

            return results

        except Exception as e:
            logger.error(f"Error in image analysis for listing {listing_id}: {e}", exc_info=True)
            return [{"error": str(e)}]

    def _enrich_description(self, description: str) -> Optional[ModelResponse]:
        """Internal method to handle description enrichment."""
        if not self.description_analyser_agent:
            raise RuntimeError("Description analyser agent not configured")

        if not description:
            return None

        return self.description_analyser_agent.run(description)

    def _enrich_images(self, listing_id: int) -> List[ModelResponse]:
        """Internal method to handle image enrichment."""
        if not hasattr(self, 'image_analyser') or not self.image_analyser:
            logger.warning("Image analyser not configured, skipping image analysis")
            return []

        try:
            # Run image analysis using the existing ImageAnalyser
            image_analytics_runs = self.image_analyser.run_single_listing(listing_id)

            if not image_analytics_runs:
                logger.info(f"No images found for listing {listing_id}")
                return []

            # Convert ImageAnalyticsRun objects to ModelResponse objects for compatibility
            model_responses = []
            for image_run in image_analytics_runs:
                # Create a mock prompt object since we need it for ModelResponse
                mock_prompt = type('MockPrompt', (), {'id': image_run.prompt_id})()

                model_response = ModelResponse(
                    original_image_id=image_run.original_image_id,
                    enriched_image_id=None,  # Not available in current structure
                    model=image_run.model,
                    prompt=mock_prompt,
                    response=image_run.image_analytics_output
                )
                model_responses.append(model_response)

            logger.info(f"Successfully analyzed {len(model_responses)} images for listing {listing_id}")
            return model_responses

        except Exception as e:
            logger.error(f"Error in image analysis for listing {listing_id}: {e}", exc_info=True)
            return []

    def _build_enriched_listing(
        self,
        original_listing: OriginalListing,
        enriched_estate_agent_id: int,
        description_response: Optional[ModelResponse],
        image_responses: Optional[List[ModelResponse]] = None
    ) -> ListingCreate:
        """Build the enriched listing create payload."""

        # Create nested images
        enriched_images = []
        if image_responses and original_listing.images:
            for img in original_listing.images:
                # Find the corresponding image analysis
                analysis_result = next((res for res in image_responses if res.original_image_id == img.id), None)
                enriched_images.append(ImageCreateNested(
                    url=img.url,
                    filename=img.filename,
                    alt_text=img.alt_text,
                    agent_reference=img.agent_reference,
                    image_analysis=json.dumps(analysis_result.response if analysis_result and analysis_result.response else {})
                ))

        # Create nested location
        location_create = None
        if original_listing.location:
            address_create = None
            if original_listing.location.address:
                address_create = AddressCreate(**original_listing.location.address.model_dump(exclude={'id', 'created_at', 'updated_at'}))
            location_create = LocationCreate(
                latitude=original_listing.location.latitude,
                longitude=original_listing.location.longitude,
                address=address_create
            )

        return ListingCreate(
            title=original_listing.title,
            description_analysis=json.dumps(description_response.response if description_response else {}),
            estate_agent_id=enriched_estate_agent_id,
            external_url=original_listing.external_url,
            location=location_create,
            images=enriched_images
        )

    def _build_orchestration_run(
        self,
        original_listing: OriginalListing,
        enriched_listing_id: Optional[int],
        description_response: Optional[ModelResponse] = None,
        image_responses: Optional[List[ModelResponse]] = None
    ) -> EnrichmentOrchestrationRunCreate:
        """Build the orchestration run create payload."""

        # Description analytics
        desc_analytics = DescriptionAnalyticsRunCreate(
            description_output=json.dumps(description_response.response if description_response else {}),
            description=original_listing.description,
            original_listing_id=original_listing.id,
            enriched_listing_id=enriched_listing_id,
            model=description_response.model if description_response else "unknown",
            prompt_id=description_response.prompt.id if description_response and description_response.prompt else None
        )

        # Image analytics - Now implemented with real ImageAnalyser
        image_analytics_runs = []
        if image_responses:
            for image_response in image_responses:
                # Create ImageAnalyticsRunCreate from ModelResponse
                image_analytics_runs.append(ImageAnalyticsRunCreate(
                    image_analytics_output=json.dumps(image_response.response if image_response.response else {}),
                    original_image_id=image_response.original_image_id,
                    enriched_image_id=image_response.enriched_image_id,
                    model=image_response.model,
                    prompt_id=image_response.prompt.id if image_response.prompt else None
                ))

        return EnrichmentOrchestrationRunCreate(
            enrichment_orchestration_set_id=0,  # Use 0 for sync processing (no orchestration set)
            run_sequence_number=1,  # Single run per listing
            original_listing_id=original_listing.id,
            enriched_listing_id=enriched_listing_id,
            timestamp=datetime.now(timezone.utc),
            description_analytics=desc_analytics,
            image_analytics=image_analytics_runs
        )
