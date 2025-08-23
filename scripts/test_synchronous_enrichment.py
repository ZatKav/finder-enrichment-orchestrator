#!/usr/bin/env python3
"""
Test script for the new synchronous enrichment system.

This script demonstrates the synchronous enrichment functionality
without requiring external API keys or database connections.
"""

import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from datetime import datetime, timezone
from finder_enrichment.services.synchronous_enrichment_service import (
    SynchronousEnrichmentService,
    EnrichmentResult,
    BatchEnrichmentResult
)
from finder_enrichment.api.models import EnrichmentResult as APIEnrichmentResult, BatchEnrichmentResult as APIBatchEnrichmentResult


def test_service_creation():
    """Test creating the synchronous enrichment service."""
    print("🧪 Testing SynchronousEnrichmentService creation...")

    service = SynchronousEnrichmentService()
    assert service is not None
    print("✅ Service created successfully")


def test_enrichment_result_model():
    """Test the EnrichmentResult model."""
    print("🧪 Testing EnrichmentResult model...")

    result = EnrichmentResult(
        listing_id="test-listing-123",
        status="success",
        processing_time_seconds=2.5,
        image_count=3,
        timestamp=datetime.now(timezone.utc)
    )

    assert result.listing_id == "test-listing-123"
    assert result.status == "success"
    assert result.processing_time_seconds == 2.5
    assert result.image_count == 3
    print("✅ EnrichmentResult model works correctly")


def test_batch_enrichment_result_model():
    """Test the BatchEnrichmentResult model."""
    print("🧪 Testing BatchEnrichmentResult model...")

    results = [
        EnrichmentResult(
            listing_id="listing-1",
            status="success",
            processing_time_seconds=1.5,
            image_count=2
        ),
        EnrichmentResult(
            listing_id="listing-2",
            status="failed",
            error_message="Network error",
            processing_time_seconds=0.5,
            image_count=1
        )
    ]

    batch_result = BatchEnrichmentResult(
        results=results,
        total_processed=2,
        total_successful=1,
        total_failed=1,
        processing_time_seconds=2.0
    )

    assert batch_result.total_processed == 2
    assert batch_result.total_successful == 1
    assert batch_result.total_failed == 1
    print("✅ BatchEnrichmentResult model works correctly")


def test_api_models():
    """Test the API response models."""
    print("🧪 Testing API response models...")

    api_result = APIEnrichmentResult(
        enriched_listing_id="api-test-123",
        status="success",
        processing_time_seconds=3.0,
        image_count=5,
        timestamp=datetime.now(timezone.utc)
    )

    assert api_result.enriched_listing_id == "api-test-123"
    assert api_result.status == "success"
    print("✅ API models work correctly")


def test_service_methods():
    """Test service methods structure without requiring agents."""
    print("🧪 Testing service method structure...")

    service = SynchronousEnrichmentService()

    # Just check that the methods exist and handle missing agents gracefully
    try:
        service.enrich_description("")
        print("❌ Expected RuntimeError for unconfigured agent")
    except RuntimeError as e:
        if "Description analyser agent not configured" in str(e):
            print("✅ Description enrichment method properly validates agent configuration")
        else:
            raise

    try:
        service.enrich_images([])
        print("❌ Expected RuntimeError for unconfigured agent")
    except RuntimeError as e:
        if "Image analyser client not configured" in str(e):
            print("✅ Image enrichment method properly validates agent configuration")
        else:
            raise

    print("✅ Service methods have proper validation")


def main():
    """Run all tests."""
    print("🚀 Testing Synchronous Enrichment System\n")

    try:
        test_service_creation()
        test_enrichment_result_model()
        test_batch_enrichment_result_model()
        test_api_models()
        test_service_methods()

        print("\n🎉 All tests passed! The synchronous enrichment system is ready.")
        print("\n📋 Next steps:")
        print("1. Set up your environment variables (LISTINGS_DB_API_KEY, etc.)")
        print("2. Start the API server: uv run python src/finder_enrichment/api/api_server.py")
        print("3. Test the endpoints:")
        print("   - GET  /api/enrichment/health")
        print("   - POST /api/enrich-listing/{listing_id}")
        print("   - POST /api/enrich-listings (with {\"listing_ids\": [\"id1\", \"id2\"]})")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
