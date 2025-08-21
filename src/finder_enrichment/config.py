"""
Configuration management for the Finder Enrichment Orchestrator.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ServiceEndpoint:
    """Configuration for a service endpoint."""
    host: str
    port: int
    protocol: str = "http"
    base_path: str = ""
    timeout: int = 30
    retries: int = 3
    
    @property
    def url(self) -> str:
        """Get the full URL for this endpoint."""
        base_url = f"{self.protocol}://{self.host}:{self.port}"
        if self.base_path:
            base_url = f"{base_url}/{self.base_path.strip('/')}"
        return base_url


@dataclass 
class DatabaseConfig:
    """Configuration for database connections."""
    host: str = "localhost"
    port: int = 5432
    database: str = "finder"
    username: str = "finder_user"
    password: str = ""
    ssl_mode: str = "prefer"
    
    @classmethod
    def from_env(cls, prefix: str = "DB") -> "DatabaseConfig":
        """Create database config from environment variables."""
        return cls(
            host=os.getenv(f"{prefix}_HOST", cls.host),
            port=int(os.getenv(f"{prefix}_PORT", str(cls.port))),
            database=os.getenv(f"{prefix}_NAME", cls.database),
            username=os.getenv(f"{prefix}_USER", cls.username),
            password=os.getenv(f"{prefix}_PASSWORD", cls.password),
            ssl_mode=os.getenv(f"{prefix}_SSL_MODE", cls.ssl_mode),
        )


@dataclass
class AIConfig:
    """Configuration for AI/ML services."""
    provider: str = "google"  # google, openai, anthropic
    api_key: str = ""
    model: str = "gemini-2.0-flash"
    temperature: float = 0.7
    max_tokens: int = 100000
    timeout: int = 60
    
    @classmethod
    def from_env(cls) -> "AIConfig":
        """Create AI config from environment variables."""
        provider = os.getenv("AI_PROVIDER", cls.provider).lower()
        
        # Determine API key based on provider
        api_key = ""
        if provider == "google":
            api_key = os.getenv("GOOGLE_GEMINI_API_KEY", "")
        elif provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY", "")
        elif provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY", "")
            
        return cls(
            provider=provider,
            api_key=api_key,
            model=os.getenv("AI_MODEL", cls.model),
            temperature=float(os.getenv("AI_TEMPERATURE", str(cls.temperature))),
            max_tokens=int(os.getenv("AI_MAX_TOKENS", str(cls.max_tokens))),
            timeout=int(os.getenv("AI_TIMEOUT", str(cls.timeout))),
        )


@dataclass
class EnrichmentConfig:
    """Configuration for the enrichment orchestrator."""
    
    # Kafka configuration
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_group_id: str = "enrichment-orchestrator"
    
    # Processing configuration
    max_workers: int = 4
    enable_parallel_processing: bool = True
    processing_timeout: int = 300  # seconds
    retry_attempts: int = 3
    retry_delay: int = 5  # seconds
    
    # Service endpoints
    listings_db_endpoint: ServiceEndpoint = field(
        default_factory=lambda: ServiceEndpoint(
            host="localhost", 
            port=8001,
            base_path="/api/v1"
        )
    )
    
    description_analyser_endpoint: ServiceEndpoint = field(
        default_factory=lambda: ServiceEndpoint(
            host="localhost",
            port=8002,
            base_path="/api/v1"
        )
    )
    
    floorplan_analyser_endpoint: ServiceEndpoint = field(
        default_factory=lambda: ServiceEndpoint(
            host="localhost",
            port=8003,
            base_path="/api/v1"
        )
    )
    
    image_analyser_endpoint: ServiceEndpoint = field(
        default_factory=lambda: ServiceEndpoint(
            host="localhost",
            port=8004,
            base_path="/api/v1"
        )
    )
    
    enriched_db_endpoint: ServiceEndpoint = field(
        default_factory=lambda: ServiceEndpoint(
            host="localhost",
            port=8005,
            base_path="/api/v1"
        )
    )
    
    # Database configurations
    listings_db: DatabaseConfig = field(
        default_factory=lambda: DatabaseConfig.from_env("LISTINGS_DB")
    )
    
    enriched_db: DatabaseConfig = field(
        default_factory=lambda: DatabaseConfig.from_env("ENRICHED_DB")
    )
    
    # AI configuration
    ai_config: AIConfig = field(
        default_factory=AIConfig.from_env
    )
    
    # Logging configuration
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    enable_file_logging: bool = True
    log_file_path: str = "logs/enrichment_orchestrator.log"
    
    @classmethod
    def from_env(cls) -> "EnrichmentConfig":
        """Create configuration from environment variables."""
        config = cls()
        
        # Kafka configuration
        config.kafka_bootstrap_servers = os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS", 
            config.kafka_bootstrap_servers
        )
        config.kafka_group_id = os.getenv(
            "KAFKA_GROUP_ID",
            config.kafka_group_id
        )
        
        # Processing configuration
        config.max_workers = int(os.getenv("MAX_WORKERS", str(config.max_workers)))
        config.enable_parallel_processing = os.getenv(
            "ENABLE_PARALLEL_PROCESSING", 
            str(config.enable_parallel_processing)
        ).lower() in ("true", "1", "yes")
        config.processing_timeout = int(os.getenv(
            "PROCESSING_TIMEOUT", 
            str(config.processing_timeout)
        ))
        config.retry_attempts = int(os.getenv(
            "RETRY_ATTEMPTS",
            str(config.retry_attempts)
        ))
        config.retry_delay = int(os.getenv(
            "RETRY_DELAY",
            str(config.retry_delay)
        ))
        
        # Service endpoints
        config.listings_db_endpoint = ServiceEndpoint(
            host=os.getenv("LISTINGS_DB_HOST", config.listings_db_endpoint.host),
            port=int(os.getenv("LISTINGS_DB_PORT", str(config.listings_db_endpoint.port))),
            protocol=os.getenv("LISTINGS_DB_PROTOCOL", config.listings_db_endpoint.protocol),
            base_path=os.getenv("LISTINGS_DB_BASE_PATH", config.listings_db_endpoint.base_path),
        )
        
        config.description_analyser_endpoint = ServiceEndpoint(
            host=os.getenv("DESCRIPTION_ANALYSER_HOST", config.description_analyser_endpoint.host),
            port=int(os.getenv("DESCRIPTION_ANALYSER_PORT", str(config.description_analyser_endpoint.port))),
            protocol=os.getenv("DESCRIPTION_ANALYSER_PROTOCOL", config.description_analyser_endpoint.protocol),
            base_path=os.getenv("DESCRIPTION_ANALYSER_BASE_PATH", config.description_analyser_endpoint.base_path),
        )
        
        config.floorplan_analyser_endpoint = ServiceEndpoint(
            host=os.getenv("FLOORPLAN_ANALYSER_HOST", config.floorplan_analyser_endpoint.host),
            port=int(os.getenv("FLOORPLAN_ANALYSER_PORT", str(config.floorplan_analyser_endpoint.port))),
            protocol=os.getenv("FLOORPLAN_ANALYSER_PROTOCOL", config.floorplan_analyser_endpoint.protocol),
            base_path=os.getenv("FLOORPLAN_ANALYSER_BASE_PATH", config.floorplan_analyser_endpoint.base_path),
        )
        
        config.image_analyser_endpoint = ServiceEndpoint(
            host=os.getenv("IMAGE_ANALYSER_HOST", config.image_analyser_endpoint.host),
            port=int(os.getenv("IMAGE_ANALYSER_PORT", str(config.image_analyser_endpoint.port))),
            protocol=os.getenv("IMAGE_ANALYSER_PROTOCOL", config.image_analyser_endpoint.protocol),
            base_path=os.getenv("IMAGE_ANALYSER_BASE_PATH", config.image_analyser_endpoint.base_path),
        )
        
        config.enriched_db_endpoint = ServiceEndpoint(
            host=os.getenv("ENRICHED_DB_HOST", config.enriched_db_endpoint.host),
            port=int(os.getenv("ENRICHED_DB_PORT", str(config.enriched_db_endpoint.port))),
            protocol=os.getenv("ENRICHED_DB_PROTOCOL", config.enriched_db_endpoint.protocol),
            base_path=os.getenv("ENRICHED_DB_BASE_PATH", config.enriched_db_endpoint.base_path),
        )
        
        # Logging configuration
        config.log_level = os.getenv("LOG_LEVEL", config.log_level)
        config.log_format = os.getenv("LOG_FORMAT", config.log_format)
        config.enable_file_logging = os.getenv(
            "ENABLE_FILE_LOGGING",
            str(config.enable_file_logging)
        ).lower() in ("true", "1", "yes")
        config.log_file_path = os.getenv("LOG_FILE_PATH", config.log_file_path)
        
        return config
    
    def validate(self) -> None:
        """Validate the configuration."""
        errors = []
        
        # Validate AI configuration
        if not self.ai_config.api_key:
            errors.append(f"AI API key is required for provider '{self.ai_config.provider}'")
            
        # Validate service endpoints
        endpoints = [
            ("listings_db", self.listings_db_endpoint),
            ("description_analyser", self.description_analyser_endpoint),
            ("floorplan_analyser", self.floorplan_analyser_endpoint),
            ("image_analyser", self.image_analyser_endpoint),
            ("enriched_db", self.enriched_db_endpoint),
        ]
        
        for name, endpoint in endpoints:
            if not endpoint.host:
                errors.append(f"{name} endpoint host is required")
            if endpoint.port <= 0:
                errors.append(f"{name} endpoint port must be positive")
                
        # Validate processing configuration
        if self.max_workers <= 0:
            errors.append("max_workers must be positive")
        if self.processing_timeout <= 0:
            errors.append("processing_timeout must be positive")
        if self.retry_attempts < 0:
            errors.append("retry_attempts must be non-negative")
            
        if errors:
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")
    
    def create_log_directory(self) -> None:
        """Create log directory if it doesn't exist."""
        if self.enable_file_logging:
            log_path = Path(self.log_file_path)
            log_path.parent.mkdir(parents=True, exist_ok=True)


def get_config() -> EnrichmentConfig:
    """Get the configuration instance."""
    config = EnrichmentConfig.from_env()
    config.validate()
    config.create_log_directory()
    return config


def load_config_from_file(config_path: str) -> EnrichmentConfig:
    """Load configuration from a file (JSON, YAML, etc.)."""
    # This could be extended to support config files
    # For now, just return environment-based config
    return get_config() 