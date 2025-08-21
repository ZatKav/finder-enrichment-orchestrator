import os
from typing import List, Optional

from dotenv import load_dotenv
from finder_enrichment_db_client import FinderEnrichmentDBAPIClient
from listings_db_contracts.schemas import Image

from finder_enrichment_db_contracts import ImageAnalyticsRun, ImageAnalyticsRunCreate
from listings_db_api_client.listings_db_api_client import ListingsDBAPIClient

from finder_enrichment.agentic_services.image_analyser.image_analyser_agent import ImageAnalyserAgent
from finder_enrichment.agentic_services.model_response import ModelResponse
from finder_enrichment.logger_config import setup_logger

logger = setup_logger(__name__)
load_dotenv()


class ImageAnalyser:
    def __init__(self):
        self.listings_db_client: ListingsDBAPIClient = ListingsDBAPIClient(api_key=os.getenv("LISTINGS_DB_API_KEY"), base_url=os.getenv("LISTINGS_DB_BASE_URL"))
        self.image_analyser_agent: ImageAnalyserAgent = ImageAnalyserAgent()
        self.enriched_db_client: FinderEnrichmentDBAPIClient = FinderEnrichmentDBAPIClient(api_key=os.getenv("ENRICHMENT_DB_API_KEY"), base_url=os.getenv("ENRICHMENT_DB_BASE_URL"))
        self.is_running = False
        self.processed_count = 0
        self.error_count = 0
    
    
    def run_single_image(self, image_id: int) -> ImageAnalyticsRun|bool:
        try:
            original_image = self.listings_db_client.get_image(image_id=image_id)
            if not original_image:
                logger.error(f"No image found for ID {image_id}")
                return False
            
            image_analytics_run = self.handle_image_analysis(original_image)
            if not image_analytics_run:
                logger.warning(f"Image analysis for image {image_id} returned no response.")
                return False
            
            return image_analytics_run
        
        except Exception as e:
            logger.error(f"Failed to analyse image {image_id}: {e}")
            return False
        

    def run_single_listing(self, listing_id: int) -> List[ImageAnalyticsRun]|bool:
        # 1. Fetch original listing data
        try:
            original_listing = self.listings_db_client.get_listing(listing_id=listing_id)
            if not original_listing:
                logger.error(f"No listing found for ID {listing_id}")
                return False
        except Exception as e:
            logger.error(f"Failed to fetch original listing {listing_id}: {e}")
            return False
        
        image_analytics_runs: List[ImageAnalyticsRun] = []
        
        for image in original_listing.images:
            # 2. Run image analysis
            image_analytics_run = self.handle_image_analysis(image)
            if not image_analytics_run:
                logger.warning(f"Image analysis for image {image.id} returned no response.")
                continue
            image_analytics_runs.append(image_analytics_run)
            
        return image_analytics_runs
        
        
    def handle_image_analysis(self, image: Image) -> Optional[ImageAnalyticsRun]:
        try:
            image_analysis_model_response: ModelResponse = self.image_analyser_agent.run(image)
            
            return self.create_image_analytics_run(image, image_analysis_model_response)
        except Exception as e:
            logger.error(f"Failed to run image analysis for image {image.id}: {e}")
            return None    
          
            
    def create_image_analytics_run(self, original_image: Image, image_analysis_model_response: ModelResponse) -> ImageAnalyticsRun:
        """Create an image analytics run in the enriched database."""
        
        image_analytics_run = ImageAnalyticsRunCreate(
            image_analytics_output=image_analysis_model_response.response,
            image_data=original_image.image_data,
            original_image_id=original_image.id,
            model=image_analysis_model_response.model,
            temperature=str(self.image_analyser_agent.config.temperature),
            prompt_id=image_analysis_model_response.prompt.id
        )
        
        created_image_analytics_run = self.enriched_db_client.create_image_analytics(image_analytics_run)
        
        return created_image_analytics_run