"""
Synchronous enrichment router for property listings.

Provides REST endpoints for synchronous property listing enrichment
optimized for serverless environments.
"""

import asyncio
import time
from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from finder_enrichment_db_contracts import DescriptionAnalyticsRun, ImageAnalyticsRun, EnrichmentOrchestrationRun

from finder_enrichment.api.auth import require_api_key
from finder_enrichment.api.models import (
    EnrichmentResult,
    BatchEnrichmentResult,
    DescriptionAnalysisResult,
    ImageAnalysisResult,
    BatchImageAnalysisResult
)
from finder_enrichment.orchestrator.database_orchestrator import DatabaseEnrichmentOrchestrator
from finder_enrichment.agentic_services.description_analyser.description_analyser import DescriptionAnalyser
from finder_enrichment.agentic_services.image_analyser.image_analyser import ImageAnalyser
from finder_enrichment.orchestrator.exceptions import (
    ListingNotFoundError, EstateAgentError, DescriptionAnalysisError, 
    ImageAnalysisError, DatabaseError, EnrichmentError
)
from finder_enrichment.logger_config import setup_logger

logger = setup_logger(__name__)

# Create router
router = APIRouter()

@router.post("/enrich/listing/{listing_id}", response_model=EnrichmentResult)
async def enrich_listing(
    listing_id: str,
    api_key: str = Depends(require_api_key)
) -> EnrichmentResult:
    """
    Enrich a single property listing synchronously.

    This endpoint processes a listing immediately and returns the result.
    Processing time may take up to 300 seconds for listings with many images.

    Args:
        listing_id: The ID of the listing to enrich
        api_key: API key for authentication

    Returns:
        EnrichmentResult with the processing outcome
    """
    start_time = time.time()
    
    try:
        logger.info(f"Received enrichment request for listing: {listing_id}")
        result: EnrichmentOrchestrationRun = DatabaseEnrichmentOrchestrator().process_single_listing(listing_id)

        processing_time = time.time() - start_time
        logger.info(f"Enrichment completed for listing {listing_id} with status: success in {processing_time:.2f}s")
        
        return EnrichmentResult(
            original_listing_id=listing_id,
            enriched_listing_id=str(result.enriched_listing_id),
            status="success",
            enriched_data={"orchestration_run_id": result.id},
            processing_time_seconds=processing_time,
            image_count=len(result.image_analytics) if result.image_analytics else 0,
            timestamp=datetime.now(timezone.utc)
        )

    except ListingNotFoundError as e:
        processing_time = time.time() - start_time
        logger.warning(f"Listing not found: {listing_id} - {e}")
        raise HTTPException(status_code=404, detail=str(e))
        
    except EstateAgentError as e:
        processing_time = time.time() - start_time
        logger.error(f"Estate agent error for listing {listing_id}: {e}")
        raise HTTPException(status_code=422, detail=str(e))
        
    except DescriptionAnalysisError as e:
        processing_time = time.time() - start_time
        logger.error(f"Description analysis error for listing {listing_id}: {e}")
        raise HTTPException(status_code=422, detail=str(e))
        
    except ImageAnalysisError as e:
        processing_time = time.time() - start_time
        logger.error(f"Image analysis error for listing {listing_id}: {e}")
        raise HTTPException(status_code=422, detail=str(e))
        
    except DatabaseError as e:
        processing_time = time.time() - start_time
        logger.error(f"Database error for listing {listing_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
    except EnrichmentError as e:
        processing_time = time.time() - start_time
        logger.error(f"Enrichment error for listing {listing_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Unexpected error processing listing {listing_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred during processing")


@router.post("/enrich/listings", response_model=BatchEnrichmentResult)
async def enrich_listings_batch(
    listing_ids: List[str],
    api_key: str = Depends(require_api_key)
) -> BatchEnrichmentResult:
    """
    Enrich multiple property listings synchronously.

    This endpoint processes multiple listings and continues even if individual
    listings fail. Returns results for all processed listings.

    Args:
        listing_ids: List of listing IDs to process
        api_key: API key for authentication

    Returns:
        BatchEnrichmentResult with results for all processed listings
    """
    start_time = time.time()
    
    try:
        logger.info(f"Received batch enrichment request for {len(listing_ids)} listings")
        results: List[EnrichmentOrchestrationRun] = DatabaseEnrichmentOrchestrator().process_listings_by_ids(listing_ids)

        processing_time = time.time() - start_time
        logger.info(f"Batch enrichment completed for {len(listing_ids)} listings with {len(results)} successful in {processing_time:.2f}s")
        
        # Convert orchestration runs to enrichment results
        enrichment_results = []
        for result in results:
            enrichment_results.append(EnrichmentResult(
                original_listing_id=str(result.original_listing_id),
                enriched_listing_id=str(result.enriched_listing_id),
                status="success",
                enriched_data={"orchestration_run_id": result.id},
                processing_time_seconds=processing_time,
                image_count=len(result.image_analytics) if result.image_analytics else 0,
                timestamp=datetime.now(timezone.utc)
            ))
        
        return BatchEnrichmentResult(
            total_listings=len(listing_ids),
            successful_listings=len(enrichment_results),
            failed_listings=len(listing_ids) - len(enrichment_results),
            results=enrichment_results
        )

    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Error in batch processing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/enrich/description/{listing_id}", response_model=DescriptionAnalysisResult)
async def enrich_description(
    listing_id: str,
    api_key: str = Depends(require_api_key)
) -> DescriptionAnalysisResult:
    """
    Analyze the description of a single property listing synchronously.

    This endpoint processes a listing's description immediately and returns the result.

    Args:
        listing_id: The ID of the listing to analyze
        api_key: API key for authentication

    Returns:
        DescriptionAnalysisResult with the processing outcome
    """
    start_time = time.time()

    try:
        logger.info(f"Received description analysis request for listing: {listing_id}")

        description_analytics_run: DescriptionAnalyticsRun = DescriptionAnalyser().run_single_listing(int(listing_id))
        if not description_analytics_run:
            raise HTTPException(status_code=500, detail="Description analysis failed - no result returned")
        

        processing_time = time.time() - start_time
        return DescriptionAnalysisResult(
            enriched_listing_id=listing_id,
            status="success",
            analytics_run_id=description_analytics_run.id,
            processing_time_seconds=processing_time,
            timestamp=datetime.now(timezone.utc)
        )
            
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Description analysis error for listing {listing_id} after {processing_time:.2f}s: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/enrich/listing/images/{listing_id}", response_model=BatchImageAnalysisResult)
async def enrich_all_images_for_listing(
    listing_id: str,
    api_key: str = Depends(require_api_key)
) -> BatchImageAnalysisResult:
    """
    Analyze all images for a specific property listing synchronously.

    This endpoint processes all images for a listing immediately and returns the results.
    Processing time may take up to 300 seconds for listings with many images.

    Args:
        listing_id: The ID of the listing whose images to analyze
        api_key: API key for authentication

    Returns:
        BatchImageAnalysisResult with results for all processed images
    """
    start_time = time.time()

    try:
        logger.info(f"Received image analysis request for listing: {listing_id}")

        # Process the images with timeout
        result = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(None, _analyze_listing_images_sync, listing_id),
            timeout=300.0  # 300 second timeout for listing image analysis
        )

        processing_time = time.time() - start_time
        logger.info(f"Listing image analysis completed for listing {listing_id} with status: {result.status} in {processing_time:.2f}s")
        return result

    except asyncio.TimeoutError:
        processing_time = time.time() - start_time
        logger.error(f"Listing image analysis timeout for listing {listing_id} after {processing_time:.2f}s")
        return BatchImageAnalysisResult(
            total_images=0,
            successful_images=0,
            failed_images=0,
            status="timeout",
            error_message="Image analysis exceeded 300 second limit",
            processing_time_seconds=processing_time,
            results=[]
        )
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Listing image analysis error for listing {listing_id} after {processing_time:.2f}s: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/enrich/image/{image_id}", response_model=ImageAnalysisResult)
async def enrich_single_image(
    image_id: str,
    api_key: str = Depends(require_api_key)
) -> ImageAnalysisResult:
    """
    Analyze a single image synchronously.

    This endpoint processes a specific image immediately and returns the result.

    Args:
        image_id: The ID of the image to analyze
        api_key: API key for authentication

    Returns:
        ImageAnalysisResult with the processing outcome
    """
    start_time = time.time()

    try:
        logger.info(f"Received single image analysis request for image: {image_id}")

        # Process the image with timeout
        result = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(None, _analyze_single_image_sync, image_id),
            timeout=60.0  # 60 second timeout for single image analysis
        )

        processing_time = time.time() - start_time
        logger.info(f"Single image analysis completed for image {image_id} with status: {result.status} in {processing_time:.2f}s")
        return result

    except asyncio.TimeoutError:
        processing_time = time.time() - start_time
        logger.error(f"Single image analysis timeout for image {image_id} after {processing_time:.2f}s")
        return ImageAnalysisResult(
            original_image_id=image_id,
            status="timeout",
            error_message="Image analysis exceeded 60 second limit",
            processing_time_seconds=processing_time
        )
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Single image analysis error for image {image_id} after {processing_time:.2f}s: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# Helper functions for synchronous processing
def _analyze_description_sync(listing_id: str) -> DescriptionAnalysisResult:
    """
    Synchronous wrapper for description analysis.
    """
    start_time = time.time()
    
    try:
        description_analytics_run: DescriptionAnalyticsRun = DescriptionAnalyser().run_single_listing(int(listing_id))
        if not description_analytics_run:
            return DescriptionAnalysisResult(
                enriched_listing_id=listing_id,
                status="failed",
                error_message="Description analysis failed - no result returned",
                processing_time_seconds=time.time() - start_time
            )
        
        processing_time = time.time() - start_time
        return DescriptionAnalysisResult(
            enriched_listing_id=listing_id,
            status="success",
            analytics_run_id=description_analytics_run.id,
            processing_time_seconds=processing_time,
            timestamp=datetime.now(timezone.utc)
        )
    except Exception as e:
        processing_time = time.time() - start_time
        return DescriptionAnalysisResult(
            enriched_listing_id=listing_id,
            status="failed",
            error_message=str(e),
            processing_time_seconds=processing_time
        )


def _analyze_single_image_sync(image_id: str) -> ImageAnalysisResult:
    """
    Synchronous wrapper for single image analysis.
    """
    start_time = time.time()
    
    try:
        image_analytics_run: ImageAnalyticsRun = ImageAnalyser().run_single_image(int(image_id))
        if not image_analytics_run:
            return ImageAnalysisResult(
                original_image_id=image_id,
                status="failed",
                error_message="Image analysis failed - no result returned",
                processing_time_seconds=time.time() - start_time
            )
        
        processing_time = time.time() - start_time
        return ImageAnalysisResult(
            original_image_id=image_id,
            status="success",
            analytics_run_id=image_analytics_run.id,
            processing_time_seconds=processing_time,
            timestamp=datetime.now(timezone.utc)
        )
    except Exception as e:
        processing_time = time.time() - start_time
        return ImageAnalysisResult(
            original_image_id=image_id,
            status="failed",
            error_message=str(e),
            processing_time_seconds=processing_time
        )


def _analyze_listing_images_sync(listing_id: str) -> BatchImageAnalysisResult:
    """
    Synchronous wrapper for listing image analysis.
    """
    start_time = time.time()
    
    try:
        image_analytics_runs: List[ImageAnalyticsRun] = ImageAnalyser().run_single_listing(int(listing_id))
        if not image_analytics_runs:
            return BatchImageAnalysisResult(
                total_images=0,
                successful_images=0,
                failed_images=0,
                status="failed",
                error_message="Image analysis failed - no results returned",
                processing_time_seconds=time.time() - start_time,
                results=[]
            )
        
        # Convert to ImageAnalysisResult objects
        results = []
        for run in image_analytics_runs:
            results.append(ImageAnalysisResult(
                original_image_id=str(run.original_image_id),
                status="success",
                analytics_run_id=run.id,
                processing_time_seconds=time.time() - start_time,
                timestamp=datetime.now(timezone.utc)
            ))
        
        processing_time = time.time() - start_time
        return BatchImageAnalysisResult(
            total_images=len(results),
            successful_images=len(results),
            failed_images=0,
            status="success",
            processing_time_seconds=processing_time,
            results=results
        )
    except Exception as e:
        processing_time = time.time() - start_time
        return BatchImageAnalysisResult(
            total_images=0,
            successful_images=0,
            failed_images=0,
            status="failed",
            error_message=str(e),
            processing_time_seconds=processing_time,
            results=[]
        )
