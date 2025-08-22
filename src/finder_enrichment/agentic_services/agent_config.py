import os

from finder_enrichment_ai_client import FinderEnrichmentGoogleAIClient

class AgentConfig:
    """Configuration for Google Gemini agents using lightweight HTTP client."""
    
    def __init__(self):
        self.api_key = os.getenv('GOOGLE_GEMINI_API_KEY')  # Updated env var name
        if not self.api_key:
            raise ValueError("GOOGLE_GEMINI_API_KEY not found in environment variables")
        
        # Use Gemini 1.5 Flash for fast, free responses
        self.model = "gemini-1.5-flash"
        self.temperature = 0.7
        self.max_tokens = 100000
        
        # Initialize lightweight HTTP client
        self.client = FinderEnrichmentGoogleAIClient(api_key=self.api_key)
        
    def get_client(self):
        """Get a properly configured lightweight Google AI client."""
        return self.client