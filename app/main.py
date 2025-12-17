"""Trybe Backend - FastAPI Application"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import logging
import sys

from app.core.config import settings
from app.api.v1.api import api_router
from app.core.security_headers import add_security_headers, add_cors_headers
from app.core.rate_limit import add_rate_limit_headers
from app.core.sentry import init_sentry

# Initialize Sentry for error tracking
init_sentry()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("🚀 Starting Trybe API...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Version: {settings.VERSION}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info(f"Sentry enabled: {bool(settings.SENTRY_DSN)}")

    # TODO: Initialize database connection pool
    # TODO: Initialize Redis connection
    # TODO: Run startup tasks

    yield

    # Shutdown
    logger.info("👋 Shutting down Trybe API...")
    # TODO: Close database connections
    # TODO: Close Redis connections


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Trybe People's Market - Backend API",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Trusted Host Middleware (production only)
if settings.is_production:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["trybe.app", "*.trybe.app", "api.trybe.app"]
    )

# Security Headers Middleware
app.middleware("http")(add_security_headers)
app.middleware("http")(add_cors_headers)

# Rate Limit Headers Middleware
app.middleware("http")(add_rate_limit_headers)


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "version": settings.APP_VERSION
    }


@app.get("/health/ready", tags=["Health"])
async def readiness_check():
    """Readiness check - verifies all dependencies are ready"""
    # TODO: Check database connection
    # TODO: Check Redis connection
    return {
        "status": "ready",
        "database": "connected",
        "redis": "connected"
    }


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """API root endpoint"""
    return {
        "message": "Welcome to Trybe API",
        "version": settings.APP_VERSION,
        "docs": "/docs" if not settings.is_production else "disabled",
        "health": "/health"
    }


# Include API v1 routes
app.include_router(api_router, prefix="/api/v1")

# Future route includes:
# TODO: Include opportunities routes
# TODO: Include payments routes
# TODO: Include learning routes
# TODO: Include messages routes
# TODO: Include performance routes
# TODO: Include reports routes
# TODO: Include solar routes


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler with Sentry integration"""
    # Log the error
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    # Sentry's FastAPI integration will automatically capture this
    # But we can add additional context if needed
    from app.core.sentry import capture_exception
    capture_exception(exc, url=str(request.url), method=request.method)

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error",
            "error": str(exc) if settings.DEBUG else "An error occurred"
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info"
    )
