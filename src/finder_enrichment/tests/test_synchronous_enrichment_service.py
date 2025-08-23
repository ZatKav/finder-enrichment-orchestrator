"""
Unit tests for SynchronousEnrichmentService.

Tests the core synchronous enrichment functionality without external dependencies.
"""

import json
import itertools
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone

from finder_enrichment.services.synchronous_enrichment_service import (
    SynchronousEnrichmentService,
    EnrichmentResult,
    BatchEnrichmentResult
)


class TestEnrichmentResult:
    """Test cases for the EnrichmentResult model."""

    def test_enrichment_result_creation(self):
        """Test creating an EnrichmentResult with all fields."""
        timestamp = datetime.now(timezone.utc)

        result = EnrichmentResult(
            listing_id="test-listing-123",
            status="success",
            enriched_data={"enriched_listing_id": 456},
            processing_time_seconds=2.5,
            image_count=3,
            timestamp=timestamp
        )

        assert result.listing_id == "test-listing-123"
        assert result.status == "success"
        assert result.enriched_data == {"enriched_listing_id": 456}
        assert result.processing_time_seconds == 2.5
        assert result.image_count == 3
        assert result.timestamp == timestamp
        assert result.error_message is None

    def test_enrichment_result_with_error(self):
        """Test creating an EnrichmentResult with error status."""
        result = EnrichmentResult(
            listing_id="failed-listing-123",
            status="failed",
            error_message="Network timeout",
            processing_time_seconds=1.0,
            image_count=0
        )

        assert result.listing_id == "failed-listing-123"
        assert result.status == "failed"
        assert result.error_message == "Network timeout"
        assert result.enriched_data is None
        assert result.processing_time_seconds == 1.0

    def test_enrichment_result_timeout(self):
        """Test creating an EnrichmentResult with timeout status."""
        result = EnrichmentResult(
            listing_id="timeout-listing-123",
            status="timeout",
            error_message="Processing exceeded 150 second limit",
            processing_time_seconds=150.0,
            image_count=5
        )

        assert result.status == "timeout"
        assert "exceeded 150 second limit" in result.error_message


class TestBatchEnrichmentResult:
    """Test cases for the BatchEnrichmentResult model."""

    def test_batch_enrichment_result_creation(self):
        """Test creating a BatchEnrichmentResult."""
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

        assert batch_result.results == results
        assert batch_result.total_processed == 2
        assert batch_result.total_successful == 1
        assert batch_result.total_failed == 1
        assert batch_result.processing_time_seconds == 2.0


class TestSynchronousEnrichmentService:
    """Test cases for the SynchronousEnrichmentService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = SynchronousEnrichmentService()

        # Mock service clients
        self.mock_listings_db = Mock()
        self.mock_description_analyser = Mock()
        self.mock_image_analyser = Mock()
        self.mock_enriched_db = Mock()

        self.service.set_service_clients(
            listings_db_client=self.mock_listings_db,
            description_analyser_client=self.mock_description_analyser,
            image_analyser_client=self.mock_image_analyser,
            enriched_db_client=self.mock_enriched_db
        )

    def test_service_initialization(self):
        """Test service initialization."""
        service = SynchronousEnrichmentService()
        assert service.listings_db_client is None
        assert service.description_analyser_agent is None
        assert service.image_analyser_client is None
        assert service.enriched_db_client is None

    def test_set_service_clients(self):
        """Test setting service clients."""
        service = SynchronousEnrichmentService()

        mock_client = Mock()
        service.set_service_clients(
            listings_db_client=mock_client,
            description_analyser_client=mock_client,
            image_analyser_client=mock_client,
            enriched_db_client=mock_client
        )

        assert service.listings_db_client is mock_client
        assert service.description_analyser_agent is mock_client
        assert service.image_analyser_client is mock_client
        assert service.enriched_db_client is mock_client

    def test_enrich_description_success(self):
        """Test successful description enrichment."""
        mock_response = Mock()
        mock_response.response = {"analysis": "Great property with modern amenities"}
        self.mock_description_analyser.run.return_value = mock_response

        result = self.service.enrich_description("Beautiful house with garden")

        assert result == {"analysis": "Great property with modern amenities"}
        self.mock_description_analyser.run.assert_called_once_with("Beautiful house with garden")

    def test_enrich_description_empty_input(self):
        """Test description enrichment with empty input."""
        mock_response = Mock()
        mock_response.response = {"analysis": "No description provided"}
        self.mock_description_analyser.run.return_value = mock_response

        result = self.service.enrich_description("")

        assert result == {"analysis": "No description provided"}

    def test_enrich_description_no_agent(self):
        """Test description enrichment without agent configured."""
        service = SynchronousEnrichmentService()  # No agent configured

        with pytest.raises(RuntimeError, match="Description analyser agent not configured"):
            service.enrich_description("Test description")

    @patch('time.time')
    def test_enrich_listing_success(self, mock_time):
        """Test successful single listing enrichment."""
        # Mock time progression - use cycle to handle multiple calls
        mock_time.side_effect = itertools.cycle([1000.0, 1002.5])

        # Mock original listing with required string fields
        mock_listing = Mock()
        mock_listing.id = 123  # Integer ID as expected by database models
        mock_listing.description = "Beautiful house"
        mock_listing.images = []  # No images for simplicity
        mock_listing.estate_agent = Mock()
        mock_listing.location = None
        mock_listing.title = "Test Property"
        mock_listing.external_url = "https://example.com/listing/123"  # Required string field

        self.mock_listings_db.get_listing.return_value = mock_listing

        # Mock description analysis with proper response structure
        mock_desc_response = Mock()
        mock_desc_response.response = {"analysis": "Great property"}
        mock_desc_response.model = "gemini-1.5-flash"  # String for model field

        # Mock prompt with ID
        mock_prompt = Mock()
        mock_prompt.id = 123
        mock_desc_response.prompt = mock_prompt

        self.mock_description_analyser.run.return_value = mock_desc_response

        with patch('finder_enrichment.services.synchronous_enrichment_service.get_or_create_estate_agent') as mock_get_agent:
            mock_get_agent.return_value = 456

            # Mock enriched listing
            mock_enriched_listing = Mock()
            mock_enriched_listing.id = 999
            self.mock_enriched_db.create_listing.return_value = mock_enriched_listing

            # Execute
            result = self.service.enrich_listing(123)

            # Assertions
            assert result.listing_id == 123
            assert result.status == "success"
            assert result.processing_time_seconds >= 0  # Processing time should be non-negative
            assert result.image_count == 0
            assert "enriched_listing_id" in result.enriched_data

    def test_enrich_listing_missing_listing(self):
        """Test enrichment when listing is not found."""
        self.mock_listings_db.get_listing.side_effect = Exception("Listing not found")

        result = self.service.enrich_listing("missing-listing-123")

        assert result.listing_id == "missing-listing-123"
        assert result.status == "failed"
        assert "Listing not found" in result.error_message

    def test_enrich_listing_no_agents_configured(self):
        """Test enrichment when no agents are configured."""
        service = SynchronousEnrichmentService()  # No agents configured

        # Should return a failed result instead of raising exception
        result = service.enrich_listing("test-listing-123")

        assert result.listing_id == "test-listing-123"
        assert result.status == "failed"
        assert "All service clients must be configured" in result.error_message

    @patch('time.time')
    def test_enrich_listings_batch_success(self, mock_time):
        """Test successful batch listing enrichment."""
        # Mock time progression - use cycle to handle multiple calls
        mock_time.side_effect = itertools.cycle([1000.0, 1003.0])

        # Mock listings with required string fields
        mock_listing1 = Mock()
        mock_listing1.id = 1  # Integer ID
        mock_listing1.description = "House 1"
        mock_listing1.images = []
        mock_listing1.estate_agent = Mock()
        mock_listing1.location = None
        mock_listing1.title = "House 1"
        mock_listing1.external_url = "https://example.com/listing/1"

        mock_listing2 = Mock()
        mock_listing2.id = 2  # Integer ID
        mock_listing2.description = "House 2"
        mock_listing2.images = []
        mock_listing2.estate_agent = Mock()
        mock_listing2.location = None
        mock_listing2.title = "House 2"
        mock_listing2.external_url = "https://example.com/listing/2"

        # Mock database calls
        def get_listing_side_effect(listing_id):
            if listing_id == "listing-1":
                return mock_listing1
            elif listing_id == "listing-2":
                return mock_listing2
            else:
                raise Exception("Listing not found")

        self.mock_listings_db.get_listing.side_effect = get_listing_side_effect

        # Mock description analysis with proper response structure
        mock_desc_response = Mock()
        mock_desc_response.response = {"analysis": "Good property"}
        mock_desc_response.model = "gemini-1.5-flash"

        mock_prompt = Mock()
        mock_prompt.id = 123
        mock_desc_response.prompt = mock_prompt

        self.mock_description_analyser.run.return_value = mock_desc_response

        with patch('finder_enrichment.services.synchronous_enrichment_service.get_or_create_estate_agent') as mock_get_agent:
            mock_get_agent.return_value = 456

            # Mock enriched listings
            mock_enriched_listing = Mock()
            mock_enriched_listing.id = 999
            self.mock_enriched_db.create_listing.return_value = mock_enriched_listing

            # Execute
            result = self.service.enrich_listings_batch(["listing-1", "listing-2"])

            # Assertions
            assert result.total_processed == 2
            assert result.total_successful == 2
            assert result.total_failed == 0
            assert result.processing_time_seconds >= 0  # Processing time should be non-negative
            assert len(result.results) == 2
            assert all(r.status == "success" for r in result.results)

    def test_enrich_listings_batch_with_failures(self):
        """Test batch enrichment with some failures."""
        # Mock first listing success, second listing failure
        mock_listing1 = Mock()
        mock_listing1.id = 1  # Integer ID
        mock_listing1.description = "House 1"
        mock_listing1.images = []
        mock_listing1.estate_agent = Mock()
        mock_listing1.location = None
        mock_listing1.title = "House 1"
        mock_listing1.external_url = "https://example.com/listing/1"

        def get_listing_side_effect(listing_id):
            if listing_id == "listing-1":
                return mock_listing1
            elif listing_id == "listing-2":
                raise Exception("Database connection error")
            else:
                raise Exception("Listing not found")

        self.mock_listings_db.get_listing.side_effect = get_listing_side_effect

        # Mock description analysis for successful listing
        mock_desc_response = Mock()
        mock_desc_response.response = {"analysis": "Good property"}
        mock_desc_response.model = "gemini-1.5-flash"

        mock_prompt = Mock()
        mock_prompt.id = 123
        mock_desc_response.prompt = mock_prompt

        self.mock_description_analyser.run.return_value = mock_desc_response

        with patch('finder_enrichment.services.synchronous_enrichment_service.get_or_create_estate_agent') as mock_get_agent:
            mock_get_agent.return_value = 456

            # Mock enriched listing
            mock_enriched_listing = Mock()
            mock_enriched_listing.id = 999
            self.mock_enriched_db.create_listing.return_value = mock_enriched_listing

            # Execute
            result = self.service.enrich_listings_batch(["listing-1", "listing-2"])

            # Assertions
            assert result.total_processed == 2
            assert result.total_successful == 1
            assert result.total_failed == 1
            assert len(result.results) == 2

            successful_result = next(r for r in result.results if r.listing_id == "listing-1")
            failed_result = next(r for r in result.results if r.listing_id == "listing-2")

            assert successful_result.status == "success"
            assert failed_result.status == "failed"
            assert "Database connection error" in failed_result.error_message

    def test_enrich_images_empty_list(self):
        """Test image enrichment with empty image list."""
        result = self.service.enrich_images([])
        assert result is not None  # Should handle empty list gracefully

    def test_enrich_images_no_client(self):
        """Test image enrichment without image analyser client."""
        service = SynchronousEnrichmentService()  # No client configured

        # Should handle gracefully by returning empty list instead of raising exception
        result = service.enrich_images("123")
        assert result == []  # Should return empty list when no image analyser is configured
