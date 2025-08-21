
from typing import List
import pytest
import requests
import time
import subprocess
import os
import sys
from listings_db_api_client.listings_db_api_client import ListingsDBAPIClient
from finder_enrichment_db_client import FinderEnrichmentDBAPIClient
from dotenv import load_dotenv
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
    while time.time() - start_time < 45:  # 45-second timeout
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
    listings_client = ListingsDBAPIClient(api_key=os.getenv("LISTINGS_DB_API_KEY"), base_url=os.getenv("LISTINGS_DB_BASE_URL"))
    listings_response = listings_client.get_listings(limit=1)
    assert listings_response, "No listings found in the database."
    return listings_response[0].id

@pytest.fixture(scope="module", autouse=True)
def image_id(listing_id: int):
    """Fetch a valid image ID from the database."""
    listings_client = ListingsDBAPIClient(api_key=os.getenv("LISTINGS_DB_API_KEY"), base_url=os.getenv("LISTINGS_DB_BASE_URL"))
    images_response = listings_client.get_images_for_listing(listing_id)
    
    assert images_response, "No images found for the listing."
    return images_response[0].id

def test_run_image_analyser_by_image_id_integration(image_id: int):
    """
    Integration test for the image analyser endpoint.
    This test ensures that the server can be started and that the endpoint
    responds correctly to a valid request.
    """
    print(f"Testing with image ID: {image_id}")

    client = OrchestratorAPIClient(base_url=BASE_URL, api_key=API_KEY)

    try:
        job_response = client.run_image_analyser_by_image_id(image_id)
    except Exception as e:
        pytest.fail(f"Request to run image analyser failed: {e}")

    assert job_response.status == "starting"
    assert job_response.job_id

    job_id = job_response.job_id
    
    # Poll for completion
    start_time = time.time()
    while time.time() - start_time < 2000: # 20 second timeout for job
        time.sleep(2)
        try:
            status = client.get_job_status(job_id)
        except Exception as e:
            pytest.fail(f"Request to get job status failed: {e}")

        if status.status == "completed":
            # Final check to verify the database record
            analytics_run_id = status.analytics_run_id
            assert analytics_run_id is not None, "analytics_run_id not found in job status"

            # Verify the record in the enrichment DB
            enrichment_db_client = FinderEnrichmentDBAPIClient(
                os.getenv("ENRICHMENT_DB_BASE_URL", "http://localhost:8200"),
                os.getenv("ENRICHMENT_DB_API_KEY"),
            )
            image_analytics_run = enrichment_db_client.get_image_analytics(
                analytics_run_id
            )
            assert (
                image_analytics_run is not None
            ), f"Record not found in DB. Status: {image_analytics_run}"
            assert status.error is None
            break
        elif status.status == "failed":
            pytest.fail(f"Job failed with error: {status.error}")
    else:
        pytest.fail("Job did not complete in time")
        

def test_run_image_analyser_by_listing_id_integration(listing_id: int):
    """
    Integration test for the image analyser endpoint.
    This test ensures that the server can be started and that the endpoint
    responds correctly to a valid request.
    """
    print(f"Testing with listing ID: {listing_id}")

    client = OrchestratorAPIClient(base_url=BASE_URL, api_key=API_KEY)

    try:
        job_response = client.run_image_analyser_by_listing_id(listing_id)
    except Exception as e:
        pytest.fail(f"Request to run image analyser failed: {e}")

    assert job_response.status == "starting"
    assert job_response.job_id

    job_id = job_response.job_id
    
    # Poll for completion
    start_time = time.time()
    while time.time() - start_time < 20000: # 200 second timeout for job
        time.sleep(2)
        try:
            status = client.get_job_status(job_id)
        except Exception as e:
            pytest.fail(f"Request to get job status failed: {e}")

        if status.status == "completed":
            # Final check to verify the database record
            analytics_run_ids = status.analytics_run_ids
            assert analytics_run_ids is not None, "analytics_run_ids not found in job status"
            assert len(analytics_run_ids) > 0, "No analytics run IDs found in job status"
            assert status.error is None

            # Verify the records in the enrichment DB
            enrichment_db_client = FinderEnrichmentDBAPIClient(
                os.getenv("ENRICHMENT_DB_BASE_URL", "http://localhost:8200"),
                os.getenv("ENRICHMENT_DB_API_KEY"),
            )
            for analytics_run_id in analytics_run_ids:  
                image_analytics_run = enrichment_db_client.get_image_analytics(
                    analytics_run_id
                )
                assert (
                    image_analytics_run is not None
                ), f"Record not found in DB. Status: {image_analytics_run}"
            break
        elif status.status == "failed":
            pytest.fail(f"Job failed with error: {status.error}")
    else:
        pytest.fail("Job did not complete in time")

