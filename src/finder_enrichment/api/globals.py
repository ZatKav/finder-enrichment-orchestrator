# Global orchestrator instance
from typing import Any, Dict, Optional

from finder_enrichment.orchestrator.database_orchestrator import DatabaseEnrichmentOrchestrator


orchestrator: Optional[DatabaseEnrichmentOrchestrator] = None

# Track running jobs
running_jobs: Dict[str, Dict[str, Any]] = {}

# Store orchestrator initialization error details
orchestrator_error: Optional[Dict[str, Any]] = None