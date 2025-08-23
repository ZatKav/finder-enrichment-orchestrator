"""
Base enrichment orchestrator with shared processing logic.
"""

import json
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timezone

from listings_db_contracts.schemas import ApiResponse, EstateAgent as OriginalEstateAgent, Listing as OriginalListing

from finder_enrichment.agentic_services.base_agent import BaseAgent
from finder_enrichment.agentic_services.description_analyser.description_analyser_agent import DescriptionAnalyserAgent
from finder_enrichment.agentic_services.image_analyser.image_analyser_agent import ImageAnalyserAgent
from finder_enrichment.agentic_services.model_response import ModelResponse

# Import the db client and models
from finder_enrichment_db_client import FinderEnrichmentDBAPIClient

from listings_db_api_client.listings_db_api_client import ListingsDBAPIClient
from finder_enrichment_db_contracts import (
    DescriptionAnalyticsRunCreate,
    EnrichmentOrchestrationRun,
    ImageAnalyticsRunCreate,
    EnrichmentOrchestrationSetCreate,
    EnrichmentOrchestrationRunCreate,
    ListingCreate,
    ImageCreateNested,
    LocationCreate,
    AddressCreate,
    EstateAgentCreate
    
)

from finder_enrichment.orchestrator.estate_agent_utils import get_or_create_estate_agent
from finder_enrichment.orchestrator.exceptions import (
    ListingNotFoundError, EstateAgentError, DescriptionAnalysisError, 
    ImageAnalysisError, DatabaseError, ExternalServiceError
)
from finder_enrichment.logger_config import setup_logger

logger = setup_logger(__name__)


class BaseEnrichmentOrchestrator:
    """
    Base orchestrator for property listing enrichment.
    
    Contains shared enrichment processing logic that can be used by different
    orchestrator implementations (Kafka-based, Database-based, etc.).
    """
    
    def __init__(
        self,
        max_workers: int = 4,
        enable_parallel_processing: bool = True
    ):
        """
        Initialize the base enrichment orchestrator.
        
        Args:
            max_workers: Maximum number of worker threads for parallel processing
            enable_parallel_processing: Whether to enable parallel processing of enrichments
        """
        self.max_workers = max_workers
        self.enable_parallel_processing = enable_parallel_processing
        
        # Service clients - will be injected via dependency injection
        self.listings_db_client: ListingsDBAPIClient = ListingsDBAPIClient()
        self.description_analyser_agent: DescriptionAnalyserAgent = DescriptionAnalyserAgent()
        self.floorplan_analyser_agent: ImageAnalyserAgent = ImageAnalyserAgent("floorplan_analyser")
        self.image_analyser_agent: ImageAnalyserAgent = ImageAnalyserAgent()
        self.enriched_db_client: FinderEnrichmentDBAPIClient = FinderEnrichmentDBAPIClient()
        
        # Processing state
        self.is_running = False
        self.processed_count = 0
        self.error_count = 0
        self.orchestration_set_id: Optional[int] = None
        
        # Enrichment handlers mapping
        self.enrichment_handlers: Dict[str, Callable] = {
            "description_analysis": self._handle_description_analysis,
            "floorplan_analysis": self._handle_floorplan_analysis,
            "image_analysis": self._handle_image_analysis,
        }
        

    def process_single_listing(self, property_id: str) -> EnrichmentOrchestrationRun:
        """
        Process a single listing by its ID.
        
        Args:
            property_id: The ID of the listing to process
            
        Returns:
            EnrichmentOrchestrationRun if processing was successful
            
        Raises:
            ListingNotFoundError: When the listing cannot be found
            EstateAgentError: When estate agent processing fails
            DescriptionAnalysisError: When description analysis fails
            ImageAnalysisError: When image analysis fails
            DatabaseError: When database operations fail
        """
        logger.info(f"Processing listing: {property_id}")
        
        # 1. Fetch original listing data
        try:
            original_listing: OriginalListing = self.listings_db_client.get_listing(listing_id=property_id)
            
        except Exception as e:
            logger.error(f"Failed to fetch original listing {property_id}: {e}")
            raise ListingNotFoundError(f"Listing {property_id} not found or inaccessible: {str(e)}") from e

        # 2. Get or create Estate Agent in enriched DB
        try:
            original_agent: OriginalEstateAgent = original_listing.estate_agent
            
            enriched_estate_agent_id = get_or_create_estate_agent(original_agent)
            if not enriched_estate_agent_id:
                raise EstateAgentError(f"Could not get or create estate agent for listing {property_id}")
        except EstateAgentError:
            raise  # Re-raise our custom exception
        except Exception as e:
            logger.error(f"Failed to get or create estate agent for listing {property_id}: {e}", exc_info=True)
            raise EstateAgentError(f"Estate agent processing failed for listing {property_id}: {str(e)}") from e
            
        # 3. Run all enrichments in sequence
        try:
            description_analysis_model_response = self._handle_description_analysis(original_listing)
        except Exception as e:
            raise DescriptionAnalysisError(f"Description analysis failed for listing {property_id}: {str(e)}") from e
            
        image_responses = None
        floorplan_responses = None
        
        if original_listing.images:
            try:
                image_responses = self._handle_image_analysis(original_listing)
            except Exception as e:
                raise ImageAnalysisError(f"Image analysis failed for listing {property_id}: {str(e)}") from e

        #TODO: Add floorplan analysis

        # 4. Create Enriched Listing
        try:
            enriched_listing_create = self._build_enriched_listing(
                original_listing,
                enriched_estate_agent_id,
                description_analysis_model_response,
                image_responses,
                floorplan_responses
            )
            enriched_listing = self.enriched_db_client.create_listing(enriched_listing_create)
            logger.info(f"Created enriched listing with ID: {enriched_listing.id}")
        except Exception as e:
            logger.error(f"Failed to create enriched listing for property {property_id}: {e}", exc_info=True)
            raise DatabaseError(f"Failed to create enriched listing for property {property_id}: {str(e)}") from e

        # 5. Create Orchestration Run Record
        try:
            orchestration_run_create: EnrichmentOrchestrationRunCreate = self._build_orchestration_run(
                original_listing=original_listing, 
                enriched_listing_id=enriched_listing.id,
                description_analysis_model_response=description_analysis_model_response,
                image_responses=image_responses,
                floorplan_responses=floorplan_responses
            )
            created_orchestration_run: EnrichmentOrchestrationRun = self.enriched_db_client.create_orchestration_run(orchestration_run_create)
            logger.info(f"Created orchestration run for original listing {property_id}")
            self.processed_count += 1
            return created_orchestration_run
        except Exception as e:
            logger.error(f"Failed to create orchestration run for property {property_id}: {e}", exc_info=True)
            raise DatabaseError(f"Failed to create orchestration run for property {property_id}: {str(e)}") from e
            
            
    def _create_orchestration_set(self) -> None:
        """Create a new orchestration set for tracking this processing run."""
        try:
            orchestration_set_create = EnrichmentOrchestrationSetCreate(
                name=f"enrichment_run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
                description="Automated enrichment processing run",
                created_at=datetime.now(timezone.utc)
            )
            created_set = self.enriched_db_client.create_orchestration_set(orchestration_set_create)
            self.orchestration_set_id = created_set.id
            logger.info(f"Created orchestration set with ID: {self.orchestration_set_id}")
        except Exception as e:
            logger.error(f"Failed to create orchestration set: {e}", exc_info=True)
            raise DatabaseError(f"Failed to create orchestration set: {str(e)}") from e
        
        
    def _build_enriched_listing(self, original_listing: OriginalListing, enriched_estate_agent_id: int, description_analysis_model_response: ModelResponse, image_responses: Optional[List[ModelResponse]] = None, floorplan_responses: Optional[List[ModelResponse]] = None) -> ListingCreate:
        """Constructs the ListingCreate payload for the new enriched listing."""
        
        original_listing: OriginalListing = original_listing
        
        # Create nested images
        enriched_images = []
        if image_responses:
            for i, img in enumerate(original_listing.images):
                analysis_result = next((res for res in image_responses if res.get("original_image_id") == img.id), {})
                enriched_images.append(ImageCreateNested(
                    url=img.url,
                    filename=img.filename,
                    alt_text=img.alt_text,
                    agent_reference=img.agent_reference,
                    image_analysis=json.dumps(analysis_result.response)
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
        
        listing_create = ListingCreate(
            title=original_listing.title,
            description_analysis=description_analysis_model_response.response,
            estate_agent_id=enriched_estate_agent_id,
            external_url=original_listing.external_url,
            location=location_create,
            images=enriched_images
        )
        return listing_create
        
        
    def _build_orchestration_run(self, original_listing: OriginalListing, enriched_listing_id: Optional[int], description_analysis_model_response: Optional[ModelResponse] = None, image_responses: Optional[List[ModelResponse]] = None, floorplan_responses: Optional[List[ModelResponse]] = None) -> EnrichmentOrchestrationRunCreate:
        """Constructs the EnrichmentOrchestrationRunCreate payload."""
        
        # Description analytics
        desc_analytics = DescriptionAnalyticsRunCreate(
            description_output=json.dumps(description_analysis_model_response.response),
            description=original_listing.description,
            original_listing_id=original_listing.id,
            enriched_listing_id=enriched_listing_id,
            model=description_analysis_model_response.model,
            prompt_id=description_analysis_model_response.prompt.id
        )

        # Image analytics
        image_analytics_runs = []
        if image_responses and len(image_responses) > 0:
            for image_response in image_responses:
                image_analytics_runs.append(ImageAnalyticsRunCreate(
                    image_analytics_output=json.dumps(image_response.response),
                    original_image_id=image_response.original_image_id,
                    enriched_image_id=image_response.enriched_image_id,
                    model=image_response.model,
                    prompt_id=image_response.prompt.id
                ))

        orchestration_run = EnrichmentOrchestrationRunCreate(
            enrichment_orchestration_set_id=self.orchestration_set_id,
            run_sequence_number=self.processed_count + 1,
            original_listing_id=original_listing.id,
            enriched_listing_id=enriched_listing_id,
            timestamp=datetime.now(timezone.utc),
            description_analytics=desc_analytics,
            image_analytics=image_analytics_runs
        )
        return orchestration_run
            
            
    # Enrichment handler methods
    def _handle_description_analysis(self, listing: OriginalListing) -> ModelResponse:
        """Handle description analysis enrichment."""
        if not self.description_analyser_agent:
            raise RuntimeError("Description analyser agent not configured")
            
        # Extract description from listing data
        description = listing.description
        
        if not description:
            raise DescriptionAnalysisError(f"No description found for property {listing.id}")
        
        return self.description_analyser_agent.run(description)
        
    def _handle_floorplan_analysis(self, listing: OriginalListing) -> List[Dict[str, Any]]:
        """Handle floorplan analysis enrichment."""
        if not self.floorplan_analyser_agent:
            raise RuntimeError("Floorplan analyser agent not configured")
        
        if not listing.floorplans:
            logger.info(f"No floorplans found for property {listing.id}, skipping floorplan analysis")
            return []

        results = []
        for floorplan in listing.floorplans:
            try:
                # Call floorplan analyser service - mocked
                analysis = self.floorplan_analyser_agent.analyse_floorplan_url(floorplan.url)
                results.append({
                    "original_floorplan_id": floorplan.id,
                    "analysis": analysis,
                    "version": "mock_floorplan_v1"
                })
            except Exception as e:
                logger.error(f"Failed to analyze floorplan {floorplan.id}: {e}")
                # Continue with other floorplans even if one fails
                continue
        
        return results
            

    def _handle_image_analysis(self, listing: OriginalListing) -> List[ModelResponse]:
        """Handle image analysis enrichment."""
        if not self.image_analyser_agent:
            raise RuntimeError("Image analyser client not configured")
            
        if not listing.images:
            logger.info(f"No images found for property {listing.id}, skipping image analysis")
            return []
            
        results = []
        # Call image analyser service for all images
        for image in listing.images:
            try:
                result = self.image_analyser_agent.run(image)
                results.append(ModelResponse(
                    original_image_id=image.id,
                    enriched_image_id=result.enriched_image_id if hasattr(result, 'enriched_image_id') else None,
                    model=result.model,
                    prompt=result.prompt,
                    response=result.response,
                ))
            except Exception as e:
                logger.error(f"Failed to analyze image {image.id}: {e}")
                # Continue with other images even if one fails
                continue
        
        return results
        
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return {
            "is_running": self.is_running,
            "processed_count": self.processed_count,
            "error_count": self.error_count,
            "success_rate": (
                self.processed_count / (self.processed_count + self.error_count)
                if (self.processed_count + self.error_count) > 0
                else 0.0
            )
        } 