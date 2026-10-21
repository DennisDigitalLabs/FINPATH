"""
FINPATH Backend - Main FastAPI Application

Entry point for the FINPATH backend service.
Initializes the FastAPI application with database, middleware, and routes.
"""

from contextlib import asynccontextmanager
import logging
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import get_settings
from backend.database import close_db, init_db
from backend.routes.auth import router as auth_router
from backend.routes.assessment import router as assessment_router
from backend.routes.prediction import router as prediction_router
from backend.routes.recommendation import router as recommendation_router
from backend.routes.dashboard import router as dashboard_router
from backend.routes.analytics import router as analytics_router

# Get settings
settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifespan events (startup and shutdown).
    
    Startup:
        - Initialize database and create tables
    
    Shutdown:
        - Close database connections
    """
    # Startup
    print("🚀 Initializing FINPATH Backend...")
    await init_db()
    print("✅ Database initialized successfully")
    
    yield
    
    # Shutdown
    print("🔌 Shutting down FINPATH Backend...")
    await close_db()
    print("✅ Database connections closed")


# Create FastAPI application
app = FastAPI(
    title="FINPATH API",
    description="Explainable ML-Based Financial Inclusion Risk Assessment System",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception):
    logger.error(
        "Unhandled API exception for %s %s",
        request.method,
        request.url.path,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected internal error occurred"},
    )

app.include_router(auth_router)
app.include_router(assessment_router)
app.include_router(prediction_router)
app.include_router(recommendation_router)
app.include_router(dashboard_router)
app.include_router(analytics_router)


@app.get("/", tags=["root"])
async def root() -> Dict[str, Any]:
    """
    Root endpoint - Welcome message.
    
    Returns:
        Welcome message and API information
    """
    return {
        "message": "Welcome to FINPATH API",
        "description": "Explainable ML-Based Financial Inclusion Risk Assessment System",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health", tags=["health"])
async def health() -> Dict[str, str]:
    """
    Health check endpoint - Verify backend is operational.
    
    Returns:
        Health status message
    """
    return {
        "status": "healthy",
        "service": "FINPATH Backend",
        "environment": settings.ENVIRONMENT,
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",  # nosec B104 - required for Docker/Render
        port=8000,
        reload=settings.DEBUG,
    )
