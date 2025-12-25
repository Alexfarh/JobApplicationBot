"""
FastAPI application entry point for JobApplicationBot.

This is the main app that:
- Initializes FastAPI with CORS
- Registers all API routers
- Provides health check endpoint
- Sets up database connection lifecycle
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
# Import API routers
from app.api import auth, profile, runs, jobs, tasks, approvals

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    
    On startup: Database connection is already handled by engine
    On shutdown: Close database connections gracefully
    """
    # Startup
    logger.info("🚀 Starting JobApplicationBot API...")
    logger.info(f"📊 Database: {settings.database_url.split('@')[1] if '@' in settings.database_url else 'configured'}")
    logger.info(f"🔧 Debug mode: {settings.debug}")
    
    yield
    
    # Shutdown
    logger.info("👋 Shutting down JobApplicationBot API...")
    await engine.dispose()


# Initialize FastAPI app
app = FastAPI(
    title="JobApplicationBot API",
    description="API for managing automated job applications",
    version="1.0.0",
    debug=settings.debug,
    lifespan=lifespan,
)

# Configure CORS
# In production, restrict this to your dashboard domain
# Set ALLOWED_ORIGINS environment variable with comma-separated domains
allowed_origins = [
    "http://localhost:3000",  # Local development
]

# Add production origins from environment variable
if hasattr(settings, 'allowed_origins') and settings.allowed_origins:
    allowed_origins.extend(settings.allowed_origins.split(','))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {
        "status": "healthy",
        "service": "JobApplicationBot API",
        "version": "1.0.0",
    }


# Root endpoint
@app.get("/")
async def root():
    """API root with basic info."""
    return {
        "message": "JobApplicationBot API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


# Register API routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(profile.router, prefix="/api", tags=["profile"])
app.include_router(runs.router, prefix="/api/runs", tags=["runs"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(approvals.router, prefix="/api/approvals", tags=["approvals"])
# app.include_router(testing.router, prefix="/api/_testing", tags=["testing"])
