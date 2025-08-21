import google.generativeai as genai
import os

class AgentConfig:
    """Configuration for Google Gemini agents."""
    
    def __init__(self):
        self.api_key = os.getenv('GOOGLE_GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GOOGLE_GEMINI_API_KEY not found in environment variables")
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        
        # Use Gemini 1.5 Flash for fast, free responses
        self.model = "gemini-2.0-flash"
        self.temperature = 0.7
        self.max_tokens = 100000
        
    def get_client(self):
        """Get a properly configured Gemini client."""
        return genai.GenerativeModel(self.model)