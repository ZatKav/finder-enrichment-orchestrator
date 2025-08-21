"""
Unit tests for the configuration module.
"""

import pytest
import os
from unittest.mock import patch

from finder_enrichment.config import (
    ServiceEndpoint,
    DatabaseConfig,
    AIConfig,
    EnrichmentConfig,
    get_config
)


class TestServiceEndpoint:
    """Test the ServiceEndpoint class."""
    
    def test_basic_url(self):
        """Test basic URL generation."""
        endpoint = ServiceEndpoint(host="localhost", port=8080)
        assert endpoint.url == "http://localhost:8080"
        
    def test_url_with_base_path(self):
        """Test URL generation with base path."""
        endpoint = ServiceEndpoint(
            host="localhost", 
            port=8080, 
            base_path="/api/v1"
        )
        assert endpoint.url == "http://localhost:8080/api/v1"
        
    def test_url_with_https(self):
        """Test URL generation with HTTPS."""
        endpoint = ServiceEndpoint(
            host="example.com", 
            port=443, 
            protocol="https"
        )
        assert endpoint.url == "https://example.com:443"


class TestDatabaseConfig:
    """Test the DatabaseConfig class."""
    
    def test_defaults(self):
        """Test default configuration values."""
        config = DatabaseConfig()
        assert config.host == "localhost"
        assert config.port == 5432
        assert config.database == "finder"
        assert config.username == "finder_user"
        
    def test_from_env(self):
        """Test creating config from environment variables."""
        env_vars = {
            "TESTDB_HOST": "test-host",
            "TESTDB_PORT": "5433",
            "TESTDB_NAME": "test_db",
            "TESTDB_USER": "test_user",
            "TESTDB_PASSWORD": "test_pass"
        }
        
        with patch.dict(os.environ, env_vars):
            config = DatabaseConfig.from_env("TESTDB")
            
        assert config.host == "test-host"
        assert config.port == 5433
        assert config.database == "test_db"
        assert config.username == "test_user"
        assert config.password == "test_pass"


class TestAIConfig:
    """Test the AIConfig class."""
    
    def test_defaults(self):
        """Test default configuration values."""
        config = AIConfig()
        assert config.provider == "google"
        assert config.model == "gemini-2.0-flash"
        assert config.temperature == 0.7
        
    def test_from_env_google(self):
        """Test creating Google AI config from environment."""
        env_vars = {
            "AI_PROVIDER": "google",
            "GOOGLE_GEMINI_API_KEY": "test-key-123",
            "AI_MODEL": "gemini-pro",
            "AI_TEMPERATURE": "0.5"
        }
        
        with patch.dict(os.environ, env_vars):
            config = AIConfig.from_env()
            
        assert config.provider == "google"
        assert config.api_key == "test-key-123"
        assert config.model == "gemini-pro"
        assert config.temperature == 0.5
        
    def test_from_env_openai(self):
        """Test creating OpenAI config from environment."""
        env_vars = {
            "AI_PROVIDER": "openai",
            "OPENAI_API_KEY": "openai-key-456"
        }
        
        with patch.dict(os.environ, env_vars):
            config = AIConfig.from_env()
            
        assert config.provider == "openai"
        assert config.api_key == "openai-key-456"


class TestEnrichmentConfig:
    """Test the EnrichmentConfig class."""
    
    def test_defaults(self):
        """Test default configuration values."""
        config = EnrichmentConfig()
        assert config.kafka_bootstrap_servers == "localhost:9092"
        assert config.max_workers == 4
        assert config.enable_parallel_processing is True
        
    def test_from_env(self):
        """Test creating config from environment variables."""
        env_vars = {
            "KAFKA_BOOTSTRAP_SERVERS": "kafka1:9092,kafka2:9092",
            "MAX_WORKERS": "8",
            "ENABLE_PARALLEL_PROCESSING": "false",
            "DESCRIPTION_ANALYSER_HOST": "desc-service",
            "DESCRIPTION_ANALYSER_PORT": "9001",
            "LOG_LEVEL": "DEBUG"
        }
        
        with patch.dict(os.environ, env_vars):
            config = EnrichmentConfig.from_env()
            
        assert config.kafka_bootstrap_servers == "kafka1:9092,kafka2:9092"
        assert config.max_workers == 8
        assert config.enable_parallel_processing is False
        assert config.description_analyser_endpoint.host == "desc-service"
        assert config.description_analyser_endpoint.port == 9001
        assert config.log_level == "DEBUG"
        
    def test_validation_success(self):
        """Test successful configuration validation."""
        config = EnrichmentConfig()
        config.ai_config.api_key = "test-key"
        
        # Should not raise any exception
        config.validate()
        
    def test_validation_missing_api_key(self):
        """Test validation failure with missing API key."""
        config = EnrichmentConfig()
        config.ai_config.api_key = ""
        
        with pytest.raises(ValueError, match="AI API key is required"):
            config.validate()
            
    def test_validation_invalid_max_workers(self):
        """Test validation failure with invalid max_workers."""
        config = EnrichmentConfig()
        config.ai_config.api_key = "test-key"
        config.max_workers = 0
        
        with pytest.raises(ValueError, match="max_workers must be positive"):
            config.validate()
            
    def test_validation_invalid_endpoint(self):
        """Test validation failure with invalid endpoint."""
        config = EnrichmentConfig()
        config.ai_config.api_key = "test-key"
        config.listings_db_endpoint.host = ""
        
        with pytest.raises(ValueError, match="listings_db endpoint host is required"):
            config.validate()


class TestGetConfig:
    """Test the get_config function."""
    
    @patch('finder_enrichment.config.EnrichmentConfig.validate')
    @patch('finder_enrichment.config.EnrichmentConfig.create_log_directory')
    def test_get_config(self, mock_create_log_dir, mock_validate):
        """Test getting configuration."""
        with patch.dict(os.environ, {"GOOGLE_GEMINI_API_KEY": "test-key"}):
            config = get_config()
            
        assert isinstance(config, EnrichmentConfig)
        mock_validate.assert_called_once()
        mock_create_log_dir.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__]) 