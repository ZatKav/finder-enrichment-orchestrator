import os
from typing import List, Dict, Any
import time
import json
from pathlib import Path

from dotenv import load_dotenv
from finder_enrichment_db_contracts import Prompt
from listings_db_contracts.schemas import Image

from finder_enrichment.agentic_services.base_agent import BaseAgent
from finder_enrichment.agentic_services.agent_config import AgentConfig
from finder_enrichment.agentic_services.agent_interaction import AgentInteraction

from finder_enrichment.agentic_services.model_response import ModelResponse
from finder_enrichment.logger_config import setup_logger

logger = setup_logger(__name__)

load_dotenv()


class ImageAnalyserAgent(BaseAgent):
    """Agent responsible for analyzing property images."""
    
    def __init__(self):
        config = AgentConfig()
        agent_name = "image_analyser"
        super().__init__(config, agent_name)
        self.model = config.model
        self.mock_image_analyser = os.getenv('MOCK_IMAGE_ENDPOINT', 'false').lower() == 'true'

    
    def run(self, image: Image) -> ModelResponse:
        """AI agent analyzes the image of a property into an agreed markdown format"""
        prompt_record: Prompt = self._load_agent_profile()
        if not prompt_record:
            logger.error(f"No prompt found for {self.agent_name}")
            raise Exception(f"No prompt found for {self.agent_name}")
        
        self.version = prompt_record.version
        self.agent_profile = prompt_record.prompt

        prompt = f"{self.agent_profile}"
        
        start_time = time.time()
        try:
            if self.mock_image_analyser or self.mock_mode:
                logger.info(f"🎭 MOCK MODE ENABLED for {self.agent_name} - returning input instead of calling AI endpoint")
                content = f"This is a mock response for {self.agent_name} for the prompt {prompt}"
            else:
                logger.info(f"🎭 MOCK MODE DISABLED for {self.agent_name} - calling AI endpoint")

                # Use the dedicated analyze_image method for better image processing
                response = self.client.analyze_image(
                    image_data=image.image_data,
                    prompt=prompt,
                    image_content_type="image/webp"  # Default to webp, could be made configurable
                )
                
                if response.get("success"):
                    content = response["text"]
                else:
                    error_msg = response.get("error", "Unknown error")
                    logger.error(f"AI client error: {error_msg}")
                    raise Exception(f"AI client error: {error_msg}")
            
            processing_time = time.time() - start_time
            
            self._record_interaction("analyse_image", prompt, content, processing_time)
            
            logger.info(f"Image analysed")
            
            return ModelResponse(
                agent_version=self.version,
                model=self.model,
                request=prompt,
                response=content,
                prompt=prompt_record,
                processing_time=processing_time,
                token_count_estimate=0
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            self._record_interaction("analyse_image_ERROR", prompt, str(e), processing_time)
            logger.error(f"Error analysing image: {e}")
            raise