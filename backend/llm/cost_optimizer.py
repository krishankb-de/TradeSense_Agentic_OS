"""
Cloud Cost Optimization Module
Implements intelligent caching, quota management, and cost tracking
for cloud-based AI services (Gemini, Azure OpenAI, Azure Speech)
"""

import time
import logging
import hashlib
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json

logger = logging.getLogger(__name__)


class ServiceType(Enum):
    """Cloud service types."""
    GEMINI = "gemini"
    AZURE_OPENAI = "azure_openai"
    AZURE_SPEECH_STT = "azure_speech_stt"
    AZURE_SPEECH_TTS = "azure_speech_tts"
    TWILIO = "twilio"


@dataclass
class QuotaLimit:
    """Quota limit configuration."""
    service: ServiceType
    daily_limit: int
    minute_limit: int
    current_daily_usage: int = 0
    current_minute_usage: int = 0
    last_reset_time: datetime = field(default_factory=datetime.now)
    last_minute_reset: datetime = field(default_factory=datetime.now)


@dataclass
class CostRecord:
    """Cost tracking record."""
    timestamp: datetime
    service: ServiceType
    operation: str
    cost: float
    tokens_used: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BudgetAlert:
    """Budget alert configuration."""
    service: ServiceType
    budget_limit: float
    alert_threshold: float  # 0.0-1.0
    current_spend: float = 0.0
    alert_sent: bool = False


class CostOptimizer:
    """
    Centralized cost optimization for cloud AI services.
    
    Features:
    - Intelligent response caching
    - Quota management and tracking
    - Cost tracking and budgeting
    - Fallback routing when quotas exceeded
    - Budget alerts
    """
    
    def __init__(
        self,
        cache_ttl: int = 3600,  # 1 hour default
        enable_caching: bool = True,
        gemini_daily_limit: int = 1500,
        azure_budget: float = 100.0,
        azure_alert_threshold: float = 0.8,
    ):
        """
        Initialize cost optimizer.
        
        Args:
            cache_ttl: Cache time-to-live in seconds
            enable_caching: Enable response caching
            gemini_daily_limit: Gemini free tier daily limit
            azure_budget: Azure student credit budget
            azure_alert_threshold: Budget alert threshold (0.0-1.0)
        """
        self.cache_ttl = cache_ttl
        self.enable_caching = enable_caching
        
        # Response cache: {cache_key: (response, timestamp)}
        self.response_cache: Dict[str, Tuple[Any, datetime]] = {}
        
        # Quota tracking
        self.quotas: Dict[ServiceType, QuotaLimit] = {
            ServiceType.GEMINI: QuotaLimit(
                service=ServiceType.GEMINI,
                daily_limit=gemini_daily_limit,
                minute_limit=60  # 60 RPM for free tier
            ),
            ServiceType.AZURE_OPENAI: QuotaLimit(
                service=ServiceType.AZURE_OPENAI,
                daily_limit=10000,  # High limit, controlled by budget
                minute_limit=300  # 300 RPM typical
            ),
            ServiceType.AZURE_SPEECH_STT: QuotaLimit(
                service=ServiceType.AZURE_SPEECH_STT,
                daily_limit=10000,
                minute_limit=100
            ),
            ServiceType.AZURE_SPEECH_TTS: QuotaLimit(
                service=ServiceType.AZURE_SPEECH_TTS,
                daily_limit=10000,
                minute_limit=100
            ),
        }
        
        # Cost tracking
        self.cost_records: List[CostRecord] = []
        self.total_costs: Dict[ServiceType, float] = {
            service: 0.0 for service in ServiceType
        }
        
        # Budget alerts
        self.budget_alerts: Dict[ServiceType, BudgetAlert] = {
            ServiceType.AZURE_OPENAI: BudgetAlert(
                service=ServiceType.AZURE_OPENAI,
                budget_limit=azure_budget,
                alert_threshold=azure_alert_threshold
            ),
            ServiceType.AZURE_SPEECH_STT: BudgetAlert(
                service=ServiceType.AZURE_SPEECH_STT,
                budget_limit=azure_budget / 2,  # Share budget
                alert_threshold=azure_alert_threshold
            ),
            ServiceType.AZURE_SPEECH_TTS: BudgetAlert(
                service=ServiceType.AZURE_SPEECH_TTS,
                budget_limit=azure_budget / 2,
                alert_threshold=azure_alert_threshold
            ),
        }
        
        # Statistics
        self.cache_hits = 0
        self.cache_misses = 0
        self.quota_exceeded_count = 0
        self.fallback_count = 0
        
        logger.info(
            f"Cost optimizer initialized: caching={enable_caching}, "
            f"cache_ttl={cache_ttl}s, gemini_limit={gemini_daily_limit}/day"
        )
    
    def _generate_cache_key(self, service: ServiceType, operation: str, **params) -> str:
        """
        Generate cache key from service, operation, and parameters.
        
        Args:
            service: Service type
            operation: Operation name
            **params: Operation parameters
        
        Returns:
            Cache key string
        """
        # Create deterministic key from parameters
        param_str = json.dumps(params, sort_keys=True)
        param_hash = hashlib.md5(param_str.encode()).hexdigest()
        return f"{service.value}:{operation}:{param_hash}"
    
    def get_cached_response(
        self,
        service: ServiceType,
        operation: str,
        **params
    ) -> Optional[Any]:
        """
        Get cached response if available and not expired.
        
        Args:
            service: Service type
            operation: Operation name
            **params: Operation parameters
        
        Returns:
            Cached response or None
        """
        if not self.enable_caching:
            return None
        
        cache_key = self._generate_cache_key(service, operation, **params)
        
        if cache_key in self.response_cache:
            response, timestamp = self.response_cache[cache_key]
            age = (datetime.now() - timestamp).total_seconds()
            
            if age < self.cache_ttl:
                self.cache_hits += 1
                logger.debug(f"Cache hit for {service.value}:{operation}")
                return response
            else:
                # Expired, remove from cache
                del self.response_cache[cache_key]
                logger.debug(f"Cache expired for {service.value}:{operation}")
        
        self.cache_misses += 1
        return None
    
    def cache_response(
        self,
        service: ServiceType,
        operation: str,
        response: Any,
        **params
    ):
        """
        Cache a response.
        
        Args:
            service: Service type
            operation: Operation name
            response: Response to cache
            **params: Operation parameters
        """
        if not self.enable_caching:
            return
        
        cache_key = self._generate_cache_key(service, operation, **params)
        self.response_cache[cache_key] = (response, datetime.now())
        logger.debug(f"Cached response for {service.value}:{operation}")
    
    def check_quota(self, service: ServiceType) -> Tuple[bool, str]:
        """
        Check if service is within quota limits.
        
        Args:
            service: Service type
        
        Returns:
            Tuple of (within_quota, reason)
        """
        if service not in self.quotas:
            return True, "No quota limits configured"
        
        quota = self.quotas[service]
        now = datetime.now()
        
        # Reset daily counter if needed
        if (now - quota.last_reset_time) > timedelta(days=1):
            quota.current_daily_usage = 0
            quota.last_reset_time = now
            logger.info(f"Daily quota reset for {service.value}")
        
        # Reset minute counter if needed
        if (now - quota.last_minute_reset) > timedelta(minutes=1):
            quota.current_minute_usage = 0
            quota.last_minute_reset = now
        
        # Check limits
        if quota.current_daily_usage >= quota.daily_limit:
            self.quota_exceeded_count += 1
            return False, f"Daily limit exceeded: {quota.current_daily_usage}/{quota.daily_limit}"
        
        if quota.current_minute_usage >= quota.minute_limit:
            self.quota_exceeded_count += 1
            return False, f"Per-minute limit exceeded: {quota.current_minute_usage}/{quota.minute_limit}"
        
        return True, "Within quota"
    
    def increment_quota(self, service: ServiceType):
        """
        Increment quota usage for a service.
        
        Args:
            service: Service type
        """
        if service in self.quotas:
            quota = self.quotas[service]
            quota.current_daily_usage += 1
            quota.current_minute_usage += 1
            logger.debug(
                f"Quota incremented for {service.value}: "
                f"daily={quota.current_daily_usage}/{quota.daily_limit}, "
                f"minute={quota.current_minute_usage}/{quota.minute_limit}"
            )
    
    def check_budget(self, service: ServiceType, estimated_cost: float) -> Tuple[bool, str]:
        """
        Check if service is within budget.
        
        Args:
            service: Service type
            estimated_cost: Estimated cost of operation
        
        Returns:
            Tuple of (within_budget, reason)
        """
        if service not in self.budget_alerts:
            return True, "No budget limits configured"
        
        alert = self.budget_alerts[service]
        projected_spend = alert.current_spend + estimated_cost
        
        if projected_spend > alert.budget_limit:
            return False, f"Budget exceeded: ${projected_spend:.2f} > ${alert.budget_limit:.2f}"
        
        # Check for budget alert
        if not alert.alert_sent:
            budget_used_pct = projected_spend / alert.budget_limit
            if budget_used_pct >= alert.alert_threshold:
                alert.alert_sent = True
                logger.warning(
                    f"Budget alert for {service.value}: {budget_used_pct*100:.1f}% used "
                    f"(${projected_spend:.2f}/${alert.budget_limit:.2f})"
                )
        
        return True, "Within budget"
    
    def record_cost(
        self,
        service: ServiceType,
        operation: str,
        cost: float,
        tokens_used: int = 0,
        **metadata
    ):
        """
        Record cost for an operation.
        
        Args:
            service: Service type
            operation: Operation name
            cost: Cost in USD
            tokens_used: Number of tokens used
            **metadata: Additional metadata
        """
        record = CostRecord(
            timestamp=datetime.now(),
            service=service,
            operation=operation,
            cost=cost,
            tokens_used=tokens_used,
            metadata=metadata
        )
        
        self.cost_records.append(record)
        self.total_costs[service] += cost
        
        # Update budget alert
        if service in self.budget_alerts:
            self.budget_alerts[service].current_spend += cost
        
        logger.info(
            f"Cost recorded: {service.value}:{operation} = ${cost:.4f}, "
            f"total={self.total_costs[service]:.2f}"
        )
    
    def get_fallback_service(self, service: ServiceType) -> Optional[ServiceType]:
        """
        Get fallback service when primary service quota/budget exceeded.
        
        Args:
            service: Primary service
        
        Returns:
            Fallback service or None
        """
        # Routing strategy: Gemini (free) → Azure OpenAI (student credits)
        if service == ServiceType.GEMINI:
            self.fallback_count += 1
            logger.info("Falling back from Gemini to Azure OpenAI")
            return ServiceType.AZURE_OPENAI
        
        # No fallback available
        return None
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive cost summary.
        
        Returns:
            Dictionary with cost information
        """
        total_cost = sum(self.total_costs.values())
        
        summary = {
            "total_cost": total_cost,
            "costs_by_service": {
                service.value: cost
                for service, cost in self.total_costs.items()
            },
            "cache_stats": {
                "hits": self.cache_hits,
                "misses": self.cache_misses,
                "hit_rate": (
                    self.cache_hits / (self.cache_hits + self.cache_misses) * 100
                    if (self.cache_hits + self.cache_misses) > 0 else 0
                ),
                "cache_size": len(self.response_cache),
            },
            "quota_stats": {
                service.value: {
                    "daily_usage": quota.current_daily_usage,
                    "daily_limit": quota.daily_limit,
                    "daily_remaining": quota.daily_limit - quota.current_daily_usage,
                    "minute_usage": quota.current_minute_usage,
                    "minute_limit": quota.minute_limit,
                }
                for service, quota in self.quotas.items()
            },
            "budget_stats": {
                service.value: {
                    "current_spend": alert.current_spend,
                    "budget_limit": alert.budget_limit,
                    "budget_remaining": alert.budget_limit - alert.current_spend,
                    "budget_used_pct": (alert.current_spend / alert.budget_limit * 100),
                    "alert_sent": alert.alert_sent,
                }
                for service, alert in self.budget_alerts.items()
            },
            "optimization_stats": {
                "quota_exceeded_count": self.quota_exceeded_count,
                "fallback_count": self.fallback_count,
            },
        }
        
        return summary
    
    def get_cost_records(
        self,
        service: Optional[ServiceType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[CostRecord]:
        """
        Get cost records with optional filtering.
        
        Args:
            service: Filter by service type
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Maximum number of records
        
        Returns:
            List of cost records
        """
        records = self.cost_records
        
        if service:
            records = [r for r in records if r.service == service]
        
        if start_time:
            records = [r for r in records if r.timestamp >= start_time]
        
        if end_time:
            records = [r for r in records if r.timestamp <= end_time]
        
        if limit:
            records = records[-limit:]
        
        return records
    
    def clear_cache(self):
        """Clear the response cache."""
        self.response_cache.clear()
        logger.info("Response cache cleared")
    
    def reset_budget_alerts(self):
        """Reset all budget alert flags."""
        for alert in self.budget_alerts.values():
            alert.alert_sent = False
        logger.info("Budget alert flags reset")


# Global cost optimizer instance
_cost_optimizer: Optional[CostOptimizer] = None


def get_cost_optimizer() -> CostOptimizer:
    """
    Get global cost optimizer instance.
    
    Returns:
        CostOptimizer instance
    """
    global _cost_optimizer
    if _cost_optimizer is None:
        _cost_optimizer = CostOptimizer()
    return _cost_optimizer


def initialize_cost_optimizer(**kwargs) -> CostOptimizer:
    """
    Initialize global cost optimizer with custom configuration.
    
    Args:
        **kwargs: Configuration parameters
    
    Returns:
        CostOptimizer instance
    """
    global _cost_optimizer
    _cost_optimizer = CostOptimizer(**kwargs)
    return _cost_optimizer
