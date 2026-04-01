"""
Cost Optimization Dashboard
Provides comprehensive cost reporting and optimization recommendations
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

from .cost_optimizer import get_cost_optimizer, ServiceType
from backend.voice.cost_tracker import get_speech_cost_tracker

logger = logging.getLogger(__name__)


@dataclass
class CostRecommendation:
    """Cost optimization recommendation."""
    category: str
    priority: str  # 'high', 'medium', 'low'
    description: str
    estimated_savings: float
    action_items: List[str]


class CostDashboard:
    """
    Comprehensive cost optimization dashboard.
    
    Provides:
    - Unified cost reporting across all services
    - Cost projections and forecasting
    - Optimization recommendations
    - Budget alerts and warnings
    """
    
    def __init__(self):
        """Initialize cost dashboard."""
        self.llm_optimizer = get_cost_optimizer()
        self.speech_tracker = get_speech_cost_tracker()
        
        logger.info("Cost dashboard initialized")
    
    def get_unified_cost_report(self) -> Dict[str, Any]:
        """
        Get unified cost report across all services.
        
        Returns:
            Comprehensive cost report
        """
        # Get individual summaries
        llm_summary = self.llm_optimizer.get_cost_summary()
        speech_summary = self.speech_tracker.get_cost_summary()
        
        # Calculate totals
        total_cost = llm_summary["total_cost"] + speech_summary["total_cost"]
        total_budget = (
            llm_summary["budget_stats"]["azure_openai"]["budget_limit"] +
            speech_summary["budget_limit"]
        )
        
        # Build unified report
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_cost": total_cost,
                "total_budget": total_budget,
                "budget_remaining": total_budget - total_cost,
                "budget_used_pct": (total_cost / total_budget * 100) if total_budget > 0 else 0,
            },
            "llm_services": {
                "total_cost": llm_summary["total_cost"],
                "gemini": {
                    "cost": llm_summary["costs_by_service"]["gemini"],
                    "quota_usage": llm_summary["quota_stats"]["gemini"]["daily_usage"],
                    "quota_limit": llm_summary["quota_stats"]["gemini"]["daily_limit"],
                    "quota_remaining": llm_summary["quota_stats"]["gemini"]["daily_remaining"],
                },
                "azure_openai": {
                    "cost": llm_summary["costs_by_service"]["azure_openai"],
                    "budget_used": llm_summary["budget_stats"]["azure_openai"]["current_spend"],
                    "budget_limit": llm_summary["budget_stats"]["azure_openai"]["budget_limit"],
                    "budget_remaining": llm_summary["budget_stats"]["azure_openai"]["budget_remaining"],
                },
            },
            "speech_services": {
                "total_cost": speech_summary["total_cost"],
                "stt": {
                    "cost": speech_summary["stt"]["total_cost"],
                    "hours_used": speech_summary["stt"]["total_hours"],
                    "cost_per_hour": speech_summary["stt"]["cost_per_hour"],
                },
                "tts": {
                    "cost": speech_summary["tts"]["total_cost"],
                    "characters_used": speech_summary["tts"]["total_characters"],
                    "cost_per_1m_chars": speech_summary["tts"]["cost_per_1m_chars"],
                },
                "budget_used": speech_summary["total_cost"],
                "budget_limit": speech_summary["budget_limit"],
                "budget_remaining": speech_summary["budget_remaining"],
            },
            "optimization": {
                "cache_hit_rate": llm_summary["cache_stats"]["hit_rate"],
                "cache_hits": llm_summary["cache_stats"]["hits"],
                "cache_misses": llm_summary["cache_stats"]["misses"],
                "quota_exceeded_count": llm_summary["optimization_stats"]["quota_exceeded_count"],
                "fallback_count": llm_summary["optimization_stats"]["fallback_count"],
            },
        }
        
        return report
    
    def get_cost_projection(self, days: int = 30) -> Dict[str, Any]:
        """
        Project costs for the next N days based on current usage.
        
        Args:
            days: Number of days to project
        
        Returns:
            Cost projection
        """
        llm_summary = self.llm_optimizer.get_cost_summary()
        speech_summary = self.speech_tracker.get_cost_summary()
        
        # Get current daily costs (simplified - assumes uniform usage)
        # In production, this would analyze historical trends
        current_total_cost = llm_summary["total_cost"] + speech_summary["total_cost"]
        
        # Estimate daily cost (rough approximation)
        # This assumes we've been running for at least 1 day
        daily_cost = current_total_cost  # Simplified for demo
        
        # Project future costs
        projected_cost = daily_cost * days
        
        # Calculate budget status
        total_budget = (
            llm_summary["budget_stats"]["azure_openai"]["budget_limit"] +
            speech_summary["budget_limit"]
        )
        
        projected_budget_remaining = total_budget - (current_total_cost + projected_cost)
        days_until_budget_exhausted = (
            (total_budget - current_total_cost) / daily_cost
            if daily_cost > 0 else float('inf')
        )
        
        projection = {
            "projection_period_days": days,
            "current_total_cost": current_total_cost,
            "estimated_daily_cost": daily_cost,
            "projected_cost": projected_cost,
            "projected_total_cost": current_total_cost + projected_cost,
            "total_budget": total_budget,
            "projected_budget_remaining": projected_budget_remaining,
            "days_until_budget_exhausted": days_until_budget_exhausted,
            "will_exceed_budget": projected_budget_remaining < 0,
        }
        
        return projection
    
    def get_optimization_recommendations(self) -> List[CostRecommendation]:
        """
        Get cost optimization recommendations.
        
        Returns:
            List of recommendations
        """
        recommendations = []
        
        llm_summary = self.llm_optimizer.get_cost_summary()
        speech_summary = self.speech_tracker.get_cost_summary()
        
        # Check cache hit rate
        cache_hit_rate = llm_summary["cache_stats"]["hit_rate"]
        if cache_hit_rate < 50:
            recommendations.append(CostRecommendation(
                category="caching",
                priority="high",
                description=f"Low cache hit rate ({cache_hit_rate:.1f}%). Improve caching to reduce API calls.",
                estimated_savings=llm_summary["total_cost"] * 0.3,  # Estimate 30% savings
                action_items=[
                    "Increase cache TTL for frequently accessed data",
                    "Implement request deduplication",
                    "Cache common queries and responses",
                ]
            ))
        
        # Check Gemini quota usage
        gemini_quota = llm_summary["quota_stats"]["gemini"]
        gemini_usage_pct = (gemini_quota["daily_usage"] / gemini_quota["daily_limit"]) * 100
        if gemini_usage_pct > 80:
            recommendations.append(CostRecommendation(
                category="quota_management",
                priority="high",
                description=f"Gemini quota usage at {gemini_usage_pct:.1f}%. Risk of quota exhaustion.",
                estimated_savings=0.0,  # Avoiding fallback to paid service
                action_items=[
                    "Implement more aggressive caching",
                    "Batch requests when possible",
                    "Use cheaper models for simple tasks",
                    "Distribute load across multiple API keys if available",
                ]
            ))
        
        # Check Azure OpenAI budget
        azure_budget = llm_summary["budget_stats"]["azure_openai"]
        azure_usage_pct = azure_budget["budget_used_pct"]
        if azure_usage_pct > 70:
            recommendations.append(CostRecommendation(
                category="budget_management",
                priority="high",
                description=f"Azure OpenAI budget at {azure_usage_pct:.1f}%. Approaching limit.",
                estimated_savings=azure_budget["current_spend"] * 0.2,  # Estimate 20% savings
                action_items=[
                    "Maximize Gemini free tier usage",
                    "Implement token usage optimization",
                    "Use GPT-3.5-turbo instead of GPT-4 for simple tasks",
                    "Reduce max_tokens for responses",
                ]
            ))
        
        # Check speech services budget
        speech_usage_pct = speech_summary["budget_used_pct"]
        if speech_usage_pct > 70:
            recommendations.append(CostRecommendation(
                category="speech_optimization",
                priority="medium",
                description=f"Speech services budget at {speech_usage_pct:.1f}%. Approaching limit.",
                estimated_savings=speech_summary["total_cost"] * 0.15,  # Estimate 15% savings
                action_items=[
                    "Optimize audio quality settings",
                    "Reduce unnecessary TTS synthesis",
                    "Implement audio caching for common responses",
                    "Use shorter prompts and responses",
                ]
            ))
        
        # Check fallback usage
        fallback_count = llm_summary["optimization_stats"]["fallback_count"]
        if fallback_count > 10:
            recommendations.append(CostRecommendation(
                category="fallback_reduction",
                priority="medium",
                description=f"High fallback count ({fallback_count}). Indicates quota/budget issues.",
                estimated_savings=0.0,
                action_items=[
                    "Increase Gemini quota if possible",
                    "Implement better request distribution",
                    "Add request queuing during peak times",
                ]
            ))
        
        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        recommendations.sort(key=lambda r: priority_order[r.priority])
        
        return recommendations
    
    def get_budget_alerts(self) -> List[Dict[str, Any]]:
        """
        Get active budget alerts.
        
        Returns:
            List of budget alerts
        """
        alerts = []
        
        llm_summary = self.llm_optimizer.get_cost_summary()
        speech_summary = self.speech_tracker.get_cost_summary()
        
        # Check LLM budget alerts
        for service_name, budget_info in llm_summary["budget_stats"].items():
            if budget_info["alert_sent"]:
                alerts.append({
                    "service": service_name,
                    "type": "budget_threshold",
                    "severity": "warning",
                    "message": f"{service_name} budget threshold exceeded",
                    "current_spend": budget_info["current_spend"],
                    "budget_limit": budget_info["budget_limit"],
                    "budget_used_pct": budget_info["budget_used_pct"],
                })
        
        # Check speech budget alert
        if speech_summary["alert_sent"]:
            alerts.append({
                "service": "speech_services",
                "type": "budget_threshold",
                "severity": "warning",
                "message": "Speech services budget threshold exceeded",
                "current_spend": speech_summary["total_cost"],
                "budget_limit": speech_summary["budget_limit"],
                "budget_used_pct": speech_summary["budget_used_pct"],
            })
        
        # Check quota alerts
        for service_name, quota_info in llm_summary["quota_stats"].items():
            usage_pct = (quota_info["daily_usage"] / quota_info["daily_limit"]) * 100
            if usage_pct > 90:
                alerts.append({
                    "service": service_name,
                    "type": "quota_threshold",
                    "severity": "critical" if usage_pct > 95 else "warning",
                    "message": f"{service_name} quota nearly exhausted",
                    "current_usage": quota_info["daily_usage"],
                    "quota_limit": quota_info["daily_limit"],
                    "usage_pct": usage_pct,
                })
        
        return alerts
    
    def get_cost_breakdown_by_operation(self) -> Dict[str, Any]:
        """
        Get cost breakdown by operation type.
        
        Returns:
            Cost breakdown
        """
        cost_records = self.llm_optimizer.get_cost_records()
        
        # Group by service and operation
        breakdown = {}
        for record in cost_records:
            service_key = record.service.value
            operation_key = record.operation
            
            if service_key not in breakdown:
                breakdown[service_key] = {}
            
            if operation_key not in breakdown[service_key]:
                breakdown[service_key][operation_key] = {
                    "count": 0,
                    "total_cost": 0.0,
                    "total_tokens": 0,
                }
            
            breakdown[service_key][operation_key]["count"] += 1
            breakdown[service_key][operation_key]["total_cost"] += record.cost
            breakdown[service_key][operation_key]["total_tokens"] += record.tokens_used
        
        return breakdown
    
    def export_cost_report(self, format: str = "json") -> str:
        """
        Export cost report in specified format.
        
        Args:
            format: Export format ('json', 'csv', 'markdown')
        
        Returns:
            Formatted report string
        """
        report = self.get_unified_cost_report()
        
        if format == "json":
            import json
            return json.dumps(report, indent=2)
        
        elif format == "markdown":
            md = "# Cost Optimization Report\n\n"
            md += f"**Generated:** {report['timestamp']}\n\n"
            
            md += "## Summary\n\n"
            md += f"- **Total Cost:** ${report['summary']['total_cost']:.2f}\n"
            md += f"- **Total Budget:** ${report['summary']['total_budget']:.2f}\n"
            md += f"- **Budget Remaining:** ${report['summary']['budget_remaining']:.2f}\n"
            md += f"- **Budget Used:** {report['summary']['budget_used_pct']:.1f}%\n\n"
            
            md += "## LLM Services\n\n"
            md += f"- **Gemini (Free Tier):** ${report['llm_services']['gemini']['cost']:.2f}\n"
            md += f"  - Quota: {report['llm_services']['gemini']['quota_usage']}/{report['llm_services']['gemini']['quota_limit']}\n"
            md += f"- **Azure OpenAI:** ${report['llm_services']['azure_openai']['cost']:.2f}\n"
            md += f"  - Budget: ${report['llm_services']['azure_openai']['budget_used']:.2f}/${report['llm_services']['azure_openai']['budget_limit']:.2f}\n\n"
            
            md += "## Speech Services\n\n"
            md += f"- **STT:** ${report['speech_services']['stt']['cost']:.2f} ({report['speech_services']['stt']['hours_used']:.2f} hours)\n"
            md += f"- **TTS:** ${report['speech_services']['tts']['cost']:.2f} ({report['speech_services']['tts']['characters_used']:,} chars)\n\n"
            
            md += "## Optimization\n\n"
            md += f"- **Cache Hit Rate:** {report['optimization']['cache_hit_rate']:.1f}%\n"
            md += f"- **Fallback Count:** {report['optimization']['fallback_count']}\n"
            
            return md
        
        else:
            raise ValueError(f"Unsupported format: {format}")


# Global dashboard instance
_cost_dashboard: Optional[CostDashboard] = None


def get_cost_dashboard() -> CostDashboard:
    """
    Get global cost dashboard instance.
    
    Returns:
        CostDashboard instance
    """
    global _cost_dashboard
    if _cost_dashboard is None:
        _cost_dashboard = CostDashboard()
    return _cost_dashboard
