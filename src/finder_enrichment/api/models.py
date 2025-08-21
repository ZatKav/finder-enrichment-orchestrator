from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class OrchestrationJobResponse(BaseModel):
    """Response model for orchestration job."""
    job_id: str
    status: str
    message: str
    started_at: str
    stats: Optional[Dict[str, Any]] = None


class OrchestrationJobStatus(BaseModel):
    """Status model for orchestration job."""
    job_id: str
    status: str  # "running", "completed", "failed"
    started_at: str
    completed_at: Optional[str] = None
    stats: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    analytics_run_id: Optional[int] = None
    analytics_run_ids: Optional[List[int]] = None