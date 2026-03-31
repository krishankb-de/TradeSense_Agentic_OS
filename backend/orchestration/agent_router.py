"""
Agent Routing Logic for TradeSense Multi-Agent System.

This module provides intelligent routing of user requests to specialized agents
based on intent classification, agent capabilities, and conversation context.

**Validates: Requirements 3.1, 3.2, 15.4**
"""

import logging
from typing import Dict, Any, Optional, List, Protocol
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from .intent_classifier import IntentType, IntentClassificationResult

logger = logging.getLogger(__name__)


# ============================================================================
# Agent Protocol
# ============================================================================


class Agent(Protocol):
    """Protocol for specialized agents."""
    
    @property
    def agent_type(self) -> str:
        """Agent type identifier."""
        ...
    
    @property
    def capabilities(self) -> List[str]:
        """List of agent capabilities."""
        ...
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process input and return result."""
        ...


# ============================================================================
# Routing Models
# ============================================================================


class AgentType(str, Enum):
    """Specialized agent types."""
    INTAKE = "intake"
    DIAGNOSTIC = "diagnostic"
    FULFILLMENT = "fulfillment"
    FALLBACK = "fallback"


@dataclass
class RoutingDecision:
    """Result of agent routing decision."""
    agent_type: AgentType
    intent: IntentType
    confidence: float
    reasoning: str
    requires_clarification: bool
    clarifying_question: Optional[str]
    timestamp: datetime
    context: Dict[str, Any]


@dataclass
class RoutingRule:
    """Rule for intent-to-agent mapping."""
    intent: IntentType
    agent_type: AgentType
    required_capabilities: List[str]
    priority: int  # Higher priority rules are checked first


# ============================================================================
# Agent Router
# ============================================================================


class AgentRouter:
    """
    Agent routing service for multi-agent orchestration.
    
    Routes user requests to specialized agents based on:
    - Intent classification results
    - Agent capability matching
    - Conversation context
    - Confidence thresholds
    
    Intent-to-Agent Mapping:
    - LEAD_INTAKE → IntakeAgent
    - DIAGNOSIS → DiagnosticAgent
    - JOB_COMPLETION → FulfillmentAgent
    - SCHEDULING → FulfillmentAgent
    - PARTS_QUERY → DiagnosticAgent (with inventory focus)
    
    **Validates: Requirements 3.1, 3.2, 15.4**
    """
    
    def __init__(
        self,
        intent_classifier: Any,
        audit_logger: Optional[Any] = None,
        confidence_threshold: float = 0.6,
    ):
        """
        Initialize agent router.
        
        Args:
            intent_classifier: Intent classification service
            audit_logger: Optional audit trail logger
            confidence_threshold: Minimum confidence for routing
        """
        self.intent_classifier = intent_classifier
        self.audit_logger = audit_logger
        self.confidence_threshold = confidence_threshold
        
        # Registered agents
        self.agents: Dict[AgentType, Agent] = {}
        
        # Routing rules (intent → agent mapping)
        self.routing_rules = self._initialize_routing_rules()
        
        # Statistics
        self.total_routes = 0
        self.successful_routes = 0
        self.clarification_requests = 0
        
        logger.info("Agent router initialized")
    
    def register_agent(self, agent_type: AgentType, agent: Agent) -> None:
        """
        Register a specialized agent.
        
        Args:
            agent_type: Type of agent
            agent: Agent instance
        """
        self.agents[agent_type] = agent
        logger.info(f"Registered agent: {agent_type.value}")
    
    async def route_request(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None,
        user_role: Optional[str] = None,
    ) -> RoutingDecision:
        """
        Route user request to appropriate agent.
        
        Process:
        1. Classify intent using intent classifier
        2. Check confidence threshold
        3. Match intent to agent using routing rules
        4. Verify agent capabilities
        5. Log routing decision to audit trail
        6. Return routing decision
        
        **Validates: Requirements 3.1, 3.2, 15.4**
        
        Args:
            user_input: User input text
            context: Optional conversation context
            user_role: Optional user role
            
        Returns:
            RoutingDecision with agent type and metadata
        """
        self.total_routes += 1
        
        logger.info(f"Routing request: {user_input[:100]}...")
        
        # Step 1: Classify intent
        from .intent_classifier import IntentClassificationRequest
        
        classification_request = IntentClassificationRequest(
            text=user_input,
            context=context,
            user_role=user_role,
        )
        
        classification_result = await self.intent_classifier.classify_intent(
            classification_request
        )
        
        # Step 2: Check confidence threshold
        requires_clarification = (
            classification_result.confidence < self.confidence_threshold
        )
        
        clarifying_question = None
        if requires_clarification:
            self.clarification_requests += 1
            clarifying_question = self.intent_classifier.generate_clarifying_question(
                classification_result,
                user_input,
            )
        
        # Step 3: Match intent to agent
        agent_type = self._match_intent_to_agent(
            classification_result.intent,
            context or {},
        )
        
        # Step 4: Verify agent is registered
        if agent_type not in self.agents:
            logger.warning(f"Agent {agent_type.value} not registered, using fallback")
            agent_type = AgentType.FALLBACK
        
        # Step 5: Create routing decision
        routing_decision = RoutingDecision(
            agent_type=agent_type,
            intent=classification_result.intent,
            confidence=classification_result.confidence,
            reasoning=classification_result.reasoning,
            requires_clarification=requires_clarification,
            clarifying_question=clarifying_question,
            timestamp=datetime.utcnow(),
            context=context or {},
        )
        
        # Step 6: Log to audit trail
        if self.audit_logger:
            await self._log_routing_decision(
                routing_decision,
                user_input,
                classification_result,
            )
        
        if not requires_clarification:
            self.successful_routes += 1
        
        logger.info(
            f"Routed to {agent_type.value} agent "
            f"(intent: {classification_result.intent.value}, "
            f"confidence: {classification_result.confidence:.2f})"
        )
        
        return routing_decision
    
    async def execute_routing(
        self,
        routing_decision: RoutingDecision,
        input_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute routing by invoking the selected agent.
        
        Args:
            routing_decision: Routing decision from route_request
            input_data: Input data for agent processing
            
        Returns:
            Agent processing result
        """
        agent = self.agents.get(routing_decision.agent_type)
        
        if not agent:
            logger.error(f"Agent {routing_decision.agent_type.value} not found")
            return {
                "error": "Agent not available",
                "agent_type": routing_decision.agent_type.value,
            }
        
        try:
            # Add routing metadata to input
            input_data["routing_metadata"] = {
                "intent": routing_decision.intent.value,
                "confidence": routing_decision.confidence,
                "timestamp": routing_decision.timestamp.isoformat(),
            }
            
            # Execute agent
            result = await agent.process(input_data)
            
            logger.info(f"Agent {routing_decision.agent_type.value} completed processing")
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing agent {routing_decision.agent_type.value}: {e}")
            return {
                "error": str(e),
                "agent_type": routing_decision.agent_type.value,
            }
    
    def get_agent(self, agent_type: AgentType) -> Optional[Agent]:
        """
        Get registered agent by type.
        
        Args:
            agent_type: Type of agent to retrieve
            
        Returns:
            Agent instance or None if not registered
        """
        return self.agents.get(agent_type)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get routing statistics.
        
        Returns:
            Dictionary with routing metrics
        """
        return {
            "total_routes": self.total_routes,
            "successful_routes": self.successful_routes,
            "clarification_requests": self.clarification_requests,
            "success_rate": (
                self.successful_routes / self.total_routes
                if self.total_routes > 0 else 0.0
            ),
            "clarification_rate": (
                self.clarification_requests / self.total_routes
                if self.total_routes > 0 else 0.0
            ),
            "registered_agents": list(self.agents.keys()),
        }
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def _initialize_routing_rules(self) -> List[RoutingRule]:
        """
        Initialize intent-to-agent routing rules.
        
        Mapping:
        - LEAD_INTAKE → IntakeAgent
        - DIAGNOSIS → DiagnosticAgent
        - JOB_COMPLETION → FulfillmentAgent
        - SCHEDULING → FulfillmentAgent
        - PARTS_QUERY → DiagnosticAgent
        """
        return [
            RoutingRule(
                intent=IntentType.LEAD_INTAKE,
                agent_type=AgentType.INTAKE,
                required_capabilities=["lead_capture", "triage"],
                priority=10,
            ),
            RoutingRule(
                intent=IntentType.DIAGNOSIS,
                agent_type=AgentType.DIAGNOSTIC,
                required_capabilities=["diagnosis", "parts_sourcing"],
                priority=10,
            ),
            RoutingRule(
                intent=IntentType.JOB_COMPLETION,
                agent_type=AgentType.FULFILLMENT,
                required_capabilities=["job_logging", "carbon_tracking"],
                priority=10,
            ),
            RoutingRule(
                intent=IntentType.SCHEDULING,
                agent_type=AgentType.FULFILLMENT,
                required_capabilities=["scheduling", "route_optimization"],
                priority=10,
            ),
            RoutingRule(
                intent=IntentType.PARTS_QUERY,
                agent_type=AgentType.DIAGNOSTIC,
                required_capabilities=["parts_sourcing", "inventory_query"],
                priority=8,
            ),
            RoutingRule(
                intent=IntentType.UNKNOWN,
                agent_type=AgentType.FALLBACK,
                required_capabilities=[],
                priority=1,
            ),
        ]
    
    def _match_intent_to_agent(
        self,
        intent: IntentType,
        context: Dict[str, Any],
    ) -> AgentType:
        """
        Match intent to agent type using routing rules.
        
        Args:
            intent: Classified intent
            context: Conversation context
            
        Returns:
            Agent type to route to
        """
        # Find matching rules
        matching_rules = [
            rule for rule in self.routing_rules
            if rule.intent == intent
        ]
        
        if not matching_rules:
            logger.warning(f"No routing rule for intent {intent.value}")
            return AgentType.FALLBACK
        
        # Sort by priority (highest first)
        matching_rules.sort(key=lambda r: r.priority, reverse=True)
        
        # Return highest priority rule
        best_rule = matching_rules[0]
        
        logger.debug(
            f"Matched intent {intent.value} to agent {best_rule.agent_type.value}"
        )
        
        return best_rule.agent_type
    
    async def _log_routing_decision(
        self,
        routing_decision: RoutingDecision,
        user_input: str,
        classification_result: IntentClassificationResult,
    ) -> None:
        """
        Log routing decision to audit trail.
        
        **Validates: Requirement 15.4**
        
        Args:
            routing_decision: Routing decision
            user_input: Original user input
            classification_result: Intent classification result
        """
        if not self.audit_logger:
            return
        
        try:
            await self.audit_logger.log_routing_decision(
                timestamp=routing_decision.timestamp,
                user_input=user_input,
                intent=routing_decision.intent.value,
                confidence=routing_decision.confidence,
                agent_type=routing_decision.agent_type.value,
                requires_clarification=routing_decision.requires_clarification,
                reasoning=routing_decision.reasoning,
                parameters=classification_result.parameters,
                context=routing_decision.context,
            )
        except Exception as e:
            logger.error(f"Failed to log routing decision: {e}")


# ============================================================================
# Factory Function
# ============================================================================


def create_agent_router(
    intent_classifier: Any,
    audit_logger: Optional[Any] = None,
    confidence_threshold: float = 0.6,
) -> AgentRouter:
    """
    Create and configure an agent router.
    
    Args:
        intent_classifier: Intent classification service
        audit_logger: Optional audit trail logger
        confidence_threshold: Minimum confidence for routing
    
    Returns:
        Configured AgentRouter instance
    """
    return AgentRouter(
        intent_classifier=intent_classifier,
        audit_logger=audit_logger,
        confidence_threshold=confidence_threshold,
    )
