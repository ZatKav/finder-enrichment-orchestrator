"""
Unit tests for the KafkaEnrichmentOrchestrator class.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json

from finder_enrichment.kafka_orchestrator import KafkaEnrichmentOrchestrator
from finder_enrichment.kafka.kafka_manager import KafkaManager

@pytest.fixture
def mock_kafka_manager():
    """Mock Kafka manager for testing."""
    manager = Mock(spec=KafkaManager)
    manager.get_consumer.return_value = MagicMock()
    manager.get_producer.return_value = MagicMock()
    return manager

@pytest.fixture
def orchestrator(mock_kafka_manager):
    """Create a KafkaEnrichmentOrchestrator instance for testing."""
    # Note: The Kafka orchestrator inherits from the base, but for these tests,
    # we are focusing on the Kafka-specific message handling logic, not the
    # full enrichment pipeline which is tested in test_base_orchestrator.
    return KafkaEnrichmentOrchestrator(
        kafka_manager=mock_kafka_manager,
        max_workers=2,
        enable_parallel_processing=False
    )

class TestKafkaEnrichmentOrchestrator:
    """Test the KafkaEnrichmentOrchestrator class."""

    def test_initialization(self, orchestrator):
        """Test orchestrator initialization."""
        assert orchestrator.max_workers == 2
        assert not orchestrator.enable_parallel_processing
        assert not orchestrator.is_running
        assert orchestrator.processed_count == 0
        assert orchestrator.error_count == 0
        assert isinstance(orchestrator.kafka_manager, KafkaManager)

    @patch('finder_enrichment.base_orchestrator.BaseEnrichmentOrchestrator.process_single_listing')
    def test_handle_property_discovered(self, mock_process_single_listing, orchestrator):
        """Test handling property discovered messages from Kafka."""
        message_data = {
            "property_id": "prop456",
            "title": "New Kafka House",
            "description": "A property from a Kafka topic."
        }
        
        orchestrator._handle_property_discovered(message_data)
        
        # The Kafka orchestrator should call the base processor
        mock_process_single_listing.assert_called_once_with("prop456")

    def test_process_message_property_discovered(self, orchestrator):
        """Test routing a 'property_discovered' message."""
        topic = "finder.harvester.property.discovered"
        message_data = {"property_id": "prop1"}
        
        with patch.object(orchestrator, 'process_single_listing', new=Mock()) as mock_process:
            orchestrator._process_message(topic, message_data)
            mock_process.assert_called_once_with("prop1")

    def test_process_message_unhandled_topic(self, orchestrator, caplog):
        """Test that an unhandled topic is logged and ignored."""
        topic = "unhandled_topic"
        message_data = {"data": "some_data"}
        
        orchestrator._process_message(topic, message_data)
        
        assert "Unknown topic" in caplog.text
        assert "unhandled_topic" in caplog.text 