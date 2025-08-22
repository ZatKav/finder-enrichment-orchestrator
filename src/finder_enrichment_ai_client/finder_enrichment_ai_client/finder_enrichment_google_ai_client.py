"""
Lightweight Google AI client using direct HTTP requests.
Part of the finder-enrichment-ai-client package for managing AI API calls.
"""
import os
import json
import time
from typing import Dict, Any, Optional
import requests

class FinderEnrichmentGoogleAIClient:
    """Lightweight client for Google AI services using direct HTTP requests."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Google AI client.
        
        Args:
            api_key: Google Gemini API key. If None, will check GOOGLE_GEMINI_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("GOOGLE_GEMINI_API_KEY")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        self.model = "gemini-1.5-flash"  # Default model
        
        if not self.api_key:
            raise ValueError("GOOGLE_GEMINI_API_KEY environment variable is required or pass api_key parameter")
    
    def generate_content(
        self, 
        prompt: str, 
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> Dict[str, Any]:
        """
        Generate content using Google's Generative AI API.
        
        Args:
            prompt: The input prompt
            model: Model to use (defaults to gemini-1.5-flash)
            temperature: Creativity level (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            
        Returns:
            API response as dictionary with 'text', 'raw_response', 'success', and optional 'error'
        """
        if not model:
            model = self.model
            
        url = f"{self.base_url}/{model}:generateContent"
        
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key
        }
        
        data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            # Extract the generated text
            if "candidates" in result and result["candidates"]:
                text = result["candidates"][0]["content"]["parts"][0]["text"]
                return {
                    "text": text,
                    "raw_response": result,
                    "success": True
                }
            else:
                return {
                    "text": "",
                    "raw_response": result,
                    "success": False,
                    "error": "No content generated"
                }
                
        except requests.exceptions.RequestException as e:
            return {
                "text": "",
                "raw_response": None,
                "success": False,
                "error": str(e)
            }
    
    def analyze_image(
        self, 
        image_data: str,
        prompt: str,
        image_content_type: Optional[str] = "image/webp",
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze an image using Google's Generative AI API.
        
        Args:
            image_data: base 64 encoded image data
            prompt: Analysis prompt
            model: Model to use
            
        Returns:
            Analysis result as dictionary with 'text', 'raw_response', 'success', and optional 'error'
        """
        if not model:
            model = "gemini-1.5-flash"
            
        try:
            url = f"{self.base_url}/{model}:generateContent"
            
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key
            }
            
            data = {
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": image_content_type,
                                "data": image_data
                            }
                        }
                    ]
                }]
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            
            if "candidates" in result and result["candidates"]:
                text = result["candidates"][0]["content"]["parts"][0]["text"]
                return {
                    "text": text,
                    "raw_response": result,
                    "success": True
                }
            else:
                return {
                    "text": "",
                    "raw_response": result,
                    "success": False,
                    "error": "No content generated"
                }
                
        except Exception as e:
            return {
                "text": "",
                "raw_response": None,
                "success": False,
                "error": str(e)
            }
    
    def set_model(self, model: str):
        """Set the default model to use for API calls."""
        self.model = model
    
    def set_temperature(self, temperature: float):
        """Set the default temperature for content generation."""
        if not 0.0 <= temperature <= 1.0:
            raise ValueError("Temperature must be between 0.0 and 1.0")
        self.temperature = temperature
    
    def get_available_models(self) -> list[str]:
        """Get list of available models (this would require additional API call)."""
        # For now, return common models
        return [
            "gemini-1.5-flash",
            "gemini-1.5-pro",
            "gemini-2.0-flash",
            "gemini-2.0-pro"
        ]
