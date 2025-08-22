"""
API server for Finder Enrichment operations.

Provides REST endpoints to trigger enrichment processes.
"""
import os
import sys

# Add src directory to Python path for Vercel deployment
# This ensures imports work correctly in the Vercel environment
vercel_working_dir = os.getcwd()
if vercel_working_dir == '/var/task':  # Vercel deployment
    src_path = os.path.join(vercel_working_dir, 'src')
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

from datetime import datetime, timezone
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import the db client
from finder_enrichment_db_client import FinderEnrichmentDBAPIClient
from listings_db_api_client.listings_db_api_client import ListingsDBAPIClient

# Security imports
from finder_enrichment.api.security import (
    SecurityHeadersMiddleware,
    setup_rate_limiting,
    limiter,
)

# Logger configuration
from finder_enrichment.logger_config import setup_logger

load_dotenv()

# Configure logging
logger = setup_logger(__name__)

# Try to import orchestrator and agent modules with error handling
try:
    from finder_enrichment.orchestrator.database_orchestrator import DatabaseEnrichmentOrchestrator
    from finder_enrichment.agentic_services.description_analyser.description_analyser_agent import DescriptionAnalyserAgent
    from finder_enrichment.agentic_services.image_analyser.image_analyser_agent import ImageAnalyserAgent
    from finder_enrichment.api.routers.orchestration import router as orchestration_router
    from finder_enrichment.api.routers.description_analyser import router as description_analyser_router
    from finder_enrichment.api.routers.image_analyser import router as image_analyser_router
    import finder_enrichment.api.globals as g
    
    modules_imported = True
    logger.info("All required modules imported successfully")
    
except ImportError as e:
    modules_imported = False
    logger.error(f"Failed to import required modules: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    
    logger.info("Starting Finder Enrichment API server...")
    
    # Check if required modules were imported successfully
    if not modules_imported:
        error_msg = "Required modules failed to import - check import dependencies"
        logger.error(error_msg)
        g.orchestrator_error = {
            "error": error_msg,
            "error_type": "ImportError",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": "One or more required Python modules could not be imported"
        }
        g.orchestrator = None
        yield
        return
    
    # Validate required environment variables
    required_env_vars = [
        "LISTINGS_DB_BASE_URL",
        "LISTINGS_DB_API_KEY", 
        "ENRICHED_DB_BASE_URL",
        "ENRICHMENT_DB_API_KEY",
        "GOOGLE_GEMINI_API_KEY"
    ]
    
    missing_env_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_env_vars:
        error_msg = f"Missing required environment variables: {missing_env_vars}"
        logger.error(error_msg)
        g.orchestrator_error = {
            "error": error_msg,
            "error_type": "MissingEnvironmentVariables",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "missing_variables": missing_env_vars
        }
        g.orchestrator = None
        yield
        return
    
    # Initialize orchestrator and service clients
    try:
        logger.info("Initializing DatabaseEnrichmentOrchestrator...")
        g.orchestrator = DatabaseEnrichmentOrchestrator(
            max_workers=4,
            enable_parallel_processing=True,
            batch_size=50
        )
        logger.info("DatabaseEnrichmentOrchestrator created successfully")
        
        # Setup service clients
        listings_db_url = os.getenv("LISTINGS_DB_BASE_URL", "http://localhost:8000/api")
        enriched_db_url = os.getenv("ENRICHED_DB_BASE_URL", "http://localhost:8200")

        logger.info(f"Connecting to Listings DB at: {listings_db_url}")
        logger.info(f"Connecting to Enriched DB at: {enriched_db_url}")

        logger.info("Creating ListingsDBAPIClient...")
        try:
            listings_db_client = ListingsDBAPIClient(
                base_url=listings_db_url,
                api_key=os.getenv("LISTINGS_DB_API_KEY")
            )
            logger.info("ListingsDBAPIClient created successfully")
        except Exception as e:
            logger.error(f"Failed to create ListingsDBAPIClient: {e}")
            raise RuntimeError(f"ListingsDBAPIClient creation failed: {e}")
        
        logger.info("Creating FinderEnrichmentDBAPIClient...")
        try:
            enriched_db_client = FinderEnrichmentDBAPIClient(
                base_url=enriched_db_url,
                api_key=os.getenv("ENRICHMENT_DB_API_KEY")
            )
            logger.info("FinderEnrichmentDBAPIClient created successfully")
        except Exception as e:
            logger.error(f"Failed to create FinderEnrichmentDBAPIClient: {e}")
            raise RuntimeError(f"FinderEnrichmentDBAPIClient creation failed: {e}")
        
        # Initialize description analyser
        logger.info("Initializing DescriptionAnalyserAgent...")
        try:
            description_analyser = DescriptionAnalyserAgent()
            logger.info("DescriptionAnalyserAgent initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize DescriptionAnalyserAgent: {e}")
            raise RuntimeError(f"DescriptionAnalyserAgent initialization failed: {e}")

        # Initialize image analyser
        logger.info("Initializing ImageAnalyserAgent...")
        try:
            image_analyser = ImageAnalyserAgent()
            logger.info("ImageAnalyserAgent initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ImageAnalyserAgent: {e}")
            raise RuntimeError(f"ImageAnalyserAgent initialization failed: {e}")
        
        # Configure the orchestrator with service clients
        logger.info("Setting service clients on orchestrator...")
        try:
            g.orchestrator.set_service_clients(
                listings_db_client=listings_db_client,
                description_analyser_client=description_analyser,
                enriched_db_client=enriched_db_client,
                image_analyser_client=image_analyser
            )
            logger.info("Service clients set successfully on orchestrator")
        except Exception as e:
            logger.error(f"Failed to set service clients on orchestrator: {e}")
            raise RuntimeError(f"Service client configuration failed: {e}")
        
        logger.info("Orchestrator initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize orchestrator: {e}", exc_info=True)
        # Store the error details for health check
        error_details = {
            "error": str(e),
            "error_type": type(e).__name__,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        g.orchestrator_error = error_details
        logger.error(f"Stored orchestrator error details: {error_details}")
        g.orchestrator = None
    
    yield
    
    logger.info("Shutting down Finder Enrichment API server...")


# Create FastAPI app
app = FastAPI(
    title="Finder Enrichment API",
    description="API for triggering property listing enrichment processes",
    version="1.0.0",
    lifespan=lifespan
)

# Setup rate limiting
setup_rate_limiting(app)

# Add CORS middleware to allow calls from the dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("DASHBOARD_URL")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Only include routers if they were successfully imported
if modules_imported:
    app.include_router(orchestration_router, prefix="/api", tags=["orchestration"])
    app.include_router(description_analyser_router, prefix="/api", tags=["description_analyser"])
    app.include_router(image_analyser_router, prefix="/api", tags=["image_analyser"])
    logger.info("All API routers included successfully")
else:
    logger.warning("Skipping router inclusion due to import failures")

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Finder Enrichment API",
        "version": "1.0.0",
        "status": "running"
    }
    
@app.get("/startup-check")
async def startup_check():
    """
    Basic startup check to verify the application can start up.

    Returns:
        Basic startup status information
    """
    return {
        "status": "started",
        "modules_imported": modules_imported,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": "Application startup check completed"
    }

@app.get("/jobs")
async def get_all_jobs():
    """
    Get status of all orchestration jobs.
    
    Returns:
        List of all job statuses
    """
    return {"jobs": list(g.running_jobs.values())}

@app.get("/health")
async def health_check():
    """Health check endpoint that also checks external service connectivity."""
    orchestrator_status = "initialized" if g.orchestrator else "not_initialized"
    
    # Get detailed orchestrator information
    orchestrator_details = {}
    if g.orchestrator:
        orchestrator_details = {
            "status": "initialized",
            "max_workers": g.orchestrator.max_workers,
            "enable_parallel_processing": g.orchestrator.enable_parallel_processing,
            "batch_size": getattr(g.orchestrator, 'batch_size', 'N/A'),
            "service_clients_configured": {
                "listings_db_client": g.orchestrator.listings_db_client is not None,
                "enriched_db_client": g.orchestrator.enriched_db_client is not None,
                "description_analyser_agent": g.orchestrator.description_analyser_agent is not None,
                "image_analyser_client": g.orchestrator.image_analyser_client is not None
            }
        }
    else:
        orchestrator_details = {
            "status": "not_initialized",
            "error_details": g.orchestrator_error if hasattr(g, 'orchestrator_error') and g.orchestrator_error else None
        }

    # Check external service connectivity
    services_status = {}
    
    # Test listings DB connectivity
    try:
        listings_client = ListingsDBAPIClient(api_key=os.getenv("LISTINGS_DB_API_KEY"), base_url=os.getenv("LISTINGS_DB_BASE_URL"))
        listings_client.get_listings(limit=1)
        services_status["listings_db"] = {
            "status": "connected",
            "url": os.getenv("LISTINGS_DB_BASE_URL")
        }
    except Exception as e:
        services_status["listings_db"] = {
            "status": "disconnected", 
            "error": str(e),
            "url": os.getenv("LISTINGS_DB_BASE_URL")
        }
    
    # Test enrichment DB connectivity
    try:
        enriched_client = FinderEnrichmentDBAPIClient(
            base_url=os.getenv("ENRICHMENT_DB_BASE_URL"),
            api_key=os.getenv("ENRICHMENT_DB_API_KEY")
        )
        enriched_client.get_estate_agents(limit=1)
        services_status["enrichment_db"] = {
            "status": "connected",
            "url": os.getenv("ENRICHMENT_DB_BASE_URL")
        }
    except Exception as e:
        services_status["enrichment_db"] = {
            "status": "disconnected",
            "error": str(e), 
            "url": os.getenv("ENRICHMENT_DB_BASE_URL")
        }
    
    # Determine overall health
    all_services_connected = all(
        service["status"] == "connected" 
        for service in services_status.values()
    )
    
    overall_status = "healthy" if (orchestrator_status == "initialized" and all_services_connected) else "degraded"
    
    return {
        "status": overall_status,
        "modules_imported": modules_imported,
        "orchestrator": orchestrator_details,
        "external_services": services_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": "All services operational" if overall_status == "healthy" else "Some services are unavailable - check orchestrator and external_services for details"
    }
   
if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting Finder Enrichment API server on localhost:3100")
    uvicorn.run(
        "finder_enrichment.api.api_server:app",
        host="localhost",
        port=3100,
        reload=True,
        log_level="info"
    ) 