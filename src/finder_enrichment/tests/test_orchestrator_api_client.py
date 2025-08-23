"""
Unit tests for the updated OrchestratorAPIClient with synchronous enrichment methods.

Tests the new synchronous enrichment functionality in the API client.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from finder_enrichment.api.orchestrator_api_client import OrchestratorAPIClient
from finder_enrichment.api.models import EnrichmentResult, BatchEnrichmentResult


class TestOrchestratorAPIClientSynchronous:
    """Test cases for the synchronous enrichment methods in OrchestratorAPIClient."""

    def setup_method(self):
        """Set up test client."""
        self.client = OrchestratorAPIClient(
            base_url="http://testserver",
            api_key="test-api-key"
        )

    @patch('finder_enrichment.api.orchestrator_api_client.requests.post')
    def test_enrich_listing_success(self, mock_post):
        """Test successful single listing enrichment."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "listing_id": "test-listing-123",
            "status": "success",
            "enriched_data": {"enriched_listing_id": 456},
            "processing_time_seconds": 2.5,
            "image_count": 3,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        mock_post.return_value = mock_response

        # Execute
        result = self.client.enrich_listing("test-listing-123")

        # Assertions
        assert isinstance(result, EnrichmentResult)
        assert result.enriched_listing_id == "test-listing-123"
        assert result.status == "success"
        assert result.processing_time_seconds == 2.5
        assert result.image_count == 3
        assert result.enriched_data == {"enriched_listing_id": 456}

        # Verify HTTP call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]["url"] == "http://testserver/api/enrich-listing/test-listing-123"
        assert call_args[1]["headers"]["Authorization"] == "Bearer test-api-key"

    @patch('finder_enrichment.api.orchestrator_api_client.requests.post')
    def test_enrich_listing_with_timeout(self, mock_post):
        """Test single listing enrichment with custom timeout."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "listing_id": "test-listing-123",
            "status": "success",
            "processing_time_seconds": 1.0,
            "image_count": 0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        mock_post.return_value = mock_response

        # Execute with custom timeout
        result = self.client.enrich_listing("test-listing-123", timeout_seconds=60.0)

        # Verify timeout was passed to requests.post
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]["timeout"] == 60.0

    @patch('finder_enrichment.api.orchestrator_api_client.requests.post')
    def test_enrich_listing_failed(self, mock_post):
        """Test failed single listing enrichment."""
        # Mock failed response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "listing_id": "failed-listing-123",
            "status": "failed",
            "error_message": "Database connection error",
            "processing_time_seconds": 1.0,
            "image_count": 0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        mock_post.return_value = mock_response

        # Execute
        result = self.client.enrich_listing("failed-listing-123")

        # Assertions
        assert isinstance(result, EnrichmentResult)
        assert result.enriched_listing_id == "failed-listing-123"
        assert result.status == "failed"
        assert result.error_message == "Database connection error"
        assert result.enriched_data is None

    @patch('finder_enrichment.api.orchestrator_api_client.requests.post')
    def test_enrich_listing_timeout_response(self, mock_post):
        """Test listing enrichment when server returns timeout."""
        # Mock timeout response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "listing_id": "timeout-listing-123",
            "status": "timeout",
            "error_message": "Processing exceeded 150 second limit",
            "processing_time_seconds": 150.0,
            "image_count": 0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        mock_post.return_value = mock_response

        # Execute
        result = self.client.enrich_listing("timeout-listing-123")

        # Assertions
        assert isinstance(result, EnrichmentResult)
        assert result.enriched_listing_id == "timeout-listing-123"
        assert result.status == "timeout"
        assert "exceeded 150 second limit" in result.error_message
        assert result.processing_time_seconds == 150.0

    @patch('finder_enrichment.api.orchestrator_api_client.requests.post')
    def test_enrich_listing_http_error(self, mock_post):
        """Test listing enrichment when HTTP request fails."""
        # Mock HTTP error
        from requests.exceptions import HTTPError
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.side_effect = HTTPError("HTTP 500: Internal Server Error", response=mock_response)

        # Execute and expect exception
        with pytest.raises(HTTPError):
            self.client.enrich_listing("error-listing-123")

    @patch('finder_enrichment.api.orchestrator_api_client.requests.post')
    def test_enrich_listings_batch_success(self, mock_post):
        """Test successful batch listing enrichment."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "listing_id": "listing-1",
                    "status": "success",
                    "processing_time_seconds": 1.5,
                    "image_count": 2,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                {
                    "listing_id": "listing-2",
                    "status": "success",
                    "processing_time_seconds": 2.0,
                    "image_count": 3,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            ],
            "total_processed": 2,
            "total_successful": 2,
            "total_failed": 0,
            "processing_time_seconds": 3.5
        }
        mock_post.return_value = mock_response

        # Execute
        result = self.client.enrich_listings_batch(["listing-1", "listing-2"])

        # Assertions
        assert isinstance(result, BatchEnrichmentResult)
        assert result.total_processed == 2
        assert result.total_successful == 2
        assert result.total_failed == 0
        assert result.processing_time_seconds == 3.5
        assert len(result.results) == 2

        # Verify HTTP call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]["url"] == "http://testserver/api/enrich-listings"
        assert call_args[1]["headers"]["Authorization"] == "Bearer test-api-key"
        assert call_args[1]["json"] == {"listing_ids": ["listing-1", "listing-2"]}

    @patch('finder_enrichment.api.orchestrator_api_client.requests.post')
    def test_enrich_listings_batch_mixed_results(self, mock_post):
        """Test batch enrichment with mixed success/failure results."""
        # Mock mixed response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "listing_id": "listing-1",
                    "status": "success",
                    "processing_time_seconds": 1.5,
                    "image_count": 2,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                {
                    "listing_id": "listing-2",
                    "status": "failed",
                    "error_message": "Network error",
                    "processing_time_seconds": 0.5,
                    "image_count": 0,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            ],
            "total_processed": 2,
            "total_successful": 1,
            "total_failed": 1,
            "processing_time_seconds": 2.0
        }
        mock_post.return_value = mock_response

        # Execute
        result = self.client.enrich_listings_batch(["listing-1", "listing-2"])

        # Assertions
        assert isinstance(result, BatchEnrichmentResult)
        assert result.total_processed == 2
        assert result.total_successful == 1
        assert result.total_failed == 1
        assert len(result.results) == 2

        # Check individual results
        successful_result = next(r for r in result.results if r.enriched_listing_id == "listing-1")
        failed_result = next(r for r in result.results if r.enriched_listing_id == "listing-2")

        assert successful_result.status == "success"
        assert failed_result.status == "failed"
        assert failed_result.error_message == "Network error"

    @patch('finder_enrichment.api.orchestrator_api_client.requests.post')
    def test_enrich_listings_batch_with_timeout(self, mock_post):
        """Test batch enrichment with custom timeout."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [],
            "total_processed": 0,
            "total_successful": 0,
            "total_failed": 0,
            "processing_time_seconds": 0.0
        }
        mock_post.return_value = mock_response

        # Execute with custom timeout
        result = self.client.enrich_listings_batch(["listing-1"], timeout_seconds=120.0)

        # Verify timeout was passed to requests.post
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]["timeout"] == 120.0

    @patch('finder_enrichment.api.orchestrator_api_client.requests.post')
    def test_enrich_listings_batch_empty_list(self, mock_post):
        """Test batch enrichment with empty listing list."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [],
            "total_processed": 0,
            "total_successful": 0,
            "total_failed": 0,
            "processing_time_seconds": 0.0
        }
        mock_post.return_value = mock_response

        # Execute with empty list
        result = self.client.enrich_listings_batch([])

        # Should still return a valid result
        assert isinstance(result, BatchEnrichmentResult)
        assert result.total_processed == 0
        assert len(result.results) == 0

    @patch('finder_enrichment.api.orchestrator_api_client.requests.post')
    def test_enrich_listings_batch_http_error(self, mock_post):
        """Test batch enrichment when HTTP request fails."""
        # Mock HTTP error
        from requests.exceptions import HTTPError
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.side_effect = HTTPError("HTTP 400: Bad Request", response=mock_response)

        # Execute and expect exception
        with pytest.raises(HTTPError):
            self.client.enrich_listings_batch(["listing-1", "listing-2"])

    def test_client_without_api_key(self):
        """Test that client raises error when no API key is provided."""
        with pytest.raises(ValueError, match="ORCHESTRATOR_API_KEY is required"):
            client = OrchestratorAPIClient(base_url="http://testserver")
            client.enrich_listing("test-listing-123")

    def test_client_with_empty_api_key(self):
        """Test that client raises error when API key is empty."""
        with pytest.raises(ValueError, match="ORCHESTRATOR_API_KEY is required"):
            client = OrchestratorAPIClient(base_url="http://testserver", api_key="")
            client.enrich_listing("test-listing-123")
