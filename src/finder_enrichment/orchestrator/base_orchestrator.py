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
        self.listings_db_client: Optional[ListingsDBAPIClient] = None
        self.description_analyser_agent: Optional[DescriptionAnalyserAgent] = None  
        self.floorplan_analyser_client: Optional[BaseAgent] = None
        self.image_analyser_client: Optional[ImageAnalyserAgent] = None
        self.enriched_db_client: Optional[FinderEnrichmentDBAPIClient] = None
        
        # Processing state
        self.is_running = False
        self.processed_count = 0
        self.error_count = 0
        
        # Orchestration state
        self.orchestration_set_id: Optional[int] = None
        
        # Enrichment handlers mapping
        self.enrichment_handlers: Dict[str, Callable] = {
            "description_analysis": self._handle_description_analysis,
            "floorplan_analysis": self._handle_floorplan_analysis,
            "image_analysis": self._handle_image_analysis,
        }
        
    def set_service_clients(
        self,
        listings_db_client=None,
        description_analyser_client=None,
        floorplan_analyser_client=None, 
        image_analyser_client=None,
        enriched_db_client=None
    ):
        """Inject service client dependencies."""
        self.listings_db_client = listings_db_client
        self.description_analyser_agent = description_analyser_client
        self.floorplan_analyser_client = floorplan_analyser_client
        self.image_analyser_client = image_analyser_client
        self.enriched_db_client = enriched_db_client
        
    def _create_orchestration_set(self) -> int:
        """Create a new orchestration set and return its ID."""
        if not self.enriched_db_client:
            raise RuntimeError("Enriched DB client must be configured before starting.")
            
        set_create = EnrichmentOrchestrationSetCreate(timestamp=datetime.now(timezone.utc))
        orchestration_set = self.enriched_db_client.create_orchestration_set(set_create)
        self.orchestration_set_id = orchestration_set.id
        logger.info(f"Created orchestration set with ID: {self.orchestration_set_id}")
        return self.orchestration_set_id

    def process_single_listing(self, property_id: str) -> bool:
        """
        Process a single listing by its ID.
        
        Args:
            property_id: The ID of the listing to process
            
        Returns:
            True if processing was successful, False otherwise
        """
        logger.info(f"Processing listing: {property_id}")
        
        # 1. Fetch original listing data
        try:
            original_listing: OriginalListing = self.listings_db_client.get_listing(listing_id=property_id)
            
        except Exception as e:
            logger.error(f"Failed to fetch original listing {property_id}: {e}")
            return False

        # 2. Get or create Estate Agent in enriched DB
        try:
            original_agent: OriginalEstateAgent = original_listing.estate_agent
            
            enriched_estate_agent_id = get_or_create_estate_agent(original_agent)
            if not enriched_estate_agent_id:
                logger.error(f"Could not get or create estate agent for listing {property_id}. Aborting processing for this listing.")
                self.error_count += 1
                return False
        except Exception as e:
            logger.error(f"Failed to get or create estate agent for listing {property_id}: {e}", exc_info=True)
            self.error_count += 1
            return False
            
        # 3. Run all enrichments in sequence
        description_analysis_model_response = self._handle_description_analysis(original_listing)
        image_responses = None
        floorplan_responses = None
        image_responses = self._handle_image_analysis(original_listing) if original_listing.images else None
        # floorplan_responses = self._handle_floorplan_analysis(original_listing) if original_listing.floorplans else None

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
            enriched_listing = None

        if enriched_listing:
            # 5. Create Orchestration Run Record
            try:
                orchestration_run_create = self._build_orchestration_run(
                    original_listing, 
                    enriched_listing.id,
                    description_analysis_model_response,
                    image_responses,
                    floorplan_responses
                )
                self.enriched_db_client.create_orchestration_run(orchestration_run_create)
                logger.info(f"Created orchestration run for original listing {property_id}")
                self.processed_count += 1
                return True
            except Exception as e:
                logger.error(f"Failed to create orchestration run for property {property_id}: {e}", exc_info=True)
                self.error_count += 1
                return False
        
        return False
            
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
    def _handle_description_analysis(self, listing: OriginalListing) -> Dict[str, Any]:
        """Handle description analysis enrichment."""
        if not self.description_analyser_agent:
            raise RuntimeError("Description analyser agent not configured")
            
        # Extract description from listing data
        description = listing.description
        
        if not description:
            logger.warning(f"No description found for property")
        
        return self.description_analyser_agent.run(description)
        
    def _handle_floorplan_analysis(self, listing: OriginalListing) -> List[Dict[str, Any]]:
        """Handle floorplan analysis enrichment."""
        if not self.floorplan_analyser_client:
            raise RuntimeError("Floorplan analyser client not configured")
        
        if not listing.floorplans:
            logger.warning(f"No floorplans found for property {listing.id}")
            return []

        results = []
        for floorplan in listing.floorplans:
            # Call floorplan analyser service - mocked
            analysis = self.floorplan_analyser_client.analyse_floorplan_url(floorplan.url)
            results.append({
                "original_floorplan_id": floorplan.id,
                "analysis": analysis,
                "version": "mock_floorplan_v1"
            })
        return results
            
    #TODO handle this next
    def _handle_image_analysis(self, listing: OriginalListing) -> List[ModelResponse]:
        """Handle image analysis enrichment."""
        if not self.image_analyser_client:
            raise RuntimeError("Image analyser client not configured")
            
        if not listing.images:
            logger.warning(f"No images found for property {listing.id}")
            return []
            
        results = []
        # Call image analyser service for all images
        # results: List[ModelResponse] = []
        # for image in listing.images:
        #     result = self.image_analyser_client.run(image)
        #     results.append(ModelResponse(
        #         original_image_id=image.id,
        #         enriched_image_id=result.enriched_image_id,
        #         model=result.model,
        #         prompt=result.prompt,
        #         response=result.response,
        #     ))
        
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