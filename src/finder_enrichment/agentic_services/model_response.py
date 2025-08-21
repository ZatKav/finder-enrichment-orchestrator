from dataclasses import asdict, dataclass
from listings_db_contracts.schemas import Image
from finder_enrichment_db_contracts.schemas import Prompt
from pydantic import BaseModel, Field
from typing import List, Optional

@dataclass
class ModelResponse:
    agent_version: str
    model: str
    request: str
    response: str
    prompt: Prompt
    processing_time: float
    token_count_estimate: int
    
@dataclass
class ImageAndResponse(ModelResponse):
    image: Image
    model_response: ModelResponse