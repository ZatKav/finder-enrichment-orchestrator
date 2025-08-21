from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, BackgroundTasks, Depends
from finder_enrichment_db_contracts import ImageAnalyticsRun

from finder_enrichment.agentic_services.image_analyser.image_analyser import ImageAnalyser
from finder_enrichment.api.models import OrchestrationJobResponse
from finder_enrichment.api.utils import generate_datetime_string
import finder_enrichment.api.globals as g
from finder_enrichment.api.auth import require_api_key
from finder_enrichment.logger_config import setup_logger

router = APIRouter()
logger = setup_logger(__name__)


@router.post("/run_image_analyser/listing/{listing_id}", response_model=OrchestrationJobResponse)
async def run_image_analyser_by_listing_id(
    background_tasks: BackgroundTasks,
    listing_id: int,
    api_key: str = Depends(require_api_key),
):
    """
    Run the image analyser to process a single listing that is already in the database.
    """
    
    job_id = f"image_analyser_by_listing_id_{listing_id}_{generate_datetime_string()}"
    
    g.running_jobs[job_id] = {
        "job_id": job_id,
        "status": "starting",
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    
    background_tasks.add_task(run_image_analyser_by_listing_id_job, job_id, listing_id)
    
    logger.info(f"Started image analyser job for listing {listing_id}")
    
    return OrchestrationJobResponse(
        job_id=job_id,
        status="starting",
        message=f"Image analyser job started for listing {listing_id}",
        started_at=g.running_jobs[job_id]["started_at"],
    )


def run_image_analyser_by_listing_id_job(job_id: str, listing_id: int):
    """Run the image analyser process in background."""
    
    try:
        logger.info(f"Starting image analyser job for listing {listing_id}")
        g.running_jobs[job_id]["status"] = "running"
        
        if not g.orchestrator:
            raise RuntimeError("Orchestrator not initialized")
        
        image_analyser = ImageAnalyser()
        image_analytics_runs: List[ImageAnalyticsRun] = image_analyser.run_single_listing(listing_id)
        if not image_analytics_runs:
            error_msg = f"Image analysis failed for listing {listing_id}. This could be due to: missing listing data or external service unavailability. Check /health endpoint for service status."
            g.running_jobs[job_id].update({
                "status": "failed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "error": error_msg,
            })
            return
        
        g.running_jobs[job_id].update({
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "analytics_run_ids": [image_analytics_run.id for image_analytics_run in image_analytics_runs],
        })

    except Exception as e:
        error_msg = f"Image analyser job failed: {str(e)}. Check that both the listings database (port 8000) and enrichment database (port 8200) are running and accessible."
        logger.error(f"Image analyser job for listing {listing_id} failed: {e}", exc_info=True)
        g.running_jobs[job_id].update({
            "status": "failed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "error": error_msg,
        })


@router.post("/run_image_analyser/image/{image_id}", response_model=OrchestrationJobResponse)
async def run_image_analyser_by_image_id(
    background_tasks: BackgroundTasks,
    image_id: int,
    api_key: str = Depends(require_api_key),
):
    """
    Run the image analyser to process a single listing that is already in the database.
    """
    
    job_id = f"image_analyser_by_image_id_{image_id}_{generate_datetime_string()}"
    
    g.running_jobs[job_id] = {
        "job_id": job_id,
        "status": "starting",
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    
    background_tasks.add_task(run_image_analyser_by_image_id_job, job_id, image_id)
    
    logger.info(f"Started image analyser job for image {image_id}")
    
    return OrchestrationJobResponse(
        job_id=job_id,
        status="starting",
        message=f"Image analyser job started for image {image_id}",
        started_at=g.running_jobs[job_id]["started_at"],
    )


def run_image_analyser_by_image_id_job(job_id: str, image_id: int):
    """Run the image analyser process in background."""
    
    try:
        logger.info(f"Starting image analyser job for image {image_id}")
        g.running_jobs[job_id]["status"] = "running"
        
        if not g.orchestrator:
            raise RuntimeError("Orchestrator not initialized")
        
        image_analyser = ImageAnalyser()
        image_analytics_run: ImageAnalyticsRun = image_analyser.run_single_image(image_id)
        if not image_analytics_run:
            error_msg = f"Image analysis failed for image {image_id}. This could be due to: missing image data or external service unavailability. Check /health endpoint for service status."
            g.running_jobs[job_id].update({
                "status": "failed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "error": error_msg,
            })
            return
        
        g.running_jobs[job_id].update({
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "analytics_run_id": image_analytics_run.id,
        })

    except Exception as e:
        error_msg = f"Image analyser job failed: {str(e)}. Check that both the listings database (port 8000) and enrichment database (port 8200) are running and accessible."
        logger.error(f"Image analyser job for image {image_id} failed: {e}", exc_info=True)
        g.running_jobs[job_id].update({
            "status": "failed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "error": error_msg,
        })