from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from typing import Optional
from datetime import datetime, timezone

from finder_enrichment.api.utils import generate_datetime_string
import finder_enrichment.api.globals as g
from finder_enrichment.api.models import OrchestrationJobResponse, OrchestrationJobStatus
from finder_enrichment.api.auth import require_api_key
from finder_enrichment.logger_config import setup_logger

router = APIRouter()
logger = setup_logger(__name__)


@router.post("/run_database_orchestrator", response_model=OrchestrationJobResponse)
async def run_database_orchestrator(
    background_tasks: BackgroundTasks,
    limit: Optional[int] = None,
    api_key: str = Depends(require_api_key),
):
    """
    Run the database orchestrator to process all listings in the database.
    """
    job_id = f"orchestration_{generate_datetime_string()}"
    
    g.running_jobs[job_id] = {
        "job_id": job_id,
        "status": "starting",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "limit": limit,
    }
    
    background_tasks.add_task(run_orchestrator_job, job_id, limit)
    
    logger.info(f"Started orchestration job {job_id}" + (f" with limit {limit}" if limit else ""))
    
    return OrchestrationJobResponse(
        job_id=job_id,
        status="starting",
        message=f"Orchestration job started" + (f" (limit: {limit})" if limit else ""),
        started_at=g.running_jobs[job_id]["started_at"],
    )
    
    
def run_orchestrator_job(job_id: str, limit: Optional[int] = None):
    """Run the database orchestrator process in background."""
    
    try:
        logger.info(f"Starting orchestration job {job_id}")
        g.running_jobs[job_id]["status"] = "running"
        
        if not g.orchestrator:
            raise RuntimeError("Orchestrator not initialized")
        
        g.orchestrator.process_all_listings(limit=limit)
        
        stats = g.orchestrator.get_database_stats()
        
        g.running_jobs[job_id].update({
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "stats": stats,
        })
        
        logger.info(f"Orchestration job {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Orchestration job {job_id} failed: {e}", exc_info=True)
        g.running_jobs[job_id].update({
            "status": "failed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "error": str(e),
        })


@router.get("/job/{job_id}", response_model=OrchestrationJobStatus)
async def get_job_status(job_id: str, api_key: str = Depends(require_api_key)):
    """
    Get the status of a specific orchestration job.
    
    Args:
        job_id: The job ID to check
        
    Returns:
        Job status information
    """
    if job_id not in g.running_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_data = g.running_jobs[job_id]
    return OrchestrationJobStatus(**job_data)

