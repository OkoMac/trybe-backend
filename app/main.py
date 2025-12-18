"""
Trybe Platform - Main Application Entry Point
FastAPI application with all endpoints and middleware
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import os

# Import routers
from app.api.v1.api import api_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Application metadata
APP_NAME = os.getenv("APP_NAME", "Trybe Platform")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Sentry integration
SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN and os.getenv("ENABLE_SENTRY", "true").lower() == "true":
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            environment=ENVIRONMENT,
            integrations=[
                FastApiIntegration(),
                SqlalchemyIntegration(),
            ],
            traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        )
        logger.info("Sentry initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize Sentry: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info(f"Starting {APP_NAME} v{APP_VERSION}")
    logger.info(f"Environment: {ENVIRONMENT}")
    logger.info(f"Debug mode: {DEBUG}")

    # Initialize Elasticsearch indices if enabled
    if os.getenv("ENABLE_ELASTICSEARCH", "true").lower() == "true":
        try:
            from app.services.elasticsearch_service import elasticsearch_service
            logger.info("Elasticsearch service initialized")
        except Exception as e:
            logger.warning(f"Elasticsearch initialization failed: {e}")

    yield

    # Shutdown
    logger.info(f"Shutting down {APP_NAME}")

    # Close Elasticsearch connection
    try:
        from app.services.elasticsearch_service import elasticsearch_service
        await elasticsearch_service.close()
        logger.info("Elasticsearch connection closed")
    except:
        pass


# Create FastAPI application
app = FastAPI(
    title=APP_NAME,
    description="A comprehensive opportunity marketplace and talent management platform",
    version=APP_VERSION,
    debug=DEBUG,
    lifespan=lifespan,
    docs_url="/docs" if DEBUG or ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if DEBUG or ENVIRONMENT == "development" else None,
)

# CORS Middleware
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip Middleware for response compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Include API router
app.include_router(api_router, prefix="/api/v1")


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint - API information"""
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "status": "running",
        "environment": ENVIRONMENT,
        "docs": "/docs" if DEBUG or ENVIRONMENT == "development" else "disabled",
        "endpoints": {
            "auth": "/api/v1/auth",
            "opportunities": "/api/v1/opportunities",
            "payments": "/api/v1/payments",
            "escrow": "/api/v1/escrow",
            "messages": "/api/v1/messages",
            "notifications": "/api/v1/notifications",
            "learning": "/api/v1/learning",
            "search": "/api/v1/search",
            "video-calls": "/api/v1/video-calls",
        }
    }


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "service": APP_NAME,
        "version": APP_VERSION,
        "environment": ENVIRONMENT
    }


# Readiness check
@app.get("/ready", tags=["Health"])
async def readiness_check():
    """Readiness check for Kubernetes/Docker"""
    # TODO: Add database connection check
    # TODO: Add Redis connection check
    # TODO: Add Elasticsearch connection check
    return {"status": "ready"}


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    if DEBUG:
        return JSONResponse(
            status_code=500,
            content={
                "detail": str(exc),
                "type": type(exc).__name__
            }
        )
    else:
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=DEBUG,
        log_level="info" if DEBUG else "warning"
    )
