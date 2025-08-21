from unittest.mock import MagicMock, patch, Mock
import json
import pytest

from finder_enrichment.orchestrator.base_orchestrator import BaseEnrichmentOrchestrator
from finder_enrichment.agentic_services.model_response import ModelResponse
from listings_db_contracts.schemas import Listing, EstateAgent, Address, ApiResponse


@pytest.fixture
def mock_db_client():
    """Fixture for a mock FinderEnrichmentDBAPIClient."""
    client = MagicMock()
    # Mock the various client methods to return mock objects
    client.create_orchestration_set.return_value = MagicMock(id=1)
    client.get_estate_agents.return_value = []
    client.create_estate_agent.return_value = MagicMock(id=10, name="Test Agent")
    client.create_listing.return_value = MagicMock(id=100)
    client.create_orchestration_run.return_value = MagicMock(id=1000)
    return client

@pytest.fixture
def mock_listings_db_client():
    """Fixture for a mock listings database client."""
    client = MagicMock()
    
    # Create a mock listing that conforms to the expected structure
    mock_address = Address(
        address_line_1="123 Test St",
        address_line_2="Testville",
        county="Testshire",
        postcode="TE1 5ST",
        country="Testland"
    )
    mock_agent = EstateAgent(
        name="Test Agent",
        website="http://testagent.com",
        phone="123-456-7890",
        email="contact@testagent.com",
        address=mock_address
    )
    mock_listing_data = Listing(
        id="prop123",
        title="A beautiful test property.",
        description="A beautiful test property.",
        price="500000",
        property_type="House",
        bedrooms=3,
        bathrooms=2,
        reception_rooms=1,
        first_seen="2024-01-01T12:00:00Z",
        last_updated="2024-01-01T12:00:00Z",
        is_active=True,
        location=None,
        estate_agent=mock_agent,
        images=[],
        created_at="2024-01-01T12:00:00Z",
        updated_at="2024-01-01T12:00:00Z",
        external_url="http://test.com/prop123",
        agency_url="http://testagent.com/prop123",
    )
    mock_api_response = ApiResponse(
        status_code=200,
        results=[mock_listing_data]
    )
    
    client.get_listing.return_value = mock_api_response
    return client

@pytest.fixture
def mock_description_analyser():
    """Fixture for a mock description analyser agent."""
    agent = MagicMock()
    analysis = {"sentiment": "positive", "tags": ["test", "property"]}
    agent.analyse_description.return_value = ModelResponse(
        agent_version="1.0",
        model="test_model",
        request="test_request",
        response=json.dumps(analysis),
        prompt="test_prompt",
        processing_time=0.1,
        token_count_estimate=10
    )
    return agent

@pytest.fixture
def base_orchestrator(mock_db_client, mock_listings_db_client, mock_description_analyser):
    """Fixture for a BaseEnrichmentOrchestrator with mocked dependencies."""
    orchestrator = BaseEnrichmentOrchestrator()
    orchestrator.set_service_clients(
        listings_db_client=mock_listings_db_client,
        enriched_db_client=mock_db_client,
        description_analyser_client=mock_description_analyser
    )
    # The base orchestrator creates this during its run, so we mock it here
    orchestrator.orchestration_set_id = 1 
    return orchestrator

class TestBaseEnrichmentOrchestrator:
    def test_initialization(self):
        """Test orchestrator initialization."""
        orchestrator = BaseEnrichmentOrchestrator(max_workers=10, enable_parallel_processing=False)
        assert orchestrator.max_workers == 10
        assert not orchestrator.enable_parallel_processing
        assert orchestrator.listings_db_client is None
        assert orchestrator.processed_count == 0
        assert orchestrator.error_count == 0

    def test_set_service_clients(self):
        """Test setting service clients."""
        orchestrator = BaseEnrichmentOrchestrator()
        mock_client = MagicMock()
        orchestrator.set_service_clients(description_analyser_client=mock_client)
        assert orchestrator.description_analyser_agent == mock_client

    def test_get_stats(self, base_orchestrator):
        """Test getting orchestrator statistics."""
        base_orchestrator.processed_count = 5
        base_orchestrator.error_count = 1
        stats = base_orchestrator.get_stats()
        assert isinstance(stats, dict)
        assert stats["processed_count"] == 5
        assert stats["error_count"] == 1
        assert "success_rate" in stats

    def test_get_or_create_estate_agent_existing(self, base_orchestrator):
        """Test retrieving an existing estate agent."""
        mock_agent_data = EstateAgent(id=42, name="Existing Agent")
        base_orchestrator.enriched_db_client.get_estate_agents.return_value = [mock_agent_data]
        
        original_agent = EstateAgent(name="Existing Agent")
        agent_id = base_orchestrator._get_or_create_estate_agent(original_agent)
        
        assert agent_id == 42
        base_orchestrator.enriched_db_client.create_estate_agent.assert_not_called()

    def test_get_or_create_estate_agent_new(self, base_orchestrator):
        """Test creating a new estate agent if it doesn't exist."""
        original_agent = EstateAgent(name="New Agent", address=None, website=None, phone=None, email=None)
        
        agent_id = base_orchestrator._get_or_create_estate_agent(original_agent)
        
        assert agent_id == 10 # From the mock_db_client fixture
        base_orchestrator.enriched_db_client.create_estate_agent.assert_called_once()
        # You could add more assertions here to check the payload sent to create_estate_agent

    def test_handle_description_analysis(self, base_orchestrator, mock_listings_db_client):
        """Test the description analysis handler."""
        listing_response = mock_listings_db_client.get_listing.return_value
        
        with patch.object(base_orchestrator.description_analyser_agent, 'run') as mock_run:
            analysis = {"sentiment": "positive", "tags": ["test", "property"]}
            mock_run.return_value = ModelResponse(
                agent_version="1.0",
                model="test_model",
                request="test_request",
                response=json.dumps(analysis),
                prompt="test_prompt",
                processing_time=0.1,
                token_count_estimate=10
            )
            model_response = base_orchestrator._handle_description_analysis(listing_response)
        
        assert isinstance(model_response, ModelResponse)

    @patch('finder_enrichment.base_orchestrator.BaseEnrichmentOrchestrator._build_enriched_listing', new=Mock())
    @patch('finder_enrichment.base_orchestrator.BaseEnrichmentOrchestrator._build_orchestration_run', new=Mock())
    def test_process_single_listing_success(self, base_orchestrator, mock_db_client):
        """Test the full successful processing of a single listing."""
        result = base_orchestrator.process_single_listing("prop123")

        assert result is True
        assert base_orchestrator.processed_count == 1
        assert base_orchestrator.error_count == 0
        
        # Verify that the key methods were called
        base_orchestrator.listings_db_client.get_listing.assert_called_once_with(listing_id="prop123")
        base_orchestrator.description_analyser_agent.run.assert_called_once()
        mock_db_client.create_listing.assert_called_once()
        mock_db_client.create_orchestration_run.assert_called_once()

    def test_process_single_listing_fetch_failure(self, base_orchestrator):
        """Test failure when the original listing cannot be fetched."""
        base_orchestrator.listings_db_client.get_listing.side_effect = Exception("DB down")
        
        result = base_orchestrator.process_single_listing("prop123")
        
        assert result is False
        assert base_orchestrator.processed_count == 0
        # The error is not incremented here, as it's a pre-condition failure
        assert base_orchestrator.error_count == 0

    def test_process_single_listing_enrichment_failure(self, base_orchestrator, mock_db_client):
        """Test failure during the enrichment step (e.g., description analysis)."""
        base_orchestrator.description_analyser_agent.run.side_effect = Exception("AI model error")
        
        with pytest.raises(Exception, match="AI model error"):
            base_orchestrator.process_single_listing("prop123")

        assert base_orchestrator.processed_count == 0
        assert base_orchestrator.error_count == 0 # The error is not incremented because the exception is not caught
        mock_db_client.create_listing.assert_not_called()
        mock_db_client.create_orchestration_run.assert_not_called()

    @patch('finder_enrichment.base_orchestrator.ListingCreate')
    def test_build_enriched_listing(self, mock_listing_create, base_orchestrator, mock_listings_db_client, mock_description_analyser):
        """Test the construction of the ListingCreate payload."""
        original_listing_response = mock_listings_db_client.get_listing.return_value
        description_response = mock_description_analyser.analyse_description.return_value

        base_orchestrator._build_enriched_listing(
            original_listing_response,
            enriched_estate_agent_id=10,
            description_analysis_model_response=description_response,
            image_responses=None,
            floorplan_responses=None
        )

        mock_listing_create.assert_called_once()
        
    def test_build_orchestration_run(self, base_orchestrator, mock_listings_db_client, mock_description_analyser):
        """Test the construction of the EnrichmentOrchestrationRunCreate payload."""
        original_listing_response = mock_listings_db_client.get_listing.return_value
        description_response = mock_description_analyser.analyse_description.return_value
        original_listing_response.results[0].id = 123

        orchestration_run_payload = base_orchestrator._build_orchestration_run(
            original_listing_response,
            enriched_listing_id=100,
            description_analysis_model_response=description_response
        )
        
        assert orchestration_run_payload.enrichment_orchestration_set_id == 1
        assert orchestration_run_payload.original_listing_id == 123
        assert orchestration_run_payload.enriched_listing_id == 100
        assert orchestration_run_payload.description_analytics is not None
        assert orchestration_run_payload.description_analytics.model == "test_model" 