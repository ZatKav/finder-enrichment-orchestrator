import os
from typing import Any, Dict, Optional, List

import requests
from pydantic import ValidationError

from finder_enrichment.api.models import (
    DescriptionAnalysisResult,
    OrchestrationJobResponse,
    OrchestrationJobStatus,
    EnrichmentResult,
    BatchEnrichmentResult,
    BatchImageAnalysisResult,
    ImageAnalysisResult,
)


class OrchestratorAPIClient:
    """
    Client for Finder Enrichment Orchestrator API.

    Handles API key authentication and provides convenience methods to
    trigger and monitor orchestration, description analyser, and image analyser jobs.

    Environment variables used by default:
    - ORCHESTRATOR_BASE_URL (default: "http://localhost:3100")
    - ORCHESTRATOR_API_KEY (required for protected endpoints)
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        api_prefix: str = "/api",
        default_timeout_seconds: float = 30.0,
    ) -> None:
        self.base_url: str = (base_url or os.getenv("ORCHESTRATOR_BASE_URL", "http://localhost:3100")).rstrip("/")
        # Ensure we also pick up .env.local from Next.js env when running locally if exported
        self.api_key: Optional[str] = api_key or os.getenv("ORCHESTRATOR_API_KEY")
        self.api_prefix: str = api_prefix
        self.default_timeout_seconds: float = default_timeout_seconds

    # ---- Internal helpers ----
    def _require_api_key(self) -> str:
        if not self.api_key or not self.api_key.strip():
            raise ValueError(
                "ORCHESTRATOR_API_KEY is required for this operation. Set it via constructor or environment variable."
            )
        return self.api_key

    def _headers(self) -> Dict[str, str]:
        api_key = self._require_api_key()
        return {"Authorization": f"Bearer {api_key}"}

    def _url(self, path: str) -> str:
        # Avoid duplicating '/api' if the base_url already ends with it
        normalized_prefix = self.api_prefix if not self.base_url.endswith(self.api_prefix) else ""
        return f"{self.base_url}{normalized_prefix}{path}"

    def _post(
        self,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[float] = None,
    ) -> requests.Response:
        response = requests.post(
            self._url(path),
            headers=self._headers(),
            params=params,
            timeout=timeout_seconds or self.default_timeout_seconds,
        )
        return response

    def _get(
        self,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[float] = None,
    ) -> requests.Response:
        response = requests.get(
            self._url(path),
            headers=self._headers(),
            params=params,
            timeout=timeout_seconds or self.default_timeout_seconds,
        )
        return response

    @staticmethod
    def _ensure_ok(response: requests.Response) -> Dict[str, Any]:
        if not (200 <= response.status_code < 300):
            # Surface server-provided error payloads when available
            try:
                payload = response.json()
            except Exception:
                payload = {"detail": response.text}
            raise requests.HTTPError(
                f"HTTP {response.status_code}: {payload}", response=response
            )
        try:
            return response.json()
        except Exception as exc:
            raise ValueError(f"Invalid JSON response: {exc}") from exc

    # ---- Public API ----
    def run_database_orchestrator(
        self,
        *,
        limit: Optional[int] = None,
        timeout_seconds: Optional[float] = None,
    ) -> OrchestrationJobResponse:
        """
        Trigger the database orchestrator to process listings.
        """
        response = self._post("/run_database_orchestrator", params={"limit": limit} if limit is not None else None, timeout_seconds=timeout_seconds)
        payload = self._ensure_ok(response)
        try:
            return OrchestrationJobResponse(**payload)
        except ValidationError as exc:
            raise ValueError(f"Unexpected response schema: {exc}\nPayload: {payload}") from exc

    def run_description_analyser(
        self,
        listing_id: int,
        *,
        timeout_seconds: Optional[float] = None,
    ) -> OrchestrationJobResponse:
        response = self._post(f"/run_description_analyser/{listing_id}", timeout_seconds=timeout_seconds)
        payload = self._ensure_ok(response)
        try:
            return OrchestrationJobResponse(**payload)
        except ValidationError as exc:
            raise ValueError(f"Unexpected response schema: {exc}\nPayload: {payload}") from exc

    def run_image_analyser_by_listing_id(
        self,
        listing_id: int,
        *,
        timeout_seconds: Optional[float] = None,
    ) -> OrchestrationJobResponse:
        response = self._post(f"/run_image_analyser/listing/{listing_id}", timeout_seconds=timeout_seconds)
        payload = self._ensure_ok(response)
        try:
            return OrchestrationJobResponse(**payload)
        except ValidationError as exc:
            raise ValueError(f"Unexpected response schema: {exc}\nPayload: {payload}") from exc

    def run_image_analyser_by_image_id(
        self,
        image_id: int,
        *,
        timeout_seconds: Optional[float] = None,
    ) -> OrchestrationJobResponse:
        response = self._post(f"/run_image_analyser/image/{image_id}", timeout_seconds=timeout_seconds)
        payload = self._ensure_ok(response)
        try:
            return OrchestrationJobResponse(**payload)
        except ValidationError as exc:
            raise ValueError(f"Unexpected response schema: {exc}\nPayload: {payload}") from exc

    def get_job_status(
        self,
        job_id: str,
        *,
        timeout_seconds: Optional[float] = None,
    ) -> OrchestrationJobStatus:
        response = self._get(f"/job/{job_id}", timeout_seconds=timeout_seconds)
        payload = self._ensure_ok(response)
        try:
            return OrchestrationJobStatus(**payload)
        except ValidationError as exc:
            raise ValueError(f"Unexpected response schema: {exc}\nPayload: {payload}") from exc

    def wait_for_job_completion(
        self,
        job_id: str,
        *,
        timeout_seconds: float = 60.0,
        poll_interval_seconds: float = 2.0,
    ) -> OrchestrationJobStatus:
        """
        Poll job status until it reaches a terminal state (completed or failed)
        or the timeout expires.
        """
        import time

        deadline = time.time() + timeout_seconds
        last_status: Optional[OrchestrationJobStatus] = None
        while time.time() < deadline:
            last_status = self.get_job_status(job_id)
            if last_status.status in {"completed", "failed"}:
                return last_status
            time.sleep(poll_interval_seconds)
        # If we exit due to timeout, return the last observed status if any
        if last_status is not None:
            return last_status
        raise TimeoutError(f"Timed out waiting for job {job_id} to complete")

    # ---- Synchronous Enrichment API ----

    def enrich_listing(self, listing_id: str, *, timeout_seconds: Optional[float] = None) -> EnrichmentResult:
        """
        Enrich a single listing synchronously.

        This method uses the new synchronous enrichment endpoint that processes
        listings immediately without background jobs.

        Args:
            listing_id: The ID of the listing to enrich
            timeout_seconds: Optional timeout for the request

        Returns:
            EnrichmentResult with the processing outcome

        Raises:
            ValueError: If the response schema is unexpected
            requests.HTTPError: If the request fails
        """
        response = self._post(f"/enrich/listing/{listing_id}", timeout_seconds=timeout_seconds)
        payload = self._ensure_ok(response)
        try:
            return EnrichmentResult(**payload)
        except ValidationError as exc:
            raise ValueError(f"Unexpected response schema: {exc}\nPayload: {payload}") from exc

    def enrich_listings(self, listing_ids: List[str], *, timeout_seconds: Optional[float] = None) -> BatchEnrichmentResult:
        """
        Enrich multiple listings synchronously in a batch.

        This method uses the new synchronous batch enrichment endpoint that processes
        multiple listings immediately, continuing even if individual listings fail.

        Args:
            listing_ids: List of listing IDs to process
            timeout_seconds: Optional timeout for the request

        Returns:
            BatchEnrichmentResult with results for all processed listings

        Raises:
            ValueError: If the response schema is unexpected
            requests.HTTPError: If the request fails
        """
        request_body = {"listing_ids": listing_ids}
        response = self._post("/enrich/listings", json=request_body, timeout_seconds=timeout_seconds)
        payload = self._ensure_ok(response)
        try:
            return BatchEnrichmentResult(**payload)
        except ValidationError as exc:
            raise ValueError(f"Unexpected response schema: {exc}\nPayload: {payload}") from exc 
        
    def enrich_description(self, listing_id: str, *, timeout_seconds: Optional[float] = None) -> DescriptionAnalysisResult:
        """
        Enrich a single listing synchronously.

        This method uses the new synchronous enrichment endpoint that processes
        listings immediately without background jobs.
        """
        response = self._post(f"/enrich/description/{listing_id}", timeout_seconds=timeout_seconds)
        payload = self._ensure_ok(response)
        try:
            return DescriptionAnalysisResult(**payload)
        except ValidationError as exc:
            raise ValueError(f"Unexpected response schema: {exc}\nPayload: {payload}") from exc
        
    def enrich_listing_images(self, listing_id: str, *, timeout_seconds: Optional[float] = None) -> BatchImageAnalysisResult:
        """
        Enrich a single listing synchronously.

        This method uses the new synchronous enrichment endpoint that processes
        listings immediately without background jobs.
        """
        response = self._post(f"/enrich/listing/images/{listing_id}", timeout_seconds=timeout_seconds)
        payload = self._ensure_ok(response)
        try:
            return BatchImageAnalysisResult(**payload)
        except ValidationError as exc:
            raise ValueError(f"Unexpected response schema: {exc}\nPayload: {payload}") from exc
        
    def enrich_image(self, image_id: str, *, timeout_seconds: Optional[float] = None) -> ImageAnalysisResult:
        """
        Enrich a single image synchronously.

        This method uses the new synchronous enrichment endpoint that processes
        images immediately without background jobs.
        """
        response = self._post(f"/enrich/image/{image_id}", timeout_seconds=timeout_seconds)
        payload = self._ensure_ok(response)
        try:
            return ImageAnalysisResult(**payload)
        except ValidationError as exc:
            raise ValueError(f"Unexpected response schema: {exc}\nPayload: {payload}") from exc
        
    def enrichment_health(self) -> Dict[str, Any]:
        """
        Check the health of the enrichment service.
        """
        response = self._get("/enrich/health")
        return self._ensure_ok(response)