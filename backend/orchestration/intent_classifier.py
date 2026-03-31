"""
Intent Classification Service for TradeSense Agent Routing.

This module provides intent classification using Gemini API with confidence scoring
to route user inputs to the appropriate specialized agent.

**Validates: Requirements 3.1, 3.2, 15.4**
"""

import logging
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ============================================================================
# Intent Types
# ============================================================================


class IntentType(str, Enum):
    """Supported intent types for agent routing."""
    JOB_COMPLETION = "job_completion"
    LEAD_INTAKE = "lead_intake"
    DIAGNOSIS = "diagnosis"
    PARTS_QUERY = "parts_query"
    SCHEDULING = "scheduling"
    UNKNOWN = "unknown"


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class IntentClassificationResult:
    """Result of intent classification."""
    intent: IntentType
    confidence: float  # 0.0-1.0
    parameters: Dict[str, Any]
    reasoning: str
    alternative_intents: List[tuple[IntentType, float]]  # (intent, confidence)


class IntentClassificationRequest(BaseModel):
    """Request for intent classification."""
    text: str = Field(..., description="User input text to classify")
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional conversation context"
    )
    user_role: Optional[str] = Field(
        default=None,
        description="User role (technician, customer, dispatcher)"
    )


# ============================================================================
# Intent Classifier
# ============================================================================


class IntentClassifier:
    """
    Intent classification service using Gemini API.
    
    Classifies user inputs into intent types for agent routing:
    - JOB_COMPLETION: Logging completed jobs, parts used, labor hours
    - LEAD_INTAKE: New service requests, customer information capture
    - DIAGNOSIS: Equipment troubleshooting, issue analysis
    - PARTS_QUERY: Parts availability, pricing, alternatives
    - SCHEDULING: Appointment scheduling, technician availability
    
    **Validates: Requirements 3.1, 3.2, 15.4**
    """
    
    def __init__(
        self,
        llm_client: Any,
        confidence_threshold: float = 0.6,
        enable_logging: bool = True,
    ):
        """
        Initialize intent classifier.
        
        Args:
            llm_client: LLM client for classification (Gemini/Azure OpenAI)
            confidence_threshold: Minimum confidence for routing (default: 0.6)
            enable_logging: Enable detailed logging
        """
        self.llm_client = llm_client
        self.confidence_threshold = confidence_threshold
        self.enable_logging = enable_logging
        
        # Statistics
        self.total_classifications = 0
        self.high_confidence_count = 0
        self.low_confidence_count = 0
        
        logger.info(
            f"Intent classifier initialized with confidence threshold: "
            f"{confidence_threshold}"
        )
    
    async def classify_intent(
        self,
        request: IntentClassificationRequest,
    ) -> IntentClassificationResult:
        """
        Classify user input into intent type.
        
        Uses Gemini API to analyze user input and determine the most
        appropriate intent for routing to specialized agents.
        
        **Validates: Requirement 15.4 (confidence < 0.6 → clarifying questions)**
        
        Args:
            request: Classification request with text and context
            
        Returns:
            IntentClassificationResult with intent, confidence, and parameters
        """
        self.total_classifications += 1
        
        logger.info(f"Classifying intent: {request.text[:100]}...")
        
        # Build classification prompt
        prompt = self._build_classification_prompt(request)
        
        try:
            # Use LLM for classification
            response = await self.llm_client.generate(
                prompt=prompt,
                temperature=0.2,  # Low temperature for consistent classification
                max_tokens=500,
            )
            
            # Parse response into structured result
            result = self._parse_classification_response(
                response.text,
                request.text,
            )
            
            # Track confidence statistics
            if result.confidence >= self.confidence_threshold:
                self.high_confidence_count += 1
            else:
                self.low_confidence_count += 1
            
            logger.info(
                f"Intent classified: {result.intent.value} "
                f"(confidence: {result.confidence:.2f})"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error classifying intent: {e}")
            # Return unknown intent with low confidence
            return IntentClassificationResult(
                intent=IntentType.UNKNOWN,
                confidence=0.0,
                parameters={},
                reasoning=f"Classification error: {str(e)}",
                alternative_intents=[],
            )
    
    def requires_clarification(
        self,
        result: IntentClassificationResult,
    ) -> bool:
        """
        Check if classification requires clarification.
        
        **Validates: Requirement 15.4**
        
        Args:
            result: Classification result
            
        Returns:
            True if confidence is below threshold
        """
        return result.confidence < self.confidence_threshold
    
    def generate_clarifying_question(
        self,
        result: IntentClassificationResult,
        original_text: str,
    ) -> str:
        """
        Generate clarifying question for low-confidence classifications.
        
        **Validates: Requirement 15.4**
        
        Args:
            result: Low-confidence classification result
            original_text: Original user input
            
        Returns:
            Clarifying question to ask user
        """
        if result.intent == IntentType.UNKNOWN:
            return (
                "I'm not sure I understood that correctly. "
                "Are you trying to:\n"
                "- Log a completed job?\n"
                "- Report a new service request?\n"
                "- Get help diagnosing an issue?\n"
                "- Check parts availability?\n"
                "- Schedule an appointment?"
            )
        
        # Generate specific clarification based on alternatives
        if result.alternative_intents:
            top_alternatives = result.alternative_intents[:2]
            alt_text = " or ".join([
                intent.value.replace("_", " ")
                for intent, _ in top_alternatives
            ])
            
            return (
                f"I think you're asking about {result.intent.value.replace('_', ' ')}, "
                f"but you might also mean {alt_text}. "
                f"Can you clarify which one?"
            )
        
        return (
            f"I think you're asking about {result.intent.value.replace('_', ' ')}, "
            f"but I'm not completely sure. Is that correct?"
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get classification statistics.
        
        Returns:
            Dictionary with classification metrics
        """
        return {
            "total_classifications": self.total_classifications,
            "high_confidence_count": self.high_confidence_count,
            "low_confidence_count": self.low_confidence_count,
            "high_confidence_rate": (
                self.high_confidence_count / self.total_classifications
                if self.total_classifications > 0 else 0.0
            ),
            "confidence_threshold": self.confidence_threshold,
        }
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def _build_classification_prompt(
        self,
        request: IntentClassificationRequest,
    ) -> str:
        """Build classification prompt for LLM."""
        prompt = f"""You are an expert intent classifier for a field service management system.

Classify the following user input into one of these intent types:

1. JOB_COMPLETION: User is logging a completed job, reporting parts used, labor hours, or job details
   Examples: "Log job completion", "Used thermostat TH-2000", "Job took 2 hours"

2. LEAD_INTAKE: User is reporting a new service request or customer issue
   Examples: "My AC stopped working", "Customer needs furnace repair", "New service call"

3. DIAGNOSIS: User needs help troubleshooting or diagnosing an equipment issue
   Examples: "What's wrong with this unit?", "Help diagnose", "Equipment not working properly"

4. PARTS_QUERY: User is asking about parts availability, pricing, or alternatives
   Examples: "Do we have capacitors?", "Check part availability", "Price for thermostat"

5. SCHEDULING: User is asking about appointments, technician availability, or schedule optimization
   Examples: "When can we schedule?", "Check my schedule", "Optimize routes"

User Input: "{request.text}"
"""
        
        # Add context if available
        if request.context:
            prompt += f"\nContext: {request.context}\n"
        
        if request.user_role:
            prompt += f"User Role: {request.user_role}\n"
        
        prompt += """
Respond with:
1. Primary intent (one of the 5 types above)
2. Confidence score (0.0-1.0)
3. Key parameters extracted from the input
4. Brief reasoning for your classification
5. Alternative intents if confidence is not high

Format as JSON:
{
  "intent": "job_completion",
  "confidence": 0.85,
  "parameters": {"job_id": "...", "parts": [...]},
  "reasoning": "User is reporting job completion with parts used",
  "alternatives": [
    {"intent": "parts_query", "confidence": 0.15}
  ]
}"""
        
        return prompt
    
    def _parse_classification_response(
        self,
        response_text: str,
        original_text: str,
    ) -> IntentClassificationResult:
        """Parse LLM response into IntentClassificationResult."""
        import json
        import re
        
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                
                # Parse intent
                intent_str = data.get("intent", "unknown").lower()
                intent = self._parse_intent_type(intent_str)
                
                # Parse confidence
                confidence = float(data.get("confidence", 0.5))
                confidence = max(0.0, min(1.0, confidence))
                
                # Parse parameters
                parameters = data.get("parameters", {})
                
                # Parse reasoning
                reasoning = data.get("reasoning", "")
                
                # Parse alternatives
                alternatives = []
                for alt in data.get("alternatives", []):
                    alt_intent = self._parse_intent_type(alt.get("intent", "unknown"))
                    alt_conf = float(alt.get("confidence", 0.0))
                    alternatives.append((alt_intent, alt_conf))
                
                return IntentClassificationResult(
                    intent=intent,
                    confidence=confidence,
                    parameters=parameters,
                    reasoning=reasoning,
                    alternative_intents=alternatives,
                )
        
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(f"Failed to parse classification response: {e}")
        
        # Fallback: Use keyword matching
        return self._fallback_classification(original_text)
    
    def _parse_intent_type(self, intent_str: str) -> IntentType:
        """Parse intent string into IntentType enum."""
        intent_str = intent_str.lower().replace(" ", "_").replace("-", "_")
        
        try:
            return IntentType(intent_str)
        except ValueError:
            # Try partial matching
            for intent_type in IntentType:
                if intent_type.value in intent_str or intent_str in intent_type.value:
                    return intent_type
            
            return IntentType.UNKNOWN
    
    def _fallback_classification(self, text: str) -> IntentClassificationResult:
        """Fallback classification using keyword matching."""
        text_lower = text.lower()
        
        # Job completion keywords
        job_keywords = [
            "log job", "job complete", "finished job", "parts used",
            "labor hours", "job done", "completed"
        ]
        
        # Lead intake keywords
        lead_keywords = [
            "new request", "customer", "service call", "not working",
            "broken", "stopped", "issue", "problem"
        ]
        
        # Diagnosis keywords
        diagnosis_keywords = [
            "diagnose", "troubleshoot", "what's wrong", "help with",
            "figure out", "analyze", "check"
        ]
        
        # Parts query keywords
        parts_keywords = [
            "parts", "availability", "in stock", "price", "cost",
            "order", "alternative"
        ]
        
        # Scheduling keywords
        scheduling_keywords = [
            "schedule", "appointment", "availability", "when",
            "time slot", "calendar", "route"
        ]
        
        # Check keywords
        scores = {
            IntentType.JOB_COMPLETION: sum(1 for kw in job_keywords if kw in text_lower),
            IntentType.LEAD_INTAKE: sum(1 for kw in lead_keywords if kw in text_lower),
            IntentType.DIAGNOSIS: sum(1 for kw in diagnosis_keywords if kw in text_lower),
            IntentType.PARTS_QUERY: sum(1 for kw in parts_keywords if kw in text_lower),
            IntentType.SCHEDULING: sum(1 for kw in scheduling_keywords if kw in text_lower),
        }
        
        # Find best match
        best_intent = max(scores.items(), key=lambda x: x[1])
        
        if best_intent[1] > 0:
            # Calculate confidence based on keyword matches
            confidence = min(0.7, 0.4 + (best_intent[1] * 0.1))
            
            return IntentClassificationResult(
                intent=best_intent[0],
                confidence=confidence,
                parameters={},
                reasoning=f"Keyword-based classification (fallback)",
                alternative_intents=[],
            )
        
        # No matches - return unknown
        return IntentClassificationResult(
            intent=IntentType.UNKNOWN,
            confidence=0.0,
            parameters={},
            reasoning="Unable to classify intent",
            alternative_intents=[],
        )


# ============================================================================
# Factory Function
# ============================================================================


def create_intent_classifier(
    llm_client: Any,
    confidence_threshold: float = 0.6,
) -> IntentClassifier:
    """
    Create and configure an intent classifier.
    
    Args:
        llm_client: LLM client for classification
        confidence_threshold: Minimum confidence for routing
    
    Returns:
        Configured IntentClassifier instance
    """
    return IntentClassifier(
        llm_client=llm_client,
        confidence_threshold=confidence_threshold,
    )
