#!/usr/bin/env python3
"""
Integration Test Environment Setup Validator

This script checks if your environment is properly configured for running
the synchronous enrichment integration tests.
"""

import os
import sys
import requests
from dotenv import load_dotenv

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from listings_db_api_client.listings_db_api_client import ListingsDBAPIClient
    from finder_enrichment_db_client import FinderEnrichmentDBAPIClient
    from finder_enrichment.api.orchestrator_api_client import OrchestratorAPIClient
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("Please ensure all dependencies are installed: uv install")
    sys.exit(1)

load_dotenv()

def check_environment_variables():
    """Check if all required environment variables are set."""
    print("🔍 Checking environment variables...")

    required_vars = [
        "ORCHESTRATOR_BASE_URL",
        "ORCHESTRATOR_API_KEY",
        "LISTINGS_DB_BASE_URL",
        "LISTINGS_DB_API_KEY",
        "ENRICHMENT_DB_BASE_URL",
        "ENRICHMENT_DB_API_KEY",
        "GOOGLE_GEMINI_API_KEY"
    ]

    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if not value or value.strip() == "":
            missing_vars.append(var)
        else:
            # Show first few characters of sensitive values
            if "KEY" in var or "TOKEN" in var:
                print(f"   ✅ {var} = {value[:8]}...")
            else:
                print(f"   ✅ {var} = {value}")

    if missing_vars:
        print("   ❌ Missing variables:")
        for var in missing_vars:
            print(f"      - {var}")
        return False

    print("   ✅ All environment variables are set")
    return True

def check_orchestrator_api():
    """Check if the orchestrator API is running."""
    print("\n🔍 Checking orchestrator API...")

    base_url = os.getenv("ORCHESTRATOR_BASE_URL", "http://localhost:3100")

    try:
        # Check health endpoint
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("   ✅ Health endpoint is responding")

            # Check synchronous enrichment health
            try:
                response = requests.get(f"{base_url}/api/enrichment/health", timeout=5)
                if response.status_code == 200:
                    print("   ✅ Synchronous enrichment health endpoint is responding")
                else:
                    print(f"   ❌ Synchronous enrichment health endpoint returned {response.status_code}")
            except Exception as e:
                print(f"   ❌ Synchronous enrichment health endpoint error: {e}")
        else:
            print(f"   ❌ Health endpoint returned {response.status_code}")
            return False

    except Exception as e:
        print(f"   ❌ Cannot connect to orchestrator API: {e}")
        return False

    return True

def check_listings_database():
    """Check if the listings database is accessible."""
    print("\n🔍 Checking listings database...")

    try:
        listings_client = ListingsDBAPIClient(
            api_key=os.getenv("LISTINGS_DB_API_KEY"),
            base_url=os.getenv("LISTINGS_DB_BASE_URL")
        )

        # Try to fetch one listing
        listings = listings_client.get_listings(limit=1)
        if listings and len(listings) > 0:
            print(f"   ✅ Listings database is accessible (found {len(listings)} listing)")
            return True
        else:
            print("   ⚠️  Listings database is accessible but no listings found")
            return True

    except Exception as e:
        print(f"   ❌ Cannot connect to listings database: {e}")
        return False

def check_enrichment_database():
    """Check if the enrichment database is accessible."""
    print("\n🔍 Checking enrichment database...")

    try:
        enrichment_client = FinderEnrichmentDBAPIClient(
            api_key=os.getenv("ENRICHMENT_DB_API_KEY"),
            base_url=os.getenv("ENRICHMENT_DB_BASE_URL")
        )

        # Try to fetch estate agents (simple query)
        try:
            estate_agents = enrichment_client.get_estate_agents(limit=1)
            print(f"   ✅ Enrichment database is accessible (found {len(estate_agents)} estate agent)")
            return True
        except Exception as e:
            print(f"   ⚠️  Enrichment database connected but query failed: {e}")
            return True

    except Exception as e:
        print(f"   ❌ Cannot connect to enrichment database: {e}")
        return False

def check_google_ai():
    """Check if Google AI API is accessible."""
    print("\n🔍 Checking Google AI API...")

    try:
        # Simple test prompt
        from finder_enrichment.agentic_services.image_analyser.image_analyser_agent import ImageAnalyserAgent

        # This will test if the API key works
        agent = ImageAnalyserAgent()
        print("   ✅ Google AI API key is configured")
        return True

    except Exception as e:
        print(f"   ❌ Google AI API configuration error: {e}")
        return False

def test_basic_integration():
    """Test a basic integration to see if everything works together."""
    print("\n🔍 Testing basic integration...")

    try:
        client = OrchestratorAPIClient(
            base_url=os.getenv("ORCHESTRATOR_BASE_URL"),
            api_key=os.getenv("ORCHESTRATOR_API_KEY")
        )

        # Test health endpoint
        response = requests.get(f"{os.getenv('ORCHESTRATOR_BASE_URL')}/api/enrichment/health", timeout=10)
        if response.status_code == 200:
            print("   ✅ Basic API integration working")
            return True
        else:
            print(f"   ❌ Basic API integration failed: {response.status_code}")
            return False

    except Exception as e:
        print(f"   ❌ Basic API integration error: {e}")
        return False

def main():
    """Run all environment checks."""
    print("🚀 Synchronous Enrichment Integration Test Environment Check")
    print("=" * 60)

    checks = [
        check_environment_variables,
        check_orchestrator_api,
        check_listings_database,
        check_enrichment_database,
        check_google_ai,
        test_basic_integration
    ]

    results = []
    for check in checks:
        try:
            results.append(check())
        except Exception as e:
            print(f"   ❌ Check failed with exception: {e}")
            results.append(False)

    print("\n" + "=" * 60)
    print("📊 Environment Check Summary:")

    passed = sum(results)
    total = len(results)
    print(f"   ✅ Passed: {passed}/{total}")
    print(f"   ❌ Failed: {total - passed}/{total}")

    if passed == total:
        print("\n🎉 Environment is ready for integration tests!")
        print("\nYou can now run:")
        print("   uv run python -m pytest src/finder_enrichment/tests/test_synchronous_enrichment_api.py -v")
        print("   uv run python -m pytest src/finder_enrichment/tests/test_synchronous_orchestration_api.py -v")
        return 0
    else:
        print("\n❌ Environment is not ready for integration tests.")
        print("Please fix the issues above before running integration tests.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
