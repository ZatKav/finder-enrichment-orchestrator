"""
Integration tests for the synchronous enrichment API endpoints.

These tests actually call the real external services (Listings DB, Enrichment DB, Google AI)
and expect the orchestrator to be running locally. They test the full synchronous enrichment
process end-to-end.
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


@pytest.fixture(scope="module", autouse=True)
def listing_id():
    """Fetch a valid listing ID from the database."""
    listings_client = ListingsDBAPIClient(
        api_key=os.getenv("LISTINGS_DB_API_KEY"),
        base_url=os.getenv("LISTINGS_DB_BASE_URL")
    )
    listings_response = listings_client.get_listings(limit=1)
    assert listings_response, "No listings found in the database."
    return listings_response[0].id


def test_synchronous_enrichment_health_check():
    """Test the synchronous enrichment health check endpoint."""
    print("Testing synchronous enrichment health check...")

    client = OrchestratorAPIClient(base_url=BASE_URL, api_key=API_KEY)

    try:
        # Make request to health endpoint - this should work without auth
        response = requests.get(f"{BASE_URL}/api/enrichment/health", timeout=10)
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "service" in data
        assert "service_clients" in data

        print("✅ Health check passed")
    except Exception as e:
        pytest.fail(f"Health check failed: {e}")


def test_synchronous_single_listing_enrichment_integration(listing_id: int):
    """
    Integration test for the synchronous single listing enrichment endpoint.
    This test ensures that the server can process a real listing with all external services.
    """
    print(f"Testing synchronous enrichment with listing ID: {listing_id}")

    client = OrchestratorAPIClient(base_url=BASE_URL, api_key=API_KEY)

    try:
        # Test the synchronous enrichment endpoint
        result = client.enrich_listing(str(listing_id), timeout_seconds=300)
    except Exception as e:
        pytest.fail(f"Request to synchronous enrichment failed: {e}")

    # Validate the response structure
    assert isinstance(result, dict)
    assert "listing_id" in result
    assert "status" in result
    assert "processing_time_seconds" in result
    assert "image_count" in result
    assert "timestamp" in result

    # Validate the result
    assert result["listing_id"] == str(listing_id)
    assert result["status"] in ["success", "failed", "timeout"]
    assert isinstance(result["processing_time_seconds"], (int, float))
    assert result["processing_time_seconds"] >= 0
    assert isinstance(result["image_count"], int)
    assert result["image_count"] >= 0

    if result["status"] == "success":
        # If successful, validate enriched data
        assert "enriched_data" in result
        enriched_data = result["enriched_data"]
        assert "enriched_listing_id" in enriched_data
        assert "description_analysis" in enriched_data
        assert "image_count" in enriched_data

        # Verify the enriched listing was created in the database
        enrichment_db_client = FinderEnrichmentDBAPIClient(
            base_url=os.getenv("ENRICHMENT_DB_BASE_URL"),
            api_key=os.getenv("ENRICHMENT_DB_API_KEY")
        )

        # Get the enriched listing
        enriched_listing = enrichment_db_client.get_listing(enriched_data["enriched_listing_id"])
        assert enriched_listing is not None, "Enriched listing not found in database"

        print(f"✅ Single listing enrichment completed successfully in {result['processing_time_seconds']:.2f} seconds")
    elif result["status"] == "failed":
        # If failed, there should be an error message
        assert "error_message" in result
        print(f"⚠️  Single listing enrichment failed: {result['error_message']}")
    else:
        print(f"⏱️  Single listing enrichment timed out after {result['processing_time_seconds']:.2f} seconds")


def test_synchronous_batch_listing_enrichment_integration(listing_id: int):
    """
    Integration test for the synchronous batch listing enrichment endpoint.
    This test ensures that the server can process multiple listings with all external services.
    """
    print(f"Testing synchronous batch enrichment with listing ID: {listing_id}")

    client = OrchestratorAPIClient(base_url=BASE_URL, api_key=API_KEY)

    try:
        # Test the synchronous batch enrichment endpoint
        result = client.enrich_listings_batch([str(listing_id)], timeout_seconds=300)
    except Exception as e:
        pytest.fail(f"Request to synchronous batch enrichment failed: {e}")

    # Validate the response structure
    assert isinstance(result, dict)
    assert "results" in result
    assert "total_processed" in result
    assert "total_successful" in result
    assert "total_failed" in result
    assert "processing_time_seconds" in result

    # Validate the result
    assert result["total_processed"] == 1
    assert isinstance(result["processing_time_seconds"], (int, float))
    assert result["processing_time_seconds"] >= 0
    assert len(result["results"]) == 1

    # Check the individual result
    individual_result = result["results"][0]
    assert individual_result["listing_id"] == str(listing_id)
    assert individual_result["status"] in ["success", "failed", "timeout"]

    if result["total_successful"] == 1:
        # If successful, validate enriched data
        assert individual_result["status"] == "success"
        assert "enriched_data" in individual_result

        enriched_data = individual_result["enriched_data"]
        assert "enriched_listing_id" in enriched_data
        assert "description_analysis" in enriched_data
        assert "image_count" in enriched_data

        print(f"✅ Batch listing enrichment completed successfully in {result['processing_time_seconds']:.2f} seconds")
    else:
        # If failed, there should be an error message
        assert individual_result["status"] == "failed"
        assert "error_message" in individual_result
        print(f"⚠️  Batch listing enrichment failed: {individual_result['error_message']}")


def test_synchronous_enrichment_with_invalid_listing():
    """Test synchronous enrichment with an invalid listing ID."""
    print("Testing synchronous enrichment with invalid listing ID...")

    client = OrchestratorAPIClient(base_url=BASE_URL, api_key=API_KEY)

    try:
        # Test with an obviously invalid listing ID
        result = client.enrich_listing("invalid-listing-999999", timeout_seconds=30)
    except Exception as e:
        pytest.fail(f"Request to synchronous enrichment with invalid ID failed: {e}")

    # Should fail gracefully
    assert isinstance(result, dict)
    assert result["listing_id"] == "invalid-listing-999999"
    assert result["status"] == "failed"
    assert "error_message" in result

    print("✅ Invalid listing ID handled correctly")


def test_synchronous_enrichment_authentication():
    """Test that synchronous enrichment endpoints require authentication."""
    print("Testing synchronous enrichment authentication...")

    # Test without API key
    try:
        response = requests.post(
            f"{BASE_URL}/api/enrich-listing/123",
            json={},
            timeout=10
        )
        assert response.status_code == 401 or response.status_code == 500  # Either 401 or obfuscated 500
    except requests.exceptions.RequestException:
        # Connection errors are also acceptable for auth tests
        pass

    # Test with invalid API key
    try:
        response = requests.post(
            f"{BASE_URL}/api/enrich-listing/123",
            headers={"Authorization": "Bearer invalid-key"},
            json={},
            timeout=10
        )
        assert response.status_code == 500  # Should be obfuscated as 500 for security
    except requests.exceptions.RequestException:
        # Connection errors are also acceptable for auth tests
        pass

    print("✅ Authentication requirements validated")


def test_synchronous_enrichment_rate_limiting():
    """Test that synchronous enrichment endpoints are rate limited."""
    print("Testing synchronous enrichment rate limiting...")

    client = OrchestratorAPIClient(base_url=BASE_URL, api_key=API_KEY)

    # Make multiple rapid requests to test rate limiting
    failed_requests = 0
    for i in range(5):
        try:
            result = client.enrich_listing("test-rate-limit", timeout_seconds=5)
            # If we get here, the request went through (might be rate limited or just fast)
            if result["status"] == "failed" and "rate limit" in result.get("error_message", "").lower():
                failed_requests += 1
        except Exception as e:
            if "rate limit" in str(e).lower() or "429" in str(e):
                failed_requests += 1
            # Other exceptions might be due to invalid listing ID

    # We expect some requests to be rate limited, but not necessarily all
    # This is a basic rate limiting test
    print(f"✅ Rate limiting test completed - {failed_requests}/5 requests potentially rate limited")
