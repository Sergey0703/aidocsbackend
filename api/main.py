#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# api/main.py
# Main FastAPI application with production-ready CORS configuration

import logging
import sys
import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Add streamlit-rag to Python path for backend imports
backend_path = Path(__file__).parent.parent / "streamlit-rag"
sys.path.insert(0, str(backend_path))

# Import from modules
from api.modules import search, indexing, vehicles, document_inbox  # 🆕 Added document_inbox
from api.core.dependencies import initialize_system_components

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    Handles startup and shutdown events
    """
    # ============================================================================
    # STARTUP
    # ============================================================================
    logger.info("🚀 Starting Document Intelligence Platform API...")
    logger.info("📁 Backend path: %s", backend_path)
    
    try:
        # Initialize system components for search module
        initialize_system_components()
        logger.info("✅ System components initialized successfully")
    except Exception as e:
        logger.error("❌ Failed to initialize system: %s", e)
        raise
    
    yield
    
    # ============================================================================
    # SHUTDOWN
    # ============================================================================
    logger.info("🛑 Shutting down Document Intelligence Platform API...")
    
    # Cleanup tasks
    try:
        # Import services for cleanup
        from api.modules.indexing.services.indexing_service import get_indexing_service
        from api.modules.indexing.services.conversion_service import get_conversion_service
        
        # Clean up indexing tasks
        logger.info("🧹 Cleaning up indexing tasks...")
        indexing_service = get_indexing_service()
        await indexing_service.clear_completed_tasks()
        
        # Clean up conversion tasks
        logger.info("🧹 Cleaning up conversion tasks...")
        conversion_service = get_conversion_service()
        # Conversion service cleanup if needed
        
        logger.info("✅ Cleanup completed successfully")
        
    except Exception as e:
        logger.error("⚠️ Error during cleanup: %s", e)


# Create FastAPI application
app = FastAPI(
    title="Document Intelligence Platform",
    description="Unified API for document search, indexing, templates, vehicle management, and document inbox",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)


# ============================================================================
# CORS CONFIGURATION - Production Ready
# ============================================================================

# Get allowed origins from environment variable
# Format: comma-separated list of origins
# Example: "http://localhost:3000,https://app.example.com,https://www.example.com"
ALLOWED_ORIGINS_ENV = os.getenv("ALLOWED_ORIGINS", "")

if ALLOWED_ORIGINS_ENV:
    # Production: Use specific origins from environment
    allowed_origins = [origin.strip() for origin in ALLOWED_ORIGINS_ENV.split(",") if origin.strip()]
    logger.info(f"🔒 CORS: Using specific origins from environment")
    logger.info(f"   Allowed origins: {allowed_origins}")
else:
    # Development: Allow common development origins
    allowed_origins = [
        "http://localhost:3000",      # React default
        "http://localhost:8501",      # Streamlit default
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8501",
    ]
    logger.warning("⚠️ CORS: Using development origins (localhost only)")
    logger.warning("   Set ALLOWED_ORIGINS environment variable for production")

# Apply CORS middleware with production-safe settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,           # Specific origins only
    allow_credentials=True,                   # Allow cookies/auth headers
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],  # Specific methods
    allow_headers=[
        "Content-Type",
        "Authorization",
        "Accept",
        "Origin",
        "User-Agent",
        "DNT",
        "Cache-Control",
        "X-Requested-With",
    ],
    expose_headers=["Content-Length", "X-Request-ID"],
    max_age=3600,  # Cache preflight requests for 1 hour
)

logger.info("✅ CORS middleware configured")


# ============================================================================
# ROUTERS
# ============================================================================

# Include search module routers
app.include_router(
    search.search_router,
    prefix="/api/search",
    tags=["Search"]
)

app.include_router(
    search.system_router,
    prefix="/api/system",
    tags=["System"]
)

# Include indexing module routers
app.include_router(
    indexing.indexing_router,
    prefix="/api/indexing",
    tags=["Indexing"]
)

app.include_router(
    indexing.documents_router,
    prefix="/api/documents",
    tags=["Documents"]
)

app.include_router(
    indexing.conversion_router,
    prefix="/api/conversion",
    tags=["Conversion"]
)

app.include_router(
    indexing.monitoring_router,
    prefix="/api/monitoring",
    tags=["Monitoring"]
)

# Include vehicles module routers
app.include_router(
    vehicles.vehicles_router,
    prefix="/api/vehicles",
    tags=["Vehicles"]
)

app.include_router(
    vehicles.documents_router,
    prefix="/api/vehicles",
    tags=["Vehicle Documents"]
)

# 🆕 Include document inbox module router
app.include_router(
    document_inbox.inbox_router,
    prefix="/api/inbox",
    tags=["Document Inbox"]
)


# ============================================================================
# ROOT ENDPOINTS
# ============================================================================

@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint with API information
    """
    from api.modules import AVAILABLE_MODULES
    
    return {
        "name": "Document Intelligence Platform",
        "version": "1.0.0",
        "status": "operational",
        "description": "Unified API for document search, indexing, templates, vehicle management, and document inbox",
        "modules": AVAILABLE_MODULES,
        "endpoints": {
            "search": "/api/search",
            "system": "/api/system",
            "indexing": "/api/indexing",
            "documents": "/api/documents",
            "conversion": "/api/conversion",
            "monitoring": "/api/monitoring",
            "vehicles": "/api/vehicles",
            "inbox": "/api/inbox",  # 🆕
        },
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json"
        },
        "cors": {
            "allowed_origins": allowed_origins if ALLOWED_ORIGINS_ENV else "development_mode",
            "allow_credentials": True
        }
    }


@app.get("/health", tags=["Root"])
async def health_check():
    """
    Quick health check endpoint
    """
    return {
        "status": "healthy",
        "service": "Document Intelligence Platform",
        "version": "1.0.0",
        "modules": {
            "search": "active",
            "indexing": "active",
            "vehicles": "active",
            "inbox": "active"  # 🆕
        }
    }


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Global exception handler for uncaught exceptions
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": str(exc),
            "error_type": type(exc).__name__,
            "message": "An internal server error occurred"
        }
    )


# ============================================================================
# STARTUP MESSAGE
# ============================================================================

@app.on_event("startup")
async def startup_message():
    """
    Print startup message with useful information
    """
    logger.info("=" * 70)
    logger.info("📡 Document Intelligence Platform API")
    logger.info("=" * 70)
    logger.info("🔗 API Documentation: http://localhost:8000/docs")
    logger.info("📚 ReDoc: http://localhost:8000/redoc")
    logger.info("")
    logger.info("🔍 Search endpoints: http://localhost:8000/api/search")
    logger.info("📄 Indexing endpoints: http://localhost:8000/api/indexing")
    logger.info("📋 Documents endpoints: http://localhost:8000/api/documents")
    logger.info("🔄 Conversion endpoints: http://localhost:8000/api/conversion")
    logger.info("📊 Monitoring endpoints: http://localhost:8000/api/monitoring")
    logger.info("🚗 Vehicles endpoints: http://localhost:8000/api/vehicles")
    logger.info("📥 Inbox endpoints: http://localhost:8000/api/inbox")  # 🆕
    logger.info("")
    logger.info("❤️  Health check: http://localhost:8000/health")
    logger.info("")
    logger.info("🔒 CORS Configuration:")
    if ALLOWED_ORIGINS_ENV:
        logger.info("   Mode: PRODUCTION (specific origins)")
        for origin in allowed_origins:
            logger.info(f"   - {origin}")
    else:
        logger.info("   Mode: DEVELOPMENT (localhost only)")
        logger.info("   ⚠️  Set ALLOWED_ORIGINS env var for production")
    logger.info("=" * 70)


if __name__ == "__main__":
    import uvicorn
    
    # Run with uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )