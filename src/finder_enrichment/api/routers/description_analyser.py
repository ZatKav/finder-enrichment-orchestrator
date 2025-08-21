from datetime import datetime, timezone
from fastapi import APIRouter, BackgroundTasks, Depends

from finder_enrichment.agentic_services.description_analyser.description_analyser import DescriptionAnalyser
from finder_enrichment.api.models import OrchestrationJobResponse
from finder_enrichment.api.utils import generate_datetime_string
import finder_enrichment.api.globals as g
from finder_enrichment.api.auth import require_api_key
from finder_enrichment.logger_config import setup_logger

router = APIRouter()
logger = setup_logger(__name__)


@router.post("/run_description_analyser/{listing_id}", response_model=OrchestrationJobResponse)
async def run_description_analyser(
    background_tasks: BackgroundTasks,
    listing_id: int,
    api_key: str = Depends(require_api_key),
):
    """
    Run the description analyser to process a single listing that is already in the database.
    """
    job_id = f"description_analyser_{listing_id}_{generate_datetime_string()}"
    
    g.running_jobs[job_id] = {
        "job_id": job_id,
        "status": "starting",
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    
    background_tasks.add_task(run_description_analyser_job, job_id, listing_id)
    
    logger.info(f"Started description analyser job for listing {listing_id}")
    
    return OrchestrationJobResponse(
        job_id=job_id,
        status="starting",
        message=f"Description analyser job started for listing {listing_id}",
        started_at=g.running_jobs[job_id]["started_at"],
    )
    
    
def run_description_analyser_job(job_id: str, listing_id: int):
    """Run the description analyser process in background."""
    
    try:
        logger.info(f"Starting description analyser job for listing {listing_id}")
        g.running_jobs[job_id]["status"] = "running"
        
        if not g.orchestrator:
            raise RuntimeError("Orchestrator not initialized")
        
        description_analyser = DescriptionAnalyser()
        description_analytics_run = description_analyser.run_single_listing(listing_id)
        if not description_analytics_run:
            error_msg = (
                f"Description analysis failed for listing {listing_id}. This could be due to: missing listing data, empty description, or external service unavailability. Check /health endpoint for service status."
            )
            g.running_jobs[job_id].update({
                "status": "failed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "error": error_msg,
            })
            return
        
        # Update job status
        g.running_jobs[job_id].update({
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "analytics_run_id": description_analytics_run.id,
        })
        
    except Exception as e:
        error_msg = (
            f"Description analyser job failed: {str(e)}. Check that both the listings database (port 8000) and enrichment database (port 8200) are running and accessible."
        )
        logger.error(f"Description analyser job for listing {listing_id} failed: {e}", exc_info=True)
        g.running_jobs[job_id].update({
            "status": "failed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "error": error_msg,
        })
