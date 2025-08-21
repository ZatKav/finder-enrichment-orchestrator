"""
Unit and integration tests for the Finder Enrichment API server.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from finder_enrichment.api.api_server import app, orchestrator, running_jobs
from finder_enrichment.orchestrator.database_orchestrator import DatabaseEnrichmentOrchestrator


class TestAPIServer:
    """Test class for API server endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_orchestrator(self):
        """Create a mock orchestrator."""
        mock = Mock(spec=DatabaseEnrichmentOrchestrator)
        mock.process_all_listings = Mock()
        mock.get_database_stats = Mock(return_value={
            "processed_count": 5,
            "error_count": 0,
            "success_rate": 1.0,
            "batch_size": 50
        })
        return mock
    
    @pytest.fixture(autouse=True)
    def setup_test_data(self):
        """Setup and cleanup test data."""
        # Clear running jobs before each test
        running_jobs.clear()
        yield
        # Clear running jobs after each test
        running_jobs.clear()


class TestHealthEndpoints(TestAPIServer):
    """Test health and info endpoints."""
    
    def test_root_endpoint(self, client):
        """Test the root endpoint returns proper information."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Finder Enrichment API"
        assert data["version"] == "1.0.0"
        assert "endpoints" in data
        assert "run_database_orchestrator" in data["endpoints"]
    
    def test_health_endpoint_with_orchestrator(self, client, mock_orchestrator):
        """Test health endpoint when orchestrator is initialized."""
        with patch('finder_enrichment.api.api_server.orchestrator', mock_orchestrator):
            response = client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["orchestrator"] == "initialized"
            assert "timestamp" in data
    
    def test_health_endpoint_without_orchestrator(self, client):
        """Test health endpoint when orchestrator is not initialized."""
        with patch('finder_enrichment.api.api_server.orchestrator', None):
            response = client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["orchestrator"] == "not_initialized"


class TestJobManagement(TestAPIServer):
    """Test job management endpoints."""
    
    def test_get_jobs_empty(self, client):
        """Test getting jobs when no jobs exist."""
        response = client.get("/jobs")
        
        assert response.status_code == 200
        data = response.json()
        assert data["jobs"] == []
    
    def test_get_jobs_with_data(self, client):
        """Test getting jobs when jobs exist."""
        # Add test job data
        test_job = {
            "job_id": "test_job_123",
            "status": "completed",
            "started_at": "2023-12-15T14:30:00Z",
            "completed_at": "2023-12-15T14:31:00Z"
        }
        running_jobs["test_job_123"] = test_job
        
        response = client.get("/jobs")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["jobs"]) == 1
        assert data["jobs"][0] == test_job
    
    def test_get_job_status_existing(self, client):
        """Test getting status of existing job."""
        test_job = {
            "job_id": "test_job_456",
            "status": "running",
            "started_at": "2023-12-15T14:30:00Z"
        }
        running_jobs["test_job_456"] = test_job
        
        response = client.get("/job/test_job_456")
        
        assert response.status_code == 200
        data = response.json()
        # Check that the returned data contains the original job data
        assert data["job_id"] == test_job["job_id"]
        assert data["status"] == test_job["status"]
        assert data["started_at"] == test_job["started_at"]
    
    def test_get_job_status_nonexistent(self, client):
        """Test getting status of non-existent job."""
        response = client.get("/job/nonexistent_job")
        
        assert response.status_code == 404
        assert "Job not found" in response.json()["detail"]


class TestOrchestrationEndpoint(TestAPIServer):
    """Test the main orchestration endpoint."""
    
    def test_run_orchestrator_without_initialized_orchestrator(self, client):
        """Test running orchestrator when not initialized."""
        with patch('finder_enrichment.api.api_server.orchestrator', None):
            response = client.post("/run_database_orchestrator")
            
            assert response.status_code == 503
            assert "Orchestrator not initialized" in response.json()["detail"]
    
    def test_run_orchestrator_success(self, client, mock_orchestrator):
        """Test successful orchestrator run."""
        with patch('finder_enrichment.api.api_server.orchestrator', mock_orchestrator):
            response = client.post("/run_database_orchestrator")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "starting" # This remains as the initial response
            assert "job_id" in data
            job_id = data["job_id"]
            assert job_id in running_jobs
            # In a test environment, the background task runs synchronously
            assert running_jobs[job_id]["status"] == "completed"
    
    def test_run_orchestrator_with_limit(self, client, mock_orchestrator):
        """Test orchestrator run with limit parameter."""
        with patch('finder_enrichment.api.api_server.orchestrator', mock_orchestrator):
            response = client.post("/run_database_orchestrator?limit=10")
            
            assert response.status_code == 200
            data = response.json()
            assert "(limit: 10)" in data["message"]
            
            # Check that limit was stored in job data
            job_id = data["job_id"]
            assert running_jobs[job_id]["limit"] == 10
    
    def test_orchestrator_background_task_success(self, client):
        """Test the background task wrapper for a successful orchestration."""
        mock_orchestrator = Mock(spec=DatabaseEnrichmentOrchestrator)
        mock_orchestrator.process_all_listings = Mock()
        mock_orchestrator.get_database_stats = Mock(return_value={
            "processed_count": 10,
            "error_count": 0,
            "success_rate": 1.0
        })

        with patch('finder_enrichment.api.api_server.orchestrator', mock_orchestrator):
            response = client.post("/run_database_orchestrator")
            assert response.status_code == 200
            job_id = response.json()["job_id"]

            # In a test environment, the background task runs synchronously
            status_response = client.get(f"/job/{job_id}")
            assert status_response.status_code == 200
            job_status = status_response.json()
            assert job_status["status"] == "completed"
            assert job_status["error"] is None
            assert job_status["stats"]["processed_count"] == 10
    
    def test_orchestrator_background_task_failure(self):
        """Test the background task wrapper for a failed orchestration."""
        from finder_enrichment.api.api_server import run_orchestrator_process
        
        # Initialize job
        job_id = "bg_test_failure"
        running_jobs[job_id] = {"status": "starting", "job_id": job_id}

        # Test with no orchestrator (should fail)
        with patch('finder_enrichment.api.api_server.orchestrator', None):
            run_orchestrator_process(job_id)
            
            assert running_jobs[job_id]["status"] == "failed"
            assert "completed_at" in running_jobs[job_id]
            assert "error" in running_jobs[job_id]
            assert "Orchestrator not initialized" in running_jobs[job_id]["error"]


class TestCORSConfiguration(TestAPIServer):
    """Test CORS configuration."""
    
    def test_cors_preflight_request(self, client):
        """Test CORS preflight request is handled correctly."""
        response = client.options(
            "/run_database_orchestrator",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )
        
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers


class TestErrorHandling(TestAPIServer):
    """Test error handling scenarios."""
    
    def test_orchestrator_process_exception(self, client, mock_orchestrator):
        """Test handling of exceptions during orchestrator processing."""
        mock_orchestrator.process_all_listings.side_effect = Exception("Database connection failed")
        
        with patch('finder_enrichment.api.api_server.orchestrator', mock_orchestrator):
            response = client.post("/run_database_orchestrator")
            
            assert response.status_code == 200  # Request succeeds, but background task will fail
            data = response.json()
            job_id = data["job_id"]
            
            # Let the background task run (in real test, we'd need to wait or mock differently)
            # For now, we'll test the error handling function directly
            from finder_enrichment.api.api_server import run_orchestrator_process
            run_orchestrator_process(job_id)
            
            assert running_jobs[job_id]["status"] == "failed"
            assert "Database connection failed" in running_jobs[job_id]["error"]


class TestIntegration:
    """Integration tests for the full API workflow."""
    
    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)
    
    def test_full_orchestration_workflow(self, client):
        """Test the complete workflow from start to finish."""
        mock_orchestrator = Mock(spec=DatabaseEnrichmentOrchestrator)
        mock_orchestrator.process_all_listings = Mock()
        mock_orchestrator.get_database_stats = Mock(return_value={
            "processed_count": 2,
            "error_count": 0,
            "success_rate": 1.0,
            "batch_size": 50
        })
        
        with patch('finder_enrichment.api.api_server.orchestrator', mock_orchestrator):
            # 1. Check health
            health_response = client.get("/health")
            assert health_response.status_code == 200
            assert health_response.json()["orchestrator"] == "initialized"
            
            # 2. Start orchestration
            start_response = client.post("/run_database_orchestrator?limit=2")
            assert start_response.status_code == 200
            job_data = start_response.json()
            job_id = job_data["job_id"]
            
            # 3. Check job was created
            jobs_response = client.get("/jobs")
            assert jobs_response.status_code == 200
            assert len(jobs_response.json()["jobs"]) == 1
            
            # 4. Get specific job status
            status_response = client.get(f"/job/{job_id}")
            assert status_response.status_code == 200
            job_status = status_response.json()
            assert job_status["job_id"] == job_id
            # The job runs synchronously in tests, so it should be completed
            assert job_status["status"] == "completed"
            
            # 5. Simulate background task completion
            from finder_enrichment.api.api_server import run_orchestrator_process
            run_orchestrator_process(job_id, limit=2)
            
            # 6. Check final job status
            final_status_response = client.get(f"/job/{job_id}")
            assert final_status_response.status_code == 200
            final_job_status = final_status_response.json()
            assert final_job_status["status"] == "completed"
            assert "stats" in final_job_status
            assert final_job_status["stats"]["processed_count"] == 2


# Test fixtures and utilities
@pytest.fixture
def mock_db_clients():
    """Mock database clients."""
    listings_client = Mock()
    enriched_client = Mock()
    
    listings_client.get_listings = Mock(return_value=Mock(results=[]))
    enriched_client.create_orchestration_set = Mock(return_value=Mock(id=1))
    
    return listings_client, enriched_client


@pytest.fixture
def mock_description_analyser():
    """Mock description analyser."""
    analyser = Mock()
    analyser.run = Mock(return_value={
        "analysis": "test analysis",
        "sentiment": "positive"
    })
    return analyser


# Additional utility tests
class TestJobIdGeneration(TestAPIServer):
    """Test job ID generation logic."""
    
    def test_job_id_format(self, client):
        """Test that job IDs follow expected format."""
        with patch('finder_enrichment.api.api_server.orchestrator', Mock(spec=DatabaseEnrichmentOrchestrator)):
            response = client.post("/run_database_orchestrator")
            assert response.status_code == 200
            job_id = response.json()["job_id"]
            
            # Example format: orchestration_20231215_143022_a1b2c3d4
            parts = job_id.split('_')
            assert len(parts) == 3
            assert parts[0] == "orchestration"
            # Check that the timestamp part is a valid date and time
            from datetime import datetime
            datetime.strptime(parts[1], '%Y%m%d')


if __name__ == "__main__":
    pytest.main([__file__]) 