#!/usr/bin/env python3
"""
Simple test script for the Finder Enrichment API.

This script tests the API endpoints to ensure they're working correctly.
"""

import requests
import time
import json
import sys


def test_api():
    """Test the API endpoints."""
    base_url = "http://localhost:3100"
    
    print("🧪 Testing Finder Enrichment API")
    print(f"📡 Base URL: {base_url}")
    print("-" * 50)
    
    # Test 1: Health check
    try:
        print("1. Testing health check endpoint...")
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Health check passed: {data['status']}")
            print(f"   📊 Orchestrator status: {data['orchestrator']}")
        else:
            print(f"   ❌ Health check failed: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Health check failed: {e}")
        print("   💡 Make sure the API server is running on localhost:3100")
        return False
    
    # Test 2: Root endpoint
    try:
        print("\n2. Testing root endpoint...")
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Root endpoint working: {data['message']}")
        else:
            print(f"   ❌ Root endpoint failed: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Root endpoint failed: {e}")
    
    # Test 3: Jobs endpoint
    try:
        print("\n3. Testing jobs endpoint...")
        response = requests.get(f"{base_url}/jobs", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Jobs endpoint working: {len(data['jobs'])} jobs found")
        else:
            print(f"   ❌ Jobs endpoint failed: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Jobs endpoint failed: {e}")
    
    # Test 4: Test orchestrator run (with limit to avoid processing too much)
    try:
        print("\n4. Testing orchestrator run (with limit=1)...")
        response = requests.post(f"{base_url}/run_database_orchestrator?limit=1", timeout=10)
        if response.status_code == 200:
            data = response.json()
            job_id = data['job_id']
            print(f"   ✅ Orchestrator started: Job {job_id}")
            
            # Poll job status for a short time
            print("   ⏳ Checking job status...")
            for i in range(5):  # Check up to 5 times
                time.sleep(2)
                try:
                    status_response = requests.get(f"{base_url}/job/{job_id}", timeout=5)
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        print(f"   📊 Job status: {status_data['status']}")
                        if status_data['status'] in ['completed', 'failed']:
                            break
                    else:
                        print(f"   ⚠️ Could not get job status: {status_response.status_code}")
                        break
                except requests.exceptions.RequestException:
                    print(f"   ⚠️ Could not get job status")
                    break
        else:
            print(f"   ⚠️ Orchestrator run failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   📝 Error: {error_data.get('detail', 'Unknown error')}")
            except:
                print(f"   📝 Response: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"   ⚠️ Orchestrator test failed: {e}")
    
    print("\n✅ API testing completed!")
    return True


def main():
    """Main function."""
    if not test_api():
        print("\n❌ API tests failed. Check that the API server is running.")
        sys.exit(1)
    
    print("\n🎉 All basic API tests passed!")
    print("\n💡 Next steps:")
    print("   • Open browser to http://localhost:3100/docs for interactive API docs")
    print("   • Run the dashboard with: make run-dashboard")
    print("   • Test the full integration with the dashboard")


if __name__ == "__main__":
    main() 