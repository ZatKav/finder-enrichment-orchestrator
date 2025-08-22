from abc import ABC, abstractmethod
import time
from typing import List
import os
from dotenv import load_dotenv

from finder_enrichment.agentic_services.agent_config import AgentConfig
from finder_enrichment.agentic_services.agent_interaction import AgentInteraction
from finder_enrichment_db_client.finder_enrichment_db_api_client import FinderEnrichmentDBAPIClient
from finder_enrichment_db_contracts.schemas import Prompt

from finder_enrichment.logger_config import setup_logger

logger = setup_logger(__name__)

# Load environment variables
load_dotenv()


class BaseAgent(ABC):
    """Base class for all agents."""
    
    def __init__(self, config: AgentConfig, agent_name: str):
        self.config = config
        self.client = config.get_client()
        self.enrichment_db_client = FinderEnrichmentDBAPIClient(api_key=os.getenv("ENRICHMENT_DB_API_KEY"), base_url=os.getenv("ENRICHMENT_DB_BASE_URL"))
        self.agent_name = agent_name
        self.interactions: List[AgentInteraction] = []
        self.generation_config = self._load_generation_config()
        self.mock_mode = os.getenv('MOCK_AI_ENDPOINT', 'false').lower() == 'true'
                
        if self.mock_mode:
            logger.info(f"🎭 MOCK MODE ENABLED for all inputs returning input instead of calling AI endpoint")
    
    def _load_agent_profile(self) -> Prompt:
        """Load agent profile from database."""
        try:
            prompt = self.enrichment_db_client.get_latest_prompt_by_name(self.agent_name)
            if not prompt:
                logger.error(f"No prompt found for {self.agent_name}")
                raise Exception(f"No prompt found for {self.agent_name}")
            return prompt
        
        except Exception as e:
            logger.error(f"Error loading agent profile from {self.agent_name}: {e}")
            raise
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation)."""
        return len(text.split()) * 1.3  # Rough estimate
    
    def _record_interaction(self, action: str, prompt: str, response: str, processing_time: float):
        """Record an agent interaction for analysis."""
        interaction = AgentInteraction(
            agent_name=self.agent_name,
            action=action,
            prompt=prompt,
            response=response,
            timestamp=time.time(),
            processing_time=processing_time,
            token_count_estimate=int(self._estimate_tokens(prompt + response))
        )
        self.interactions.append(interaction)
        
        # Log the interaction
        logger.debug(f"🏠 Listings Curator Agent - {action}")
        logger.debug(f"⏱️  Processing time: {processing_time:.2f}s")
        logger.debug(f"📊 Estimated tokens: {interaction.token_count_estimate}")
        
    def _load_generation_config(self) -> dict:
        """Load generation config for the new client interface."""
        return {
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }
    
    def _mock_generate_response(self, prompt: str) -> str:
        """Mock response that returns the input prompt instead of calling AI endpoint."""
        logger.info(f"🎭 MOCK MODE: {self.agent_name} returning input instead of AI call")
        return f"[MOCK RESPONSE] {prompt}"
    
    @abstractmethod
    def run(self, *args, **kwargs):
        """Run the agent."""