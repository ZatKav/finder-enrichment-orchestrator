import os
from typing import List, Dict, Any
import time
import json
from pathlib import Path

from dotenv import load_dotenv

from finder_enrichment.agentic_services.base_agent import BaseAgent
from finder_enrichment.agentic_services.agent_config import AgentConfig
from finder_enrichment.agentic_services.agent_interaction import AgentInteraction
import google.generativeai as genai

from finder_enrichment.agentic_services.model_response import ModelResponse
from finder_enrichment.logger_config import setup_logger

logger = setup_logger(__name__)

load_dotenv()


class DescriptionAnalyserAgent(BaseAgent):
    """Agent responsible for searching and curating property listings."""
    
    def __init__(self):
        config = AgentConfig()
        agent_name = "description_analyser"
        super().__init__(config, agent_name)
        self.model = config.model
        self.mock_description_analyser = os.getenv('MOCK_DESCRIPTION_ENDPOINT', 'false').lower() == 'true'

    
    def run(self, description: str) -> ModelResponse:
        """AI agent summarises the description of a property into an agreed markdown format"""
        
        prompt_record = self._load_agent_profile()
        if not prompt_record:
            logger.error(f"No prompt found for {self.agent_name}")
            raise Exception(f"No prompt found for {self.agent_name}")
        
        self.version = prompt_record.version
        self.agent_profile = prompt_record.prompt

        prompt = f"{self.agent_profile}: \n\n {description}"
        
        if not description:
            logger.warning(f"No description found for property")
            return ModelResponse(
                agent_version=self.version,
                model=self.model,
                request=prompt,
                response="No description found for property",
                prompt=prompt_record,
                processing_time=0,
                token_count_estimate=0
            )
        
        start_time = time.time()
        try:
            if self.mock_description_analyser or self.mock_mode:
                logger.info(f"🎭 MOCK MODE ENABLED for {self.agent_name} - returning input instead of calling AI endpoint")
                content = f"This is a mock response for {self.agent_name} for the prompt {prompt}"
            else:
                logger.info(f"🎭 MOCK MODE DISABLED for {self.agent_name} - calling AI endpoint")

                response = self.client.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=self.config.temperature,
                        max_output_tokens=self.config.max_tokens,
                    )
                )
                content = response.text
            
            processing_time = time.time() - start_time
            
            self._record_interaction("analyse_description", prompt, content, processing_time)
            
            logger.info(f"Description analysed")
            
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
            self._record_interaction("analyse_description_ERROR", prompt, str(e), processing_time)
            logger.error(f"Error analysing description: {e}")
            raise