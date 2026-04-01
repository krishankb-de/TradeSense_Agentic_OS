"""
Cost Optimization API Routes
Provides endpoints for cost tracking, reporting, and optimization
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging

from backend.llm.cost_dashboard import get_cost_dashboard
from backend.llm.cost_optimizer import get_cost_optimizer
from backend.voice.cost_tracker import get_speech_cost_tracker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cost", tags=["cost-optimization"])


@router.get("/report")
async def get_cost_report():
    """
    Get unified cost report across all services.
    
    Returns comprehensive cost information including:
    - Total costs and budget status
    - LLM service costs (Gemini, Azure OpenAI)
    - Speech service costs (STT, TTS)
    - Optimization metrics (cache hit rate, fallback count)
    """
    try:
        dashboard = get_cost_dashboard()
        report = dashboard.get_unified_cost_report()
        return report
    except Exception as e:
        logger.error(f"Error generating cost report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projection")
async def get_cost_projection(
    days: int = Query(default=30, ge=1, le=365, description="Number of days to project")
):
    """
    Get cost projection for the next N days.
    
    Args:
        days: Number of days to project (1-365)
    
    Returns cost projection including:
    - Estimated daily cost
    - Projected total cost
    - Budget remaining
    - Days until budget exhausted
    """
    try:
        dashboard = get_cost_dashboard()
        projection = dashboard.get_cost_projection(days=days)
        return projection
    except Exception as e:
        logger.error(f"Error generating cost projection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommendations")
async def get_optimization_recommendations():
    """
    Get cost optimization recommendations.
    
    Returns prioritized list of recommendations including:
    - Category (caching, quota_management, budget_management, etc.)
    - Priority (high, medium, low)
    - Description
    - Estimated savings
    - Action items
    """
    try:
        dashboard = get_cost_dashboard()
        recommendations = dashboard.get_optimization_recommendations()
        
        # Convert dataclass to dict
        return [
            {
                "category": rec.category,
                "priority": rec.priority,
                "description": rec.description,
                "estimated_savings": rec.estimated_savings,
                "action_items": rec.action_items,
            }
            for rec in recommendations
        ]
    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts")
async def get_budget_alerts():
    """
    Get active budget and quota alerts.
    
    Returns list of alerts including:
    - Service name
    - Alert type (budget_threshold, quota_threshold)
    - Severity (warning, critical)
    - Current usage and limits
    """
    try:
        dashboard = get_cost_dashboard()
        alerts = dashboard.get_budget_alerts()
        return {"alerts": alerts, "count": len(alerts)}
    except Exception as e:
        logger.error(f"Error getting budget alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/breakdown")
async def get_cost_breakdown():
    """
    Get cost breakdown by operation type.
    
    Returns detailed breakdown of costs by:
    - Service (gemini, azure_openai, etc.)
    - Operation (generate, embed, etc.)
    - Count, total cost, total tokens
    """
    try:
        dashboard = get_cost_dashboard()
        breakdown = dashboard.get_cost_breakdown_by_operation()
        return breakdown
    except Exception as e:
        logger.error(f"Error generating cost breakdown: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export")
async def export_cost_report(
    format: str = Query(default="json", regex="^(json|markdown)$", description="Export format")
):
    """
    Export cost report in specified format.
    
    Args:
        format: Export format (json or markdown)
    
    Returns formatted cost report
    """
    try:
        dashboard = get_cost_dashboard()
        report = dashboard.export_cost_report(format=format)
        
        if format == "markdown":
            return {"content": report, "content_type": "text/markdown"}
        else:
            return {"content": report, "content_type": "application/json"}
    except Exception as e:
        logger.error(f"Error exporting cost report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cache/stats")
async def get_cache_stats():
    """
    Get cache statistics.
    
    Returns:
    - Cache hits and misses
    - Cache hit rate
    - Cache size
    """
    try:
        optimizer = get_cost_optimizer()
        summary = optimizer.get_cost_summary()
        return summary["cache_stats"]
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cache/clear")
async def clear_cache():
    """
    Clear the response cache.
    
    This will force all subsequent requests to hit the API,
    which may increase costs but ensures fresh data.
    """
    try:
        optimizer = get_cost_optimizer()
        optimizer.clear_cache()
        return {"message": "Cache cleared successfully"}
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quota/status")
async def get_quota_status():
    """
    Get quota status for all services.
    
    Returns:
    - Daily usage and limits
    - Per-minute usage and limits
    - Remaining quota
    """
    try:
        optimizer = get_cost_optimizer()
        summary = optimizer.get_cost_summary()
        return summary["quota_stats"]
    except Exception as e:
        logger.error(f"Error getting quota status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/budget/status")
async def get_budget_status():
    """
    Get budget status for all services.
    
    Returns:
    - Current spend
    - Budget limits
    - Budget remaining
    - Budget used percentage
    - Alert status
    """
    try:
        optimizer = get_cost_optimizer()
        summary = optimizer.get_cost_summary()
        return summary["budget_stats"]
    except Exception as e:
        logger.error(f"Error getting budget status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/budget/reset-alerts")
async def reset_budget_alerts():
    """
    Reset budget alert flags.
    
    This allows alerts to be sent again when thresholds are exceeded.
    """
    try:
        optimizer = get_cost_optimizer()
        optimizer.reset_budget_alerts()
        
        speech_tracker = get_speech_cost_tracker()
        speech_tracker.reset_budget_alert()
        
        return {"message": "Budget alerts reset successfully"}
    except Exception as e:
        logger.error(f"Error resetting budget alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/speech/summary")
async def get_speech_cost_summary():
    """
    Get speech services cost summary.
    
    Returns:
    - STT usage and costs
    - TTS usage and costs
    - Total costs
    - Budget status
    """
    try:
        speech_tracker = get_speech_cost_tracker()
        summary = speech_tracker.get_cost_summary()
        return summary
    except Exception as e:
        logger.error(f"Error getting speech cost summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))
