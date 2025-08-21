import os
import uuid
import pytest
from fastapi.testclient import TestClient
from dotenv import load_dotenv

from finder_enrichment.api.api_server import app

load_dotenv()


@pytest.fixture()
def test_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    # Ensure API key is set for the app under test
    api_key = os.getenv("ORCHESTRATOR_API_KEY", "test-orchestrator-key")
    monkeypatch.setenv("ORCHESTRATOR_API_KEY", api_key)
    return TestClient(app)


@pytest.fixture(scope="module")
def api_key() -> str:
    key = os.getenv("ORCHESTRATOR_API_KEY", "test-orchestrator-key")
    if not key:
        raise EnvironmentError("ORCHESTRATOR_API_KEY environment variable is required for testing.")
    return key


class TestAuthentication:
    """Authentication tests against orchestrator endpoints."""

    def test_health_endpoint_no_auth_required(self, test_client: TestClient):
        response = test_client.get("/health")
        assert response.status_code == 200
        assert response.json().get("status") in {"ok", "healthy", "degraded"}

    def test_root_endpoint_no_auth_required(self, test_client: TestClient):
        response = test_client.get("/")
        assert response.status_code == 200
        assert "message" in response.json()

    def test_protected_endpoints_without_auth_fail(self, test_client: TestClient):
        # Map endpoints to HTTP methods
        protected_calls = [
            ("POST", "/api/run_database_orchestrator"),
            ("POST", "/api/run_description_analyser/1"),
            ("POST", "/api/run_image_analyser/listing/1"),
            ("POST", "/api/run_image_analyser/image/1"),
            ("GET", f"/api/job/{uuid.uuid4()}"),
        ]
        for method, endpoint in protected_calls:
            resp = test_client.request(method, endpoint)
            assert resp.status_code == 500, f"Endpoint {endpoint} should require authentication"

    def test_protected_endpoints_with_valid_api_key(self, test_client: TestClient, api_key: str):
        headers = {"Authorization": f"Bearer {api_key}"}
        # These should succeed with 200; job GET may be 404 if unknown job id
        calls = [
            ("POST", "/api/run_database_orchestrator", [200]),
            ("POST", "/api/run_description_analyser/1", [200]),
            ("POST", "/api/run_image_analyser/listing/1", [200]),
            ("POST", "/api/run_image_analyser/image/1", [200]),
            ("GET", f"/api/job/{uuid.uuid4()}", [200, 404]),
        ]
        for method, endpoint, ok_codes in calls:
            resp = test_client.request(method, endpoint, headers=headers)
            assert resp.status_code in ok_codes, f"{endpoint} with auth expected {ok_codes}, got {resp.status_code}"

    def test_wrong_scheme_fails(self, test_client: TestClient, api_key: str):
        headers = {"Authorization": f"Basic {api_key}"}
        resp = test_client.post("/api/run_database_orchestrator", headers=headers)
        assert resp.status_code == 500

    def test_malformed_header_fails(self, test_client: TestClient, api_key: str):
        headers = {"Authorization": f"Bearer{api_key}"}  # Missing space
        resp = test_client.post("/api/run_database_orchestrator", headers=headers)
        assert resp.status_code == 500

    def test_empty_bearer_token_fails(self, test_client: TestClient):
        headers = {"Authorization": "Bearer "}
        resp = test_client.post("/api/run_database_orchestrator", headers=headers)
        assert resp.status_code == 500

    def test_partial_api_key_fails(self, test_client: TestClient, api_key: str):
        partial_key = api_key[: len(api_key) // 2] if len(api_key) > 1 else "partial"
        headers = {"Authorization": f"Bearer {partial_key}"}
        resp = test_client.post("/api/run_database_orchestrator", headers=headers)
        assert resp.status_code == 500

    def test_extra_characters_in_key_fails(self, test_client: TestClient, api_key: str):
        modified_key = f"{api_key}extra"
        headers = {"Authorization": f"Bearer {modified_key}"}
        resp = test_client.post("/api/run_database_orchestrator", headers=headers)
        assert resp.status_code == 500

    def test_whitespace_in_key_is_ignored(self, test_client: TestClient, api_key: str):
        modified_key = f" {api_key} "
        headers = {"Authorization": f"Bearer {modified_key}"}
        resp = test_client.post("/api/run_database_orchestrator", headers=headers)
        assert resp.status_code == 200

    def test_bearer_scheme_case_insensitive(self, test_client: TestClient, api_key: str):
        headers = {"Authorization": f"bearer {api_key}"}
        resp = test_client.post("/api/run_database_orchestrator", headers=headers)
        assert resp.status_code == 200

        headers = {"Authorization": f"BeArEr {api_key}"}
        resp = test_client.post("/api/run_database_orchestrator", headers=headers)
        assert resp.status_code == 200

    def test_api_key_exact_match_required(self, test_client: TestClient, api_key: str):
        if len(api_key) > 1:
            different_key = api_key[:-1] + ("1" if api_key[-1] != "1" else "2")
            headers = {"Authorization": f"Bearer {different_key}"}
            resp = test_client.post("/api/run_database_orchestrator", headers=headers)
            assert resp.status_code == 500 