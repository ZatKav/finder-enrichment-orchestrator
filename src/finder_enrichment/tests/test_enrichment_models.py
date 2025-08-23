"""
Unit tests for enrichment API response models.

Tests the Pydantic models used in the enrichment API responses.
"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from finder_enrichment.api.models import EnrichmentResult, BatchEnrichmentResult


class TestAPIEnrichmentResult:
    """Test cases for the API EnrichmentResult model."""

    def test_enrichment_result_creation(self):
        """Test creating an API EnrichmentResult with all fields."""
        timestamp = datetime.now(timezone.utc)

        result = EnrichmentResult(
            enriched_listing_id="test-listing-123",
            status="success",
            enriched_data={"enriched_listing_id": 456},
            processing_time_seconds=2.5,
            image_count=3,
            timestamp=timestamp
        )

        assert result.enriched_listing_id == "test-listing-123"
        assert result.status == "success"
        assert result.enriched_data == {"enriched_listing_id": 456}
        assert result.processing_time_seconds == 2.5
        assert result.image_count == 3
        assert result.timestamp == timestamp
        assert result.error_message is None

    def test_enrichment_result_optional_fields(self):
        """Test creating an API EnrichmentResult with optional fields."""
        result = EnrichmentResult(
            enriched_listing_id="test-listing-456",
            status="success",
            processing_time_seconds=1.0,
            image_count=0,
            timestamp=datetime.now(timezone.utc)
        )

        assert result.enriched_data is None
        assert result.error_message is None
        assert result.timestamp is not None  # Should be auto-generated

    def test_enrichment_result_with_error(self):
        """Test creating an API EnrichmentResult with error status."""
        result = EnrichmentResult(
            enriched_listing_id="failed-listing-123",
            status="failed",
            error_message="Network timeout",
            processing_time_seconds=1.0,
            image_count=0,
            timestamp=datetime.now(timezone.utc)
        )

        assert result.status == "failed"
        assert result.error_message == "Network timeout"
        assert result.enriched_data is None

    def test_enrichment_result_timeout_status(self):
        """Test creating an API EnrichmentResult with timeout status."""
        result = EnrichmentResult(
            enriched_listing_id="timeout-listing-123",
            status="timeout",
            error_message="Processing exceeded 150 second limit",
            processing_time_seconds=150.0,
            image_count=5,
            timestamp=datetime.now(timezone.utc)
        )

        assert result.status == "timeout"
        assert "exceeded 150 second limit" in result.error_message

    def test_enrichment_result_invalid_status(self):
        """Test that invalid status values raise validation error."""
        with pytest.raises(ValidationError):
            EnrichmentResult(
                enriched_listing_id="test-listing-123",
                status="invalid_status",
                processing_time_seconds=1.0,
                image_count=0
            )

    def test_enrichment_result_negative_processing_time(self):
        """Test that negative processing time raises validation error."""
        with pytest.raises(ValidationError):
            EnrichmentResult(
                enriched_listing_id="test-listing-123",
                status="success",
                processing_time_seconds=-1.0,
                image_count=0
            )

    def test_enrichment_result_negative_image_count(self):
        """Test that negative image count raises validation error."""
        with pytest.raises(ValidationError):
            EnrichmentResult(
                enriched_listing_id="test-listing-123",
                status="success",
                processing_time_seconds=1.0,
                image_count=-1
            )


class TestAPIBatchEnrichmentResult:
    """Test cases for the API BatchEnrichmentResult model."""

    def test_batch_enrichment_result_creation(self):
        """Test creating an API BatchEnrichmentResult."""
        results = [
            EnrichmentResult(
                enriched_listing_id="listing-1",
                status="success",
                processing_time_seconds=1.5,
                image_count=2,
                timestamp=datetime.now(timezone.utc)
            ),
            EnrichmentResult(
                enriched_listing_id="listing-2",
                status="failed",
                error_message="Network error",
                processing_time_seconds=0.5,
                image_count=1,
                timestamp=datetime.now(timezone.utc)
            )
        ]

        batch_result = BatchEnrichmentResult(
            results=results,
            total_processed=2,
            total_successful=1,
            total_failed=1,
            processing_time_seconds=2.0
        )

        assert batch_result.results == results
        assert batch_result.total_processed == 2
        assert batch_result.total_successful == 1
        assert batch_result.total_failed == 1
        assert batch_result.processing_time_seconds == 2.0

    def test_batch_enrichment_result_empty_results(self):
        """Test creating an API BatchEnrichmentResult with empty results."""
        batch_result = BatchEnrichmentResult(
            results=[],
            total_processed=0,
            total_successful=0,
            total_failed=0,
            processing_time_seconds=0.0
        )

        assert batch_result.results == []
        assert batch_result.total_processed == 0
        assert batch_result.total_successful == 0
        assert batch_result.total_failed == 0

    def test_batch_enrichment_result_all_successful(self):
        """Test batch result with all successful enrichments."""
        results = [
            EnrichmentResult(
                enriched_listing_id="listing-1",
                status="success",
                processing_time_seconds=1.0,
                image_count=2,
                timestamp=datetime.now(timezone.utc)
            ),
            EnrichmentResult(
                enriched_listing_id="listing-2",
                status="success",
                processing_time_seconds=1.5,
                image_count=3,
                timestamp=datetime.now(timezone.utc)
            )
        ]

        batch_result = BatchEnrichmentResult(
            results=results,
            total_processed=2,
            total_successful=2,
            total_failed=0,
            processing_time_seconds=2.5
        )

        assert batch_result.total_successful == 2
        assert batch_result.total_failed == 0

    def test_batch_enrichment_result_all_failed(self):
        """Test batch result with all failed enrichments."""
        results = [
            EnrichmentResult(
                enriched_listing_id="listing-1",
                status="failed",
                error_message="Error 1",
                processing_time_seconds=0.5,
                image_count=0,
                timestamp=datetime.now(timezone.utc)
            ),
            EnrichmentResult(
                enriched_listing_id="listing-2",
                status="failed",
                error_message="Error 2",
                processing_time_seconds=0.3,
                image_count=0,
                timestamp=datetime.now(timezone.utc)
            )
        ]

        batch_result = BatchEnrichmentResult(
            results=results,
            total_processed=2,
            total_successful=0,
            total_failed=2,
            processing_time_seconds=0.8
        )

        assert batch_result.total_successful == 0
        assert batch_result.total_failed == 2

    def test_batch_enrichment_result_mixed_statuses(self):
        """Test batch result with mixed success/failure/timeout statuses."""
        results = [
            EnrichmentResult(
                enriched_listing_id="listing-1",
                status="success",
                processing_time_seconds=2.0,
                image_count=2,
                timestamp=datetime.now(timezone.utc)
            ),
            EnrichmentResult(
                enriched_listing_id="listing-2",
                status="failed",
                error_message="Network error",
                processing_time_seconds=0.5,
                image_count=1,
                timestamp=datetime.now(timezone.utc)
            ),
            EnrichmentResult(
                enriched_listing_id="listing-3",
                status="timeout",
                error_message="Processing timeout",
                processing_time_seconds=150.0,
                image_count=5,
                timestamp=datetime.now(timezone.utc)
            )
        ]

        batch_result = BatchEnrichmentResult(
            results=results,
            total_processed=3,
            total_successful=1,
            total_failed=2,  # failed + timeout both count as failed
            processing_time_seconds=152.5
        )

        assert batch_result.total_processed == 3
        assert batch_result.total_successful == 1
        assert batch_result.total_failed == 2

        # Check individual result types
        successful = [r for r in batch_result.results if r.status == "success"]
        failed = [r for r in batch_result.results if r.status == "failed"]
        timeout = [r for r in batch_result.results if r.status == "timeout"]

        assert len(successful) == 1
        assert len(failed) == 1
        assert len(timeout) == 1
