from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime, timezone


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


class EnrichmentResult(BaseModel):
    """Result model for individual listing enrichment."""
    original_listing_id: int
    enriched_listing_id: str
    status: str  # "success", "failed", "timeout"
    enriched_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    processing_time_seconds: float
    image_count: int
    timestamp: datetime


class BatchEnrichmentResult(BaseModel):
    """Result model for batch listing enrichment."""
    results: List[EnrichmentResult]
    total_processed: int
    total_failed: int
    total_successful: int
    processing_time_seconds: float


class DescriptionAnalysisResult(BaseModel):
    """Result model for individual description analysis."""
    original_listing_id: int
    enriched_listing_id: int
    status: str  # "success", "failed", "timeout"
    analytics_run_id: Optional[int] = None
    error_message: Optional[str] = None
    processing_time_seconds: float
    timestamp: datetime


class ImageAnalysisResult(BaseModel):
    """Result model for individual image analysis."""
    original_image_id: int
    enriched_image_id: int
    original_listing_id: int
    enriched_listing_id: int
    status: str  # "success", "failed", "timeout"
    analytics_run_id: Optional[int] = None
    error_message: Optional[str] = None
    processing_time_seconds: float
    timestamp: datetime


class BatchImageAnalysisResult(BaseModel):
    """Result model for batch image analysis of a listing."""
    listing_id: str
    status: str  # "success", "failed", "timeout"
    analytics_run_ids: Optional[List[int]] = None
    error_message: Optional[str] = None
    processing_time_seconds: float
    image_count: int
    timestamp: datetime