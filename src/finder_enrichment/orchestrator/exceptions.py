"""
Custom exceptions for the enrichment orchestrator.
"""

class EnrichmentError(Exception):
    """Base exception for enrichment-related errors."""
    pass

class ListingNotFoundError(EnrichmentError):
    """Raised when a listing cannot be found."""
    pass

class EstateAgentError(EnrichmentError):
    """Raised when there are issues with estate agent processing."""
    pass

class DescriptionAnalysisError(EnrichmentError):
    """Raised when description analysis fails."""
    pass

class ImageAnalysisError(EnrichmentError):
    """Raised when image analysis fails."""
    pass

class DatabaseError(EnrichmentError):
    """Raised when database operations fail."""
    pass

class ExternalServiceError(EnrichmentError):
    """Raised when external services (AI models, etc.) fail."""
    pass
