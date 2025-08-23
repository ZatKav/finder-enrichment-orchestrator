import os
from typing import Optional

from dotenv import load_dotenv
from listings_db_contracts.schemas import ApiResponse, Listing, EstateAgent
from finder_enrichment_db_client import FinderEnrichmentDBAPIClient
from finder_enrichment_db_contracts import DescriptionAnalyticsRunCreate, DescriptionAnalyticsRun
from listings_db_api_client.listings_db_api_client import ListingsDBAPIClient

from finder_enrichment.agentic_services.description_analyser.description_analyser_agent import DescriptionAnalyserAgent
from finder_enrichment.agentic_services.model_response import ModelResponse
from finder_enrichment.orchestrator.estate_agent_utils import get_or_create_estate_agent
from finder_enrichment.logger_config import setup_logger

logger = setup_logger(__name__)
load_dotenv()


class DescriptionAnalyser:
    def __init__(self):
        self.listings_db_client: ListingsDBAPIClient = ListingsDBAPIClient(api_key=os.getenv("LISTINGS_DB_API_KEY"), base_url=os.getenv("LISTINGS_DB_BASE_URL"))
        self.description_analyser_agent: DescriptionAnalyserAgent = DescriptionAnalyserAgent()
        self.enriched_db_client: FinderEnrichmentDBAPIClient = FinderEnrichmentDBAPIClient(api_key=os.getenv("ENRICHMENT_DB_API_KEY"), base_url=os.getenv("ENRICHMENT_DB_BASE_URL"))
        self.is_running = False
        self.processed_count = 0
        self.error_count = 0
    

    def run_single_listing(self, listing_id: int) -> DescriptionAnalyticsRun|bool:
        # 1. Fetch original listing data
        try:
            original_listing = self.listings_db_client.get_listing(listing_id=listing_id)
            if not original_listing:
                logger.error(f"No listing found for ID {listing_id}")
                return False
        except Exception as e:
            logger.error(f"Failed to fetch original listing {listing_id}: {e}")
            return False
        
        # 2. Get or create Estate Agent in enriched DB
        try:
            original_agent: EstateAgent = original_listing.estate_agent
            
            enriched_estate_agent_id = get_or_create_estate_agent(original_agent)
            if not enriched_estate_agent_id:
                logger.error(f"Could not get or create estate agent for listing {listing_id}. Aborting processing for this listing.")
                self.error_count += 1
                return False
        except Exception as e:
            logger.error(f"Failed to get or create estate agent for listing {listing_id}: {e}", exc_info=True)
            self.error_count += 1
            return False
        
        # 3. Run description analysis
        description_analysis_model_response = self.handle_description_analysis(original_listing)
        if not description_analysis_model_response:
            logger.warning(f"Description analysis for listing {original_listing.id} returned no response.")
            return False
        
        return self.create_description_analytics_run(original_listing, description_analysis_model_response)
            
    def create_description_analytics_run(self, original_listing: Listing, description_analysis_model_response: ModelResponse) -> DescriptionAnalyticsRun:
        """Create a description analytics run in the enriched database."""
        
        description_analytics_run = DescriptionAnalyticsRunCreate(
            description_output=description_analysis_model_response.response,
            description=original_listing.description,
            original_listing_id=original_listing.id,
            model=description_analysis_model_response.model,
            temperature=str(self.description_analyser_agent.config.temperature),
            prompt_id=description_analysis_model_response.prompt.id
        )
        
        created_description_analytics_run = self.enriched_db_client.create_description_analytics(description_analytics_run)
        
        return created_description_analytics_run
        
    def handle_description_analysis(self, listing: Listing) -> ModelResponse:
        """Handle description analysis enrichment."""
        if not self.description_analyser_agent:
            raise RuntimeError("Description analyser agent not configured")
            
        # Extract description from listing data
        description = listing.description
        if not description:
            logger.warning(f"No description found for property {listing.id}")
            return None
        
        return self.description_analyser_agent.run(description)
        
    
    