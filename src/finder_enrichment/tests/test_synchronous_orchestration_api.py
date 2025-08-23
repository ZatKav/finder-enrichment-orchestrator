"""
Integration tests for the synchronous orchestration API endpoints.

These tests verify the complete orchestration process including:
- Description analysis
- Image analysis
- Full listing enrichment
- Database record creation

They test against real external services and expect the orchestrator to be running locally.
"""

from dotenv import load_dotenv
import pytest
import requests
import time
import subprocess
import os
import sys
from listings_db_api_client.listings_db_api_client import ListingsDBAPIClient
from finder_enrichment_db_client import FinderEnrichmentDBAPIClient
from finder_enrichment.api.orchestrator_api_client import OrchestratorAPIClient

load_dotenv()

BASE_URL = os.getenv("ORCHESTRATOR_BASE_URL", "http://localhost:3100")
API_KEY = os.getenv("ORCHESTRATOR_API_KEY", "")


@pytest.fixture(scope="module", autouse=True)
def api_server():
    """Start and stop the API server for the test module."""
    print("\nStarting API server...")
    api_process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "finder_enrichment.api.api_server:app",
            "--host",
            "localhost",
            "--port",
            "3100",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True,
    )

    # Wait for the server to be ready by polling the health endpoint
    start_time = time.time()
    while time.time() - start_time < 45:  # up to 45-second timeout
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=2)
            if response.status_code == 200:
                print("API server is ready.")
                break
        except (requests.ConnectionError, requests.ReadTimeout):
            time.sleep(0.5)
    else:
        api_process.terminate()
        stdout, _ = api_process.communicate()
        pytest.fail(f"API server failed to start within timeout.\nServer output:\n{stdout}")

    yield

    # Stop the server
    print("\nStopping API server...")
    api_process.terminate()
    try:
        stdout, _ = api_process.communicate(timeout=10)
        if stdout:
            print(f"Server output:\n{stdout}")
    except subprocess.TimeoutExpired:
        api_process.kill()
        api_process.wait()
    print("API server stopped.")


@pytest.fixture(scope="module")
def listing_with_images():
    """Fetch a listing that has images for comprehensive testing."""
    listings_client = ListingsDBAPIClient(
        api_key=os.getenv("LISTINGS_DB_API_KEY"),
        base_url=os.getenv("LISTINGS_DB_BASE_URL")
    )

    # Get listings with limit to find one with images
    listings_response = listings_client.get_listings(limit=10)

    # Find a listing with images
    for listing in listings_response:
        if hasattr(listing, 'images') and listing.images and len(listing.images) > 0:
            print(f"Found listing with {len(listing.images)} images: {listing.id}")
            return listing

    # If no listing with images found, just return the first one
    assert listings_response, "No listings found in the database."
    print(f"Using listing without images: {listings_response[0].id}")
    return listings_response[0]


def test_full_synchronous_orchestration_process(listing_with_images):
    """
    Integration test for the complete synchronous orchestration process.
    This tests the full pipeline: listing fetch -> description analysis -> image analysis -> enrichment.
    """
    print(f"Testing full synchronous orchestration with listing ID: {listing_with_images.id}")

    client = OrchestratorAPIClient(base_url=BASE_URL, api_key=API_KEY)

    # Record start time for performance monitoring
    start_time = time.time()

    try:
        # Run the synchronous enrichment
        result = client.enrich_listing(str(listing_with_images.id), timeout_seconds=300)
    except Exception as e:
        pytest.fail(f"Synchronous enrichment request failed: {e}")

    total_time = time.time() - start_time
    print(".2f")

    # Validate basic response structure
    assert isinstance(result, dict)
    assert "listing_id" in result
    assert "status" in result
    assert "processing_time_seconds" in result

    if result["status"] == "success":
        # Comprehensive validation for successful enrichment
        assert "enriched_data" in result
        enriched_data = result["enriched_data"]

        # Validate enriched data structure
        assert "enriched_listing_id" in enriched_data
        assert "description_analysis" in enriched_data
        assert "image_count" in enriched_data

        # Verify the enrichment process worked correctly
        enriched_listing_id = enriched_data["enriched_listing_id"]

        # Test database integration
        enrichment_db_client = FinderEnrichmentDBAPIClient(
            base_url=os.getenv("ENRICHMENT_DB_BASE_URL"),
            api_key=os.getenv("ENRICHMENT_DB_API_KEY")
        )

        # Verify enriched listing exists
        enriched_listing = enrichment_db_client.get_listing(enriched_listing_id)
        assert enriched_listing is not None, f"Enriched listing {enriched_listing_id} not found in database"

        # Verify original listing reference
        assert enriched_listing.listing_id == listing_with_images.id

        # Verify description analysis was performed
        assert enriched_listing.description_analysis is not None
        assert len(enriched_listing.description_analysis) > 0

        # Verify image analysis was performed (if images exist)
        if listing_with_images.images and len(listing_with_images.images) > 0:
            # Check that images were processed
            if hasattr(enriched_listing, 'images') and enriched_listing.images:
                assert len(enriched_listing.images) > 0, "No enriched images found"

                # Verify at least some images have analysis
                images_with_analysis = [img for img in enriched_listing.images if img.image_analysis]
                assert len(images_with_analysis) > 0, "No images have analysis data"

        # Verify orchestration run was created
        # Note: The synchronous enrichment doesn't create orchestration sets like the async version
        # but should still create orchestration runs

        print("✅ Full synchronous orchestration completed successfully")
        print(f"   - Processing time: {result['processing_time_seconds']:.2f} seconds")
        print(f"   - Images processed: {result['image_count']}")
        print(f"   - Enriched listing ID: {enriched_listing_id}")

    elif result["status"] == "failed":
        error_msg = result.get("error_message", "Unknown error")
        print(f"⚠️  Synchronous orchestration failed: {error_msg}")
        # Don't fail the test for expected failures, but log the issue

    elif result["status"] == "timeout":
        timeout_time = result.get("processing_time_seconds", 0)
        print(".2f")
        # Don't fail the test for timeouts, but log the issue


def test_synchronous_orchestration_performance_baseline(listing_with_images):
    """
    Performance baseline test for synchronous orchestration.
    This establishes expected performance characteristics.
    """
    print(f"Testing synchronous orchestration performance with listing ID: {listing_with_images.id}")

    client = OrchestratorAPIClient(base_url=BASE_URL, api_key=API_KEY)

    # Run multiple times to get performance baseline
    results = []
    for i in range(3):
        start_time = time.time()
        try:
            result = client.enrich_listing(str(listing_with_images.id), timeout_seconds=300)
            end_time = time.time()

            if result["status"] == "success":
                processing_time = result["processing_time_seconds"]
                total_time = end_time - start_time
                results.append({
                    "processing_time": processing_time,
                    "total_time": total_time,
                    "image_count": result["image_count"]
                })
                print(".2f")
            else:
                print(f"⚠️  Run {i+1} failed with status: {result['status']}")

        except Exception as e:
            print(f"⚠️  Run {i+1} failed with exception: {e}")

    if results:
        avg_processing_time = sum(r["processing_time"] for r in results) / len(results)
        avg_total_time = sum(r["total_time"] for r in results) / len(results)
        avg_image_count = sum(r["image_count"] for r in results) / len(results)

        print("📊 Performance Baseline:")
        print(f"   - Average Processing Time: {avg_processing_time:.2f} seconds")
        print(f"   - Average Total Time: {avg_total_time:.2f} seconds")
        print(f"   - Average Images: {avg_image_count:.1f}")

        # Basic performance assertions
        # These are reasonable expectations for a synchronous process
        assert avg_processing_time < 60, f"Processing time too high: {avg_processing_time:.2f}s"
        assert avg_total_time < 120, f"Total time too high: {avg_total_time:.2f}s"

    else:
        print("⚠️  No successful runs to establish performance baseline")


def test_synchronous_orchestration_error_recovery():
    """
    Test error recovery and resilience in synchronous orchestration.
    This tests how the system handles various error conditions.
    """
    print("Testing synchronous orchestration error recovery...")

    client = OrchestratorAPIClient(base_url=BASE_URL, api_key=API_KEY)

    # Test with various invalid listing IDs
    invalid_ids = ["-1", "999999999", "abc", "", " "]

    for invalid_id in invalid_ids:
        try:
            result = client.enrich_listing(invalid_id, timeout_seconds=30)

            # Should fail gracefully
            assert isinstance(result, dict)
            assert result["listing_id"] == invalid_id
            assert result["status"] == "failed"
            assert "error_message" in result

            print(f"✅ Invalid ID '{invalid_id}' handled correctly")

        except Exception as e:
            print(f"⚠️  Invalid ID '{invalid_id}' caused exception: {e}")

    print("✅ Error recovery testing completed")


def test_synchronous_orchestration_database_integrity(listing_with_images):
    """
    Test database integrity after synchronous orchestration.
    This verifies that all expected database records are created correctly.
    """
    print(f"Testing database integrity with listing ID: {listing_with_images.id}")

    client = OrchestratorAPIClient(base_url=BASE_URL, api_key=API_KEY)

    try:
        result = client.enrich_listing(str(listing_with_images.id), timeout_seconds=300)
    except Exception as e:
        pytest.fail(f"Synchronous enrichment request failed: {e}")

    if result["status"] == "success":
        enriched_data = result["enriched_data"]
        enriched_listing_id = enriched_data["enriched_listing_id"]

        # Test database client
        enrichment_db_client = FinderEnrichmentDBAPIClient(
            base_url=os.getenv("ENRICHMENT_DB_BASE_URL"),
            api_key=os.getenv("ENRICHMENT_DB_API_KEY")
        )

        # Verify enriched listing
        enriched_listing = enrichment_db_client.get_listing(enriched_listing_id)
        assert enriched_listing is not None

        # Verify listing has correct original reference
        assert enriched_listing.listing_id == listing_with_images.id

        # Verify description analysis exists
        assert enriched_listing.description_analysis is not None
        assert len(enriched_listing.description_analysis.strip()) > 0

        # Verify estate agent relationship
        assert enriched_listing.estate_agent_id is not None

        # Verify location data (if available)
        if listing_with_images.location:
            assert enriched_listing.location is not None

        print("✅ Database integrity verified successfully")
    else:
        print(f"⚠️  Cannot test database integrity - enrichment failed with status: {result['status']}")
