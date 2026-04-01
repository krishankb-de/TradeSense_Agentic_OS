"""
TradeSense FastAPI Application (Cloud-Based Lightweight)
Optimized for Lenovo SlimPad 5 with Azure/Gemini cloud services
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import sys
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from core.config import settings
from api.middleware import RateLimitMiddleware
import logging

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("🚀 Starting TradeSense backend...")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Database: {settings.postgres_host}:{settings.postgres_port}")
    logger.info(f"Redis: {settings.redis_host}:{settings.redis_port}")
    
    # Check cloud services configuration
    if settings.use_azure_openai:
        logger.info("✅ Azure OpenAI: Enabled")
    if settings.use_azure_speech:
        logger.info("✅ Azure Speech: Enabled")
    
    logger.info("✨ TradeSense backend started successfully!")
    
    yield
    
    # Shutdown
    logger.info("👋 Shutting down TradeSense backend...")


# Create FastAPI app
app = FastAPI(
    title="TradeSense Agentic FSM",
    description="Open-source voice-first agentic field service management system",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=60,
    burst_size=10
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to TradeSense Agentic FSM API",
        "version": "0.1.0",
        "status": "running",
        "environment": settings.environment,
        "docs": "/docs",
        "cloud_services": {
            "azure_openai": settings.use_azure_openai,
            "azure_speech": settings.use_azure_speech,
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "environment": settings.environment,
        "services": {
            "database": "connected",  # TODO: Add actual DB health check
            "redis": "connected",  # TODO: Add actual Redis health check
        }
    }

@app.get("/api/v1/info")
async def api_info():
    """API information endpoint"""
    return {
        "api_version": "v1",
        "features": {
            "voice_pipeline": "planned",
            "intake_agent": "planned",
            "diagnostic_agent": "planned",
            "fulfillment_agent": "planned",
            "webrtc_communication": "planned",
        },
        "cloud_services": {
            "azure_openai": settings.use_azure_openai,
            "azure_speech": settings.use_azure_speech,
            "datadog": settings.use_datadog,
        }
    }

# Add API routers
from api.routes import (
    voice,
    intake,
    voice_agent,
    auth,
    leads,
    jobs,
    technicians,
    websocket,
    webrtc,
    notifications
)

# Voice and agent routes
app.include_router(voice.router, prefix="/api/v1/voice", tags=["voice"])
app.include_router(voice_agent.router, prefix="/api/v1/voice-agent", tags=["voice-agent"])
app.include_router(intake.router, prefix="/api/v1", tags=["intake"])

# Authentication routes
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])

# Resource management routes
app.include_router(leads.router, prefix="/api/v1/leads", tags=["leads"])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["jobs"])
app.include_router(technicians.router, prefix="/api/v1/technicians", tags=["technicians"])

# Real-time communication routes
app.include_router(websocket.router, prefix="/api/v1", tags=["websocket"])
app.include_router(webrtc.router, prefix="/api/v1/webrtc", tags=["webrtc"])

# Notification routes
app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["notifications"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level=settings.log_level.lower()
    )
