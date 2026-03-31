"""
TradeSense FastAPI Application (Cloud-Based Lightweight)
Optimized for Lenovo SlimPad 5 with Azure/Gemini cloud services
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from core.config import settings
import logging

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="TradeSense Agentic FSM",
    description="Open-source voice-first agentic field service management system",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
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

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("👋 Shutting down TradeSense backend...")

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
from api.routes import voice, intake

app.include_router(voice.router, prefix="/api/v1/voice", tags=["voice"])
app.include_router(intake.router, prefix="/api/v1", tags=["intake"])

# TODO: Add more routers as they are implemented
# from api.routes import agents, jobs, inventory
# app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])
# app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["jobs"])
# app.include_router(inventory.router, prefix="/api/v1/inventory", tags=["inventory"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level=settings.log_level.lower()
    )
