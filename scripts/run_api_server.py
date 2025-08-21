#!/usr/bin/env python3
"""
Script to run the Finder Enrichment API server.

This script starts the FastAPI server on localhost:3100 that provides
endpoints to trigger database orchestration processes.
"""

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import uvicorn
from finder_enrichment.logger_config import setup_logger

def main():
    """Run the API server."""
    logger = setup_logger(__name__)
    
    logger.info("🚀 Starting Finder Enrichment API Server")
    logger.info("📡 Server will be available at: http://localhost:3100")
    logger.info("📖 API documentation at: http://localhost:3100/docs")
    logger.info("🔧 To stop the server, press Ctrl+C")
    
    try:
        uvicorn.run(
            "finder_enrichment.api.api_server:app",
            host="localhost",
            port=3100,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        logger.info("⏹️  Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Server failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 