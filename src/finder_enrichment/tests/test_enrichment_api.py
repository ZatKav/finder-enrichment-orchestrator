"""
API endpoint tests for the synchronous enrichment system.

Tests the new enrichment endpoints without requiring external API dependencies.
"""

from typing import List
from finder_enrichment_db_client import FinderEnrichmentDBAPIClient
from finder_enrichment_db_contracts import Image, Listing
from listings_db_api_client import ListingsDBAPIClient
import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from finder_enrichment.api.api_server import app
from finder_enrichment.api.orchestrator_api_client import OrchestratorAPIClient
from finder_enrichment.logger_config import setup_logger
from finder_enrichment.services.synchronous_enrichment_service import (
    EnrichmentResult,
    BatchEnrichmentResult
)
from finder_enrichment.api.models import (
    DescriptionAnalysisResult,
    ImageAnalysisResult,
    BatchImageAnalysisResult
)

listings_client = ListingsDBAPIClient()
finder_enrichment_db_client = FinderEnrichmentDBAPIClient()
logger = setup_logger(__name__)
orchestrator_client = OrchestratorAPIClient()


@pytest.fixture(scope="function")
def first_listing():
    """Get the first available listing ID from the listings database."""
    try:
        # Try to get the first listing
        listings: List[Listing] = listings_client.get_listings(limit=1)

        if listings and len(listings) > 0:
            return listings[0]
        else:
            logger.error("No listings found, db is empty and tests cannot run")
            raise Exception("No listings found, db is empty and tests cannot run")

    except Exception as e:
        logger.error(f"Warning: Could not fetch listing from database: {e}")
        raise Exception(f"Warning: Could not fetch listing from database: {e}")


@pytest.fixture(scope="function")
def first_image(first_listing: Listing):
    """Get the first available image ID from the first listing in the listings database."""
    try:
        images: List[Image] = listings_client.get_images_for_listing(first_listing.id)

        if images and len(images) > 0:
            return images[0]
        else:
            logger.error("No images found, db is empty and tests cannot run")
            raise Exception("No images found, db is empty and tests cannot run")

    except Exception as e:
        logger.error(f"Warning: Could not fetch image from database: {e}")
        raise Exception(f"Warning: Could not fetch image from database: {e}")


def test_enrich_listing_success(first_listing: Listing):
        """Test successful single listing enrichment endpoint."""
        result: EnrichmentResult = orchestrator_client.enrich_listing(first_listing.id)

        assert result.status == "success"
        assert result.listing_id != None
        assert result.processing_time_seconds > 0
        assert result.image_count > 0
        assert result.enriched_data is not None
        
        enriched_listing_id = 
        

        # Verify service was called correctly
        mock_service.enrich_listing.assert_called_once_with("test-listing-123")

    @patch('finder_enrichment.api.routers.enrichment.enrichment_service')
    @patch('finder_enrichment.api.routers.enrichment.get_enrichment_service')
    def test_enrich_listing_no_auth(self, mock_get_service, mock_service):
        """Test enrichment endpoint without authentication."""
        mock_get_service.return_value = mock_service

        # Make request without auth header
        response = self.client.post("/api/enrich-listing/test-listing-123")

        # Should return 401 Unauthorized
        assert response.status_code == 401

    @patch('finder_enrichment.api.routers.enrichment.enrichment_service')
    @patch('finder_enrichment.api.routers.enrichment.get_enrichment_service')
    def test_enrich_listing_service_error(self, mock_get_service, mock_service):
        """Test enrichment endpoint when service raises an error."""
        mock_service.enrich_listing.side_effect = Exception("Service error")
        mock_get_service.return_value = mock_service

        # Make request
        response = self.client.post(
            "/api/enrich-listing/test-listing-123",
            headers={"Authorization": f"Bearer {ORCHESTRATOR_API_KEY}"}
        )

        # Should return 500 Internal Server Error
        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]

    @patch('finder_enrichment.api.routers.enrichment.enrichment_service')
    @patch('finder_enrichment.api.routers.enrichment.get_enrichment_service')
    def test_enrich_listing_failed_result(self, mock_get_service, mock_service):
        """Test enrichment endpoint when enrichment fails."""
        # Mock failed service response
        mock_result = EnrichmentResult(
            listing_id=TEST_LISTING_ID,
            status="failed",
            error_message="Database connection error",
            processing_time_seconds=1.0,
            image_count=0,
            timestamp=datetime.now(timezone.utc)
        )
        mock_service.enrich_listing.return_value = mock_result
        mock_get_service.return_value = mock_service

        # Make request
        response = self.client.post(
            "/api/enrich-listing/test-listing-123",
            headers={"Authorization": f"Bearer {ORCHESTRATOR_API_KEY}"}
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error_message"] == "Database connection error"
        assert data["enriched_data"] is None

    @patch('finder_enrichment.api.routers.enrichment.enrichment_service')
    @patch('finder_enrichment.api.routers.enrichment.get_enrichment_service')
    def test_enrich_listing_timeout_result(self, mock_get_service, mock_service):
        """Test enrichment endpoint when processing times out."""
        # Mock timeout service response
        mock_result = EnrichmentResult(
            listing_id=TEST_LISTING_ID,
            status="timeout",
            error_message="Processing exceeded 150 second limit",
            processing_time_seconds=150.0,
            image_count=0,
            timestamp=datetime.now(timezone.utc)
        )
        mock_service.enrich_listing.return_value = mock_result
        mock_get_service.return_value = mock_service

        # Make request
        response = self.client.post(
            "/api/enrich-listing/test-listing-123",
            headers={"Authorization": f"Bearer {ORCHESTRATOR_API_KEY}"}
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "timeout"
        assert "exceeded 150 second limit" in data["error_message"]


class TestBatchEnrichmentAPI:
    """Test cases for the batch enrichment API endpoints."""

    @patch('finder_enrichment.api.routers.enrichment.enrichment_service')
    @patch('finder_enrichment.api.routers.enrichment.get_enrichment_service')
    def test_enrich_listings_batch_success(self, mock_get_service, mock_service):
        """Test successful batch listing enrichment endpoint."""
        # Mock service response
        mock_results = [
            EnrichmentResult(
                listing_id="listing-1",
                status="success",
                processing_time_seconds=1.5,
                image_count=2,
                timestamp=datetime.now(timezone.utc)
            ),
            EnrichmentResult(
                listing_id="listing-2",
                status="success",
                processing_time_seconds=2.0,
                image_count=3,
                timestamp=datetime.now(timezone.utc)
            )
        ]

        mock_batch_result = BatchEnrichmentResult(
            results=mock_results,
            total_processed=2,
            total_successful=2,
            total_failed=0,
            processing_time_seconds=3.5
        )

        mock_service.enrich_listings_batch.return_value = mock_batch_result
        mock_get_service.return_value = mock_service

        # Make request
        response = self.client.post(
            "/api/enrich-listings",
            json={"listing_ids": ["listing-1", "listing-2"]},
            headers={"Authorization": f"Bearer {ORCHESTRATOR_API_KEY}"}
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["total_processed"] == 2
        assert data["total_successful"] == 2
        assert data["total_failed"] == 0
        assert data["processing_time_seconds"] == 3.5
        assert len(data["results"]) == 2

        # Verify service was called correctly
        mock_service.enrich_listings_batch.assert_called_once_with(["listing-1", "listing-2"])

    @patch('finder_enrichment.api.routers.enrichment.enrichment_service')
    @patch('finder_enrichment.api.routers.enrichment.get_enrichment_service')
    def test_enrich_listings_batch_no_auth(self, mock_get_service, mock_service):
        """Test batch enrichment endpoint without authentication."""
        mock_get_service.return_value = mock_service

        # Make request without auth header
        response = self.client.post(
            "/api/enrich-listings",
            json={"listing_ids": ["listing-1", "listing-2"]}
        )

        # Should return 401 Unauthorized
        assert response.status_code == 401

    @patch('finder_enrichment.api.routers.enrichment.enrichment_service')
    @patch('finder_enrichment.api.routers.enrichment.get_enrichment_service')
    def test_enrich_listings_batch_empty_list(self, mock_get_service, mock_service):
        """Test batch enrichment endpoint with empty listing_ids."""
        mock_get_service.return_value = mock_service

        # Make request with empty list
        response = self.client.post(
            "/api/enrich-listings",
            json={"listing_ids": []},
            headers={"Authorization": f"Bearer {ORCHESTRATOR_API_KEY}"}
        )

        # Should return 400 Bad Request
        assert response.status_code == 400
        assert "No listing IDs provided" in response.json()["detail"]

    @patch('finder_enrichment.api.routers.enrichment.enrichment_service')
    @patch('finder_enrichment.api.routers.enrichment.get_enrichment_service')
    def test_enrich_listings_batch_too_many_listings(self, mock_get_service, mock_service):
        """Test batch enrichment endpoint with too many listings."""
        mock_get_service.return_value = mock_service

        # Make request with too many listings
        listing_ids = [f"listing-{i}" for i in range(60)]  # More than the 50 limit
        response = self.client.post(
            "/api/enrich-listings",
            json={"listing_ids": listing_ids},
            headers={"Authorization": f"Bearer {ORCHESTRATOR_API_KEY}"}
        )

        # Should return 400 Bad Request
        assert response.status_code == 400
        assert "Maximum 50 listings per batch request" in response.json()["detail"]

    @patch('finder_enrichment.api.routers.enrichment.enrichment_service')
    @patch('finder_enrichment.api.routers.enrichment.get_enrichment_service')
    def test_enrich_listings_batch_mixed_results(self, mock_get_service, mock_service):
        """Test batch enrichment endpoint with mixed success/failure results."""
        # Mock service response with mixed results
        mock_results = [
            EnrichmentResult(
                listing_id="listing-1",
                status="success",
                processing_time_seconds=1.5,
                image_count=2,
                timestamp=datetime.now(timezone.utc)
            ),
            EnrichmentResult(
                listing_id="listing-2",
                status="failed",
                error_message="Network error",
                processing_time_seconds=0.5,
                image_count=0,
                timestamp=datetime.now(timezone.utc)
            )
        ]

        mock_batch_result = BatchEnrichmentResult(
            results=mock_results,
            total_processed=2,
            total_successful=1,
            total_failed=1,
            processing_time_seconds=2.0
        )

        mock_service.enrich_listings_batch.return_value = mock_batch_result
        mock_get_service.return_value = mock_service

        # Make request
        response = self.client.post(
            "/api/enrich-listings",
            json={"listing_ids": ["listing-1", "listing-2"]},
            headers={"Authorization": f"Bearer {ORCHESTRATOR_API_KEY}"}
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["total_processed"] == 2
        assert data["total_successful"] == 1
        assert data["total_failed"] == 1
        assert len(data["results"]) == 2

        # Check individual results
        results = data["results"]
        successful_result = next(r for r in results if r["listing_id"] == "listing-1")
        failed_result = next(r for r in results if r["listing_id"] == "listing-2")

        assert successful_result["status"] == "success"
        assert failed_result["status"] == "failed"
        assert failed_result["error_message"] == "Network error"


class TestEnrichmentHealthAPI:
    """Test cases for the enrichment health API endpoints."""

    @patch('finder_enrichment.api.routers.enrichment.enrichment_service')
    def test_enrichment_health_check_healthy(self, mock_service):
        """Test enrichment health check when service is healthy."""
        # Mock healthy service
        mock_service.listings_db_client = Mock()
        mock_service.description_analyser_agent = Mock()
        mock_service.image_analyser_client = Mock()
        mock_service.enriched_db_client = Mock()

        with patch('finder_enrichment.api.routers.enrichment.enrichment_service', mock_service):
            response = self.client.get("/api/enrichment/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "enrichment"
        assert data["service_clients"]["listings_db_client"] is True
        assert data["service_clients"]["description_analyser_agent"] is True
        assert data["service_clients"]["image_analyser_client"] is True
        assert data["service_clients"]["enriched_db_client"] is True

    @patch('finder_enrichment.api.routers.enrichment.enrichment_service')
    def test_enrichment_health_check_unhealthy(self, mock_service):
        """Test enrichment health check when service is unhealthy."""
        # Mock unhealthy service (no service clients configured)
        mock_service.listings_db_client = None
        mock_service.description_analyser_agent = None
        mock_service.image_analyser_client = None
        mock_service.enriched_db_client = None

        with patch('finder_enrichment.api.routers.enrichment.enrichment_service', mock_service):
            response = self.client.get("/api/enrichment/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["service"] == "enrichment"
        assert data["service_clients"]["listings_db_client"] is False
        assert data["service_clients"]["description_analyser_agent"] is False
        assert data["service_clients"]["image_analyser_client"] is False
        assert data["service_clients"]["enriched_db_client"] is False

    @patch('finder_enrichment.api.routers.enrichment.enrichment_service')
    def test_enrichment_health_check_no_service(self, mock_service):
        """Test enrichment health check when no service is configured."""
        # Mock no service at all
        mock_service = None

        with patch('finder_enrichment.api.routers.enrichment.enrichment_service', mock_service):
            response = self.client.get("/api/enrichment/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["service"] == "enrichment"
        assert "Enrichment service not initialized" in data["error"]


class TestDescriptionAnalysisAPI:
    """Test cases for the description analysis API endpoints."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)

    @patch('finder_enrichment.api.routers.enrich._analyze_description_sync')
    @patch('finder_enrichment.api.routers.enrich.require_api_key')
    def test_enrich_description_success(self, mock_auth, mock_analyze):
        """Test successful description analysis endpoint."""
        # Mock authentication
        mock_auth.return_value = None

        # Mock the analyzer response
        mock_result = DescriptionAnalysisResult(
            enriched_listing_id=TEST_LISTING_ID,
            status="success",
            analytics_run_id=789,
            processing_time_seconds=1.5,
            timestamp=datetime.now(timezone.utc)
        )
        mock_analyze.return_value = mock_result

        # Make request
        response = self.client.post(
            f"/api/enrich/description/{TEST_LISTING_ID}",
            headers={"Authorization": f"Bearer {ORCHESTRATOR_API_KEY}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["listing_id"] == TEST_LISTING_ID
        assert data["status"] == "success"
        assert data["analytics_run_id"] == 789
        assert data["processing_time_seconds"] == 1.5

        # Verify the mock was called with correct parameters
        mock_analyze.assert_called_once_with(TEST_LISTING_ID)

    @patch('finder_enrichment.api.routers.enrich._analyze_description_sync')
    @patch('finder_enrichment.api.routers.enrich.require_api_key')
    def test_enrich_description_failure(self, mock_auth, mock_analyze):
        """Test description analysis endpoint with failure."""
        # Mock authentication
        mock_auth.return_value = None

        # Mock the analyzer response
        mock_result = DescriptionAnalysisResult(
            enriched_listing_id=TEST_LISTING_ID,
            status="failed",
            error_message="Analysis failed",
            processing_time_seconds=0.5,
            timestamp=datetime.now(timezone.utc)
        )
        mock_analyze.return_value = mock_result

        # Make request
        response = self.client.post(
            f"/api/enrich/description/{TEST_LISTING_ID}",
            headers={"Authorization": f"Bearer {ORCHESTRATOR_API_KEY}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["listing_id"] == TEST_LISTING_ID
        assert data["status"] == "failed"
        assert data["error_message"] == "Analysis failed"

    def test_enrich_description_missing_auth(self):
        """Test description analysis endpoint without authentication."""
        response = self.client.post(f"/api/enrich/description/{TEST_LISTING_ID}")

        assert response.status_code == 401


class TestImageAnalysisAPI:
    """Test cases for the image analysis API endpoints."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)

    @patch('finder_enrichment.api.routers.enrich._analyze_images_listing_sync')
    @patch('finder_enrichment.api.routers.enrich.require_api_key')
    def test_enrich_images_listing_success(self, mock_auth, mock_analyze):
        """Test successful batch image analysis for listing endpoint."""
        # Mock authentication
        mock_auth.return_value = None

        # Mock the analyzer response
        mock_result = BatchImageAnalysisResult(
            listing_id=TEST_LISTING_ID,
            status="success",
            analytics_run_ids=[101, 102, 103],
            processing_time_seconds=8.5,
            image_count=3,
            timestamp=datetime.now(timezone.utc)
        )
        mock_analyze.return_value = mock_result

        # Make request
        response = self.client.post(
            f"/api/enrich/listing/images/{TEST_LISTING_ID}",
            headers={"Authorization": f"Bearer {ORCHESTRATOR_API_KEY}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["listing_id"] == TEST_LISTING_ID
        assert data["status"] == "success"
        assert data["analytics_run_ids"] == [101, 102, 103]
        assert data["image_count"] == 3

        # Verify the mock was called with correct parameters
        mock_analyze.assert_called_once_with(TEST_LISTING_ID)

    @patch('finder_enrichment.api.routers.enrich._analyze_single_image_sync')
    @patch('finder_enrichment.api.routers.enrich.require_api_key')
    def test_enrich_single_image_success(self, mock_auth, mock_analyze):
        """Test successful single image analysis endpoint."""
        # Mock authentication
        mock_auth.return_value = None

        # Mock the analyzer response
        mock_result = ImageAnalysisResult(
            original_image_id=TEST_IMAGE_ID,
            status="success",
            analytics_run_id=202,
            processing_time_seconds=3.2,
            timestamp=datetime.now(timezone.utc)
        )
        mock_analyze.return_value = mock_result

        # Make request
        response = self.client.post(
            f"/api/enrich/image/{TEST_IMAGE_ID}",
            headers={"Authorization": f"Bearer {ORCHESTRATOR_API_KEY}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["image_id"] == TEST_IMAGE_ID
        assert data["status"] == "success"
        assert data["analytics_run_id"] == 202

        # Verify the mock was called with correct parameters
        mock_analyze.assert_called_once_with(TEST_IMAGE_ID)

    @patch('finder_enrichment.api.routers.enrich._analyze_images_listing_sync')
    @patch('finder_enrichment.api.routers.enrich.require_api_key')
    def test_enrich_images_listing_failure(self, mock_auth, mock_analyze):
        """Test batch image analysis endpoint with failure."""
        # Mock authentication
        mock_auth.return_value = None

        # Mock the analyzer response
        mock_result = BatchImageAnalysisResult(
            listing_id=TEST_LISTING_ID,
            status="failed",
            error_message="No images found",
            processing_time_seconds=1.0,
            image_count=0,
            timestamp=datetime.now(timezone.utc)
        )
        mock_analyze.return_value = mock_result

        # Make request
        response = self.client.post(
            f"/api/enrich/listing/images/{TEST_LISTING_ID}",
            headers={"Authorization": f"Bearer {ORCHESTRATOR_API_KEY}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["listing_id"] == TEST_LISTING_ID
        assert data["status"] == "failed"
        assert data["error_message"] == "No images found"
        assert data["image_count"] == 0

    def test_enrich_images_missing_auth(self):
        """Test image analysis endpoints without authentication."""
        # Test listing endpoint
        response = self.client.post(f"/api/enrich/listing/images/{TEST_LISTING_ID}")
        assert response.status_code == 401

        # Test single image endpoint
        response = self.client.post(f"/api/enrich/image/{TEST_IMAGE_ID}")
        assert response.status_code == 401


class TestEnrichDescriptionIntegration:
    """Integration tests for the enrich description endpoint."""

    def setup_method(self):
        """Set up test environment."""
        self.client = TestClient(app)

    @patch('finder_enrichment.api.routers.enrich.DescriptionAnalyser')
    @patch('finder_enrichment.api.routers.enrich.require_api_key')
    def test_enrich_description_integration(self, mock_auth, mock_analyser_class):
        """Test the full integration of description enrichment."""
        # Mock authentication
        mock_auth.return_value = None

        # Create mock description analyser
        mock_analyser = Mock()
        mock_analyser_class.return_value = mock_analyser

        # Mock the analytics run result
        mock_analytics_run = Mock()
        mock_analytics_run.id = 12345
        mock_analyser.run_single_listing.return_value = mock_analytics_run

        # Make request
        response = self.client.post(
            f"/api/enrich/description/{TEST_LISTING_ID}",
            headers={"Authorization": f"Bearer {ORCHESTRATOR_API_KEY}"}
        )

        # Verify response structure
        assert response.status_code == 200
        data = response.json()
        assert data["listing_id"] == TEST_LISTING_ID
        assert data["status"] in ["success", "failed"]  # Can be either depending on real service
        assert data["processing_time_seconds"] >= 0
        assert "timestamp" in data

        # If successful, verify analytics_run_id is present
        if data["status"] == "success":
            assert data["analytics_run_id"] is not None
            assert isinstance(data["analytics_run_id"], int)

        # Verify the analyser was called correctly
        mock_analyser_class.assert_called_once()
        mock_analyser.run_single_listing.assert_called_once_with(int(TEST_LISTING_ID))

    @patch('finder_enrichment.api.routers.enrich.DescriptionAnalyser')
    @patch('finder_enrichment.api.routers.enrich.require_api_key')
    def test_enrich_description_integration_failure(self, mock_auth, mock_analyser_class):
        """Test description enrichment when analysis fails."""
        # Mock authentication
        mock_auth.return_value = None

        # Create mock description analyser that returns None (failure)
        mock_analyser = Mock()
        mock_analyser_class.return_value = mock_analyser
        mock_analyser.run_single_listing.return_value = None

        # Make request
        response = self.client.post(
            "/api/enrich/description/123",
            headers={"Authorization": f"Bearer {ORCHESTRATOR_API_KEY}"}
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["listing_id"] == "123"
        assert data["status"] == "failed"
        assert "Description analysis failed" in data["error_message"]
        assert data["processing_time_seconds"] > 0


class TestEnrichListingImagesIntegration:
    """Integration tests for the enrich listing images endpoint."""

    def setup_method(self):
        """Set up test environment."""
        self.client = TestClient(app)

    @patch('finder_enrichment.api.routers.enrich.ImageAnalyser')
    @patch('finder_enrichment.api.routers.enrich.require_api_key')
    def test_enrich_listing_images_integration(self, mock_auth, mock_analyser_class):
        """Test the full integration of listing image enrichment."""
        # Mock authentication
        mock_auth.return_value = None

        # Create mock image analyser
        mock_analyser = Mock()
        mock_analyser_class.return_value = mock_analyser

        # Mock the analytics runs result
        mock_analytics_run1 = Mock()
        mock_analytics_run1.id = 111
        mock_analytics_run2 = Mock()
        mock_analytics_run2.id = 222
        mock_analytics_run3 = Mock()
        mock_analytics_run3.id = 333

        mock_analyser.run_single_listing.return_value = [
            mock_analytics_run1,
            mock_analytics_run2,
            mock_analytics_run3
        ]

        # Make request
        response = self.client.post(
            f"/api/enrich/listing/images/{TEST_LISTING_ID}",
            headers={"Authorization": f"Bearer {ORCHESTRATOR_API_KEY}"}
        )

        # Verify response structure
        assert response.status_code == 200
        data = response.json()
        assert data["listing_id"] == TEST_LISTING_ID
        assert data["status"] in ["success", "failed"]  # Can be either depending on real service
        assert data["image_count"] >= 0
        assert data["processing_time_seconds"] >= 0
        assert "timestamp" in data

        # If successful, verify analytics_run_ids are present
        if data["status"] == "success":
            assert data["analytics_run_ids"] is not None
            assert isinstance(data["analytics_run_ids"], list)
            assert len(data["analytics_run_ids"]) == data["image_count"]

        # Verify the analyser was called correctly
        mock_analyser_class.assert_called_once()
        mock_analyser.run_single_listing.assert_called_once_with(int(TEST_LISTING_ID))

    @patch('finder_enrichment.api.routers.enrich.ImageAnalyser')
    @patch('finder_enrichment.api.routers.enrich.require_api_key')
    def test_enrich_listing_images_integration_empty(self, mock_auth, mock_analyser_class):
        """Test listing image enrichment when no images are found."""
        # Mock authentication
        mock_auth.return_value = None

        # Create mock image analyser that returns empty list
        mock_analyser = Mock()
        mock_analyser_class.return_value = mock_analyser
        mock_analyser.run_single_listing.return_value = []

        # Make request
        response = self.client.post(
            "/api/enrich/listing/images/456",
            headers={"Authorization": f"Bearer {ORCHESTRATOR_API_KEY}"}
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["listing_id"] == "456"
        assert data["status"] == "failed"
        assert "Image analysis failed" in data["error_message"]
        assert data["image_count"] == 0


class TestEnrichImageIntegration:
    """Integration tests for the enrich single image endpoint."""

    def setup_method(self):
        """Set up test environment."""
        self.client = TestClient(app)

    @patch('finder_enrichment.api.routers.enrich.ImageAnalyser')
    @patch('finder_enrichment.api.routers.enrich.require_api_key')
    def test_enrich_single_image_integration(self, mock_auth, mock_analyser_class):
        """Test the full integration of single image enrichment."""
        # Mock authentication
        mock_auth.return_value = None

        # Create mock image analyser
        mock_analyser = Mock()
        mock_analyser_class.return_value = mock_analyser

        # Mock the analytics run result
        mock_analytics_run = Mock()
        mock_analytics_run.id = 777
        mock_analyser.run_single_image.return_value = mock_analytics_run

        # Make request
        response = self.client.post(
            f"/api/enrich/image/{TEST_IMAGE_ID}",
            headers={"Authorization": f"Bearer {ORCHESTRATOR_API_KEY}"}
        )

        # Verify response structure
        assert response.status_code == 200
        data = response.json()
        assert data["image_id"] == TEST_IMAGE_ID
        assert data["status"] in ["success", "failed"]  # Can be either depending on real service
        assert data["processing_time_seconds"] >= 0
        assert "timestamp" in data

        # If successful, verify analytics_run_id is present
        if data["status"] == "success":
            assert data["analytics_run_id"] is not None
            assert isinstance(data["analytics_run_id"], int)

        # Verify the analyser was called correctly
        mock_analyser_class.assert_called_once()
        mock_analyser.run_single_image.assert_called_once_with(int(TEST_IMAGE_ID))

    @patch('finder_enrichment.api.routers.enrich.ImageAnalyser')
    @patch('finder_enrichment.api.routers.enrich.require_api_key')
    def test_enrich_single_image_integration_failure(self, mock_auth, mock_analyser_class):
        """Test single image enrichment when analysis fails."""
        # Mock authentication
        mock_auth.return_value = None

        # Create mock image analyser that returns None (failure)
        mock_analyser = Mock()
        mock_analyser_class.return_value = mock_analyser
        mock_analyser.run_single_image.return_value = None

        # Make request
        response = self.client.post(
            "/api/enrich/image/789",
            headers={"Authorization": f"Bearer {ORCHESTRATOR_API_KEY}"}
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["image_id"] == "789"
        assert data["status"] == "failed"
        assert "Image analysis failed" in data["error_message"]
        assert data["processing_time_seconds"] > 0
