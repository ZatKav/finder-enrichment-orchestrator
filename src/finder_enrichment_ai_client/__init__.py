"""
Finder Enrichment AI Client Package

A lightweight package for managing AI API calls to various providers.
Currently supports Google Gemini AI with more providers coming soon.
"""

from .finder_enrichment_ai_client import FinderEnrichmentGoogleAIClient

__version__ = "0.1.0"
__all__ = ["FinderEnrichmentGoogleAIClient"]
