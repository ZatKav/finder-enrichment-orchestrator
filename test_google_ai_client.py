#!/usr/bin/env python3
"""
Test script for the lightweight Google AI HTTP client.
Tests basic connectivity and functionality before integration.
"""

import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our lightweight client from the new package location
from src.finder_enrichment_ai_client.finder_enrichment_ai_client import FinderEnrichmentGoogleAIClient

def test_basic_connectivity():
    """Test basic connectivity to Google AI API."""
    print("🧪 Testing Google AI HTTP Client")
    print("=" * 50)
    
    # Check API key
    api_key = os.getenv('GOOGLE_GEMINI_API_KEY')
    if not api_key:
        print("❌ GOOGLE_GEMINI_API_KEY not found in environment variables")
        print("   Please set GOOGLE_GEMINI_API_KEY in your .env file")
        return False
    
    print(f"✅ API key found: {api_key[:10]}...")
    
    try:
        # Initialize client
        client = FinderEnrichmentGoogleAIClient()
        print("✅ FinderEnrichmentGoogleAIClient initialized successfully")
        
        # Test simple text generation
        print("\n📝 Testing text generation...")
        response = client.generate_content("Hello! Please respond with just 'Hello back!'")
        
        if response['success']:
            print(f"✅ API call successful!")
            print(f"   Response: {response['text']}")
            print(f"   Raw response keys: {list(response['raw_response'].keys())}")
        else:
            print(f"❌ API call failed: {response['error']}")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Error initializing client: {e}")
        return False

def test_image_analysis():
    """Test image analysis functionality."""
    print("\n🖼️  Testing image analysis...")
    
    try:
        client = FinderEnrichmentGoogleAIClient()
        
        # Test with a simple image URL (you can change this)
        test_image_url = "https://picsum.photos/200/300"  # Random test image
        prompt = "Describe this image in one sentence"
        
        print(f"   Testing with image: {test_image_url}")
        print(f"   Prompt: {prompt}")
        
        response = client.analyze_image(test_image_url, prompt)
        
        if response['success']:
            print(f"✅ Image analysis successful!")
            print(f"   Response: {response['text']}")
        else:
            print(f"❌ Image analysis failed: {response['error']}")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Error in image analysis: {e}")
        return False

def test_error_handling():
    """Test error handling with invalid API key."""
    print("\n🚨 Testing error handling...")
    
    try:
        # Create client with invalid key
        original_key = os.environ.get('GOOGLE_GEMINI_API_KEY')
        os.environ['GOOGLE_GEMINI_API_KEY'] = 'invalid_key'
        
        client = FinderEnrichmentGoogleAIClient()
        response = client.generate_content("Test")
        
        if not response['success']:
            print("✅ Error handling working - invalid key properly rejected")
        else:
            print("❌ Error handling failed - invalid key was accepted")
            return False
            
        # Restore original key
        if original_key:
            os.environ['GOOGLE_GEMINI_API_KEY'] = original_key
        else:
            del os.environ['GOOGLE_GEMINI_API_KEY']
            
        return True
        
    except Exception as e:
        print(f"✅ Error handling working - exception caught: {e}")
        # Restore original key
        if original_key:
            os.environ['GOOGLE_GEMINI_API_KEY'] = original_key
        return True

def test_api_key_parameter():
    """Test passing API key as parameter instead of environment variable."""
    print("\n🔑 Testing API key parameter...")
    
    try:
        # Get the real API key
        api_key = os.getenv('GOOGLE_GEMINI_API_KEY')
        if not api_key:
            print("❌ No API key available for testing")
            return False
        
        # Create client with parameter
        client = FinderEnrichmentGoogleAIClient(api_key=api_key)
        print("✅ GoogleAIClient initialized with API key parameter")
        
        # Test functionality
        response = client.generate_content("Test with parameter API key")
        
        if response['success']:
            print("✅ API call successful with parameter API key")
            return True
        else:
            print(f"❌ API call failed: {response['error']}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing API key parameter: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Starting Google AI HTTP Client Tests")
    print("=" * 60)
    
    tests = [
        ("Basic Connectivity", test_basic_connectivity),
        ("Image Analysis", test_image_analysis),
        ("Error Handling", test_error_handling),
        ("API Key Parameter", test_api_key_parameter),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running: {test_name}")
        print("-" * 40)
        
        try:
            if test_func():
                print(f"✅ {test_name}: PASSED")
                passed += 1
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Ready to integrate the lightweight client.")
        print("\nNext steps:")
        print("1. ✅ HTTP client is working")
        print("2. 🔄 Update agent services to use new client")
        print("3. 🧹 Remove Google Generative AI dependencies")
        print("4. 🚀 Deploy to Vercel with 100MB+ savings!")
    else:
        print("⚠️  Some tests failed. Please fix issues before integration.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
