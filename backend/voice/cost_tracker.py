"""
Azure Speech Services Cost Tracker
Tracks STT and TTS usage and costs for budget management
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class SpeechUsageRecord:
    """Speech service usage record."""
    timestamp: datetime
    service: str  # 'stt' or 'tts'
    duration_seconds: float = 0.0
    characters: int = 0
    cost: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class SpeechCostTracker:
    """
    Track Azure Speech Services usage and costs.
    
    Pricing (as of 2024):
    - STT Standard: $1.00 per audio hour
    - TTS Neural: $16.00 per 1M characters
    """
    
    # Pricing per unit
    STT_COST_PER_HOUR = 1.00  # $1 per audio hour
    TTS_COST_PER_1M_CHARS = 16.00  # $16 per 1M characters
    
    def __init__(
        self,
        budget_limit: float = 50.0,  # $50 budget for speech services
        alert_threshold: float = 0.8,
    ):
        """
        Initialize speech cost tracker.
        
        Args:
            budget_limit: Maximum budget in USD
            alert_threshold: Budget alert threshold (0.0-1.0)
        """
        self.budget_limit = budget_limit
        self.alert_threshold = alert_threshold
        
        # Usage tracking
        self.stt_total_seconds = 0.0
        self.tts_total_characters = 0
        
        # Cost tracking
        self.stt_total_cost = 0.0
        self.tts_total_cost = 0.0
        
        # Records
        self.usage_records = []
        
        # Alerts
        self.budget_alert_sent = False
        
        logger.info(
            f"Speech cost tracker initialized: budget=${budget_limit:.2f}, "
            f"alert_threshold={alert_threshold*100:.0f}%"
        )
    
    def record_stt_usage(
        self,
        duration_seconds: float,
        **metadata
    ) -> float:
        """
        Record STT usage and calculate cost.
        
        Args:
            duration_seconds: Audio duration in seconds
            **metadata: Additional metadata
        
        Returns:
            Cost in USD
        """
        # Calculate cost
        duration_hours = duration_seconds / 3600.0
        cost = duration_hours * self.STT_COST_PER_HOUR
        
        # Update totals
        self.stt_total_seconds += duration_seconds
        self.stt_total_cost += cost
        
        # Create record
        record = SpeechUsageRecord(
            timestamp=datetime.now(),
            service="stt",
            duration_seconds=duration_seconds,
            cost=cost,
            metadata=metadata
        )
        self.usage_records.append(record)
        
        # Check budget
        self._check_budget()
        
        logger.info(
            f"STT usage recorded: {duration_seconds:.2f}s, cost=${cost:.4f}, "
            f"total=${self.stt_total_cost:.2f}"
        )
        
        return cost
    
    def record_tts_usage(
        self,
        characters: int,
        **metadata
    ) -> float:
        """
        Record TTS usage and calculate cost.
        
        Args:
            characters: Number of characters synthesized
            **metadata: Additional metadata
        
        Returns:
            Cost in USD
        """
        # Calculate cost
        cost = (characters / 1_000_000) * self.TTS_COST_PER_1M_CHARS
        
        # Update totals
        self.tts_total_characters += characters
        self.tts_total_cost += cost
        
        # Create record
        record = SpeechUsageRecord(
            timestamp=datetime.now(),
            service="tts",
            characters=characters,
            cost=cost,
            metadata=metadata
        )
        self.usage_records.append(record)
        
        # Check budget
        self._check_budget()
        
        logger.info(
            f"TTS usage recorded: {characters} chars, cost=${cost:.4f}, "
            f"total=${self.tts_total_cost:.2f}"
        )
        
        return cost
    
    def _check_budget(self):
        """Check budget and send alert if threshold exceeded."""
        total_cost = self.stt_total_cost + self.tts_total_cost
        
        if not self.budget_alert_sent:
            budget_used_pct = total_cost / self.budget_limit
            if budget_used_pct >= self.alert_threshold:
                self.budget_alert_sent = True
                logger.warning(
                    f"Speech services budget alert: {budget_used_pct*100:.1f}% used "
                    f"(${total_cost:.2f}/${self.budget_limit:.2f})"
                )
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """
        Get cost summary.
        
        Returns:
            Dictionary with cost information
        """
        total_cost = self.stt_total_cost + self.tts_total_cost
        
        return {
            "total_cost": total_cost,
            "budget_limit": self.budget_limit,
            "budget_remaining": self.budget_limit - total_cost,
            "budget_used_pct": (total_cost / self.budget_limit) * 100,
            "stt": {
                "total_seconds": self.stt_total_seconds,
                "total_hours": self.stt_total_seconds / 3600.0,
                "total_cost": self.stt_total_cost,
                "cost_per_hour": self.STT_COST_PER_HOUR,
            },
            "tts": {
                "total_characters": self.tts_total_characters,
                "total_cost": self.tts_total_cost,
                "cost_per_1m_chars": self.TTS_COST_PER_1M_CHARS,
            },
            "alert_sent": self.budget_alert_sent,
        }
    
    def reset_budget_alert(self):
        """Reset budget alert flag."""
        self.budget_alert_sent = False
        logger.info("Speech services budget alert flag reset")


# Global speech cost tracker instance
_speech_cost_tracker: Optional[SpeechCostTracker] = None


def get_speech_cost_tracker() -> SpeechCostTracker:
    """
    Get global speech cost tracker instance.
    
    Returns:
        SpeechCostTracker instance
    """
    global _speech_cost_tracker
    if _speech_cost_tracker is None:
        _speech_cost_tracker = SpeechCostTracker()
    return _speech_cost_tracker


def initialize_speech_cost_tracker(**kwargs) -> SpeechCostTracker:
    """
    Initialize global speech cost tracker with custom configuration.
    
    Args:
        **kwargs: Configuration parameters
    
    Returns:
        SpeechCostTracker instance
    """
    global _speech_cost_tracker
    _speech_cost_tracker = SpeechCostTracker(**kwargs)
    return _speech_cost_tracker
