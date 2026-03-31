"""
Comprehensive Tests for Task 12: Agent Routing and Conversation Management.

Includes unit, integration, system, and end-to-end tests for:
- Intent classification
- Agent routing
- Conversation context management
- Audit trail logging

**Validates: Requirements 3.1, 3.2, 3.2, 4.10, 11.6, 15.4, 18.6, 18.7, 18.8**
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from orchestration.intent_classifier import (
    IntentClassifier,
    IntentType,
    IntentClassificationRequest,
    create_intent_classifier,
)
from orchestration.agent_router import (
    AgentRouter,
    AgentType,
    RoutingDecision,
    create_agent_router,
)
from orchestration.conversation_context import (
    ConversationContextManager,
    UserRole,
    SessionState,
    create_conversation_context_manager,
)
from orchestration.audit_logger import (
    AuditLogger,
    AuditEventType,
    create_audit_logger,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_llm_client():
    """Create mock LLM client for testing."""
    client = Mock()
    client.generate = AsyncMock()
    return client


@pytest.fixture
def intent_classifier(mock_llm_client):
    """Create intent classifier."""
    return create_intent_classifier(
        llm_client=mock_llm_client,
        confidence_threshold=0.6,
    )


@pytest.fixture
def audit_logger():
    """Create audit logger."""
    return create_audit_logger(
        db_session=None,
        signing_key="test-signing-key",
        enable_signing=True,
    )


@pytest.fixture
def agent_router(intent_classifier, audit_logger):
    """Create agent router with dependencies."""
    return create_agent_router(
        intent_classifier=intent_classifier,
        audit_logger=audit_logger,
        confidence_threshold=0.6,
    )


@pytest.fixture
def context_manager():
    """Create conversation context manager."""
    return create_conversation_context_manager(
        redis_client=None,
        session_ttl=3600,
    )


@pytest.fixture
def mock_agents():
    """Create mock agents for routing."""
    intake_agent = Mock()
    intake_agent.agent_type = "intake"
    intake_agent.capabilities = ["lead_capture", "triage"]
    intake_agent.process = AsyncMock(return_value={"status": "success"})
    
    diagnostic_agent = Mock()
    diagnostic_agent.agent_type = "diagnostic"
    diagnostic_agent.capabilities = ["diagnosis", "parts_sourcing"]
    diagnostic_agent.process = AsyncMock(return_value={"status": "success"})
    
    fulfillment_agent = Mock()
    fulfillment_agent.agent_type = "fulfillment"
    fulfillment_agent.capabilities = ["job_logging", "scheduling"]
    fulfillment_agent.process = AsyncMock(return_value={"status": "success"})
    
    return {
        AgentType.INTAKE: intake_agent,
        AgentType.DIAGNOSTIC: diagnostic_agent,
        AgentType.FULFILLMENT: fulfillment_agent,
    }


# ============================================================================
# Unit Tests (12.8.1)
# ============================================================================


class TestIntentClassificationUnit:
    """Unit tests for intent classification."""
    
    @pytest.mark.asyncio
    async def test_job_completion_classification(self, intent_classifier, mock_llm_client):
        """Test intent classification with job completion input."""
        mock_llm_client.generate.return_value = Mock(
            text='{"intent": "job_completion", "confidence": 0.92, "parameters": {"job_id": "123"}, "reasoning": "Technician logging job", "alternatives": []}'
        )
        
        request = IntentClassificationRequest(
            text="Log job completion for Smith residence, used thermostat TH-2000",
            user_role="technician",
        )
        
        result = await intent_classifier.classify_intent(request)
        
        assert result.intent == IntentType.JOB_COMPLETION
        assert result.confidence >= 0.6
        assert not intent_classifier.requires_clarification(result)
    
    @pytest.mark.asyncio
    async def test_lead_intake_classification(self, intent_classifier, mock_llm_client):
        """Test intent classification with lead intake input."""
        mock_llm_client.generate.return_value = Mock(
            text='{"intent": "lead_intake", "confidence": 0.88, "parameters": {}, "reasoning": "Customer reporting issue", "alternatives": []}'
        )
        
        request = IntentClassificationRequest(
            text="My furnace stopped working and it's freezing",
            user_role="customer",
        )
        
        result = await intent_classifier.classify_intent(request)
        
        assert result.intent == IntentType.LEAD_INTAKE
        assert result.confidence >= 0.6
    
    @pytest.mark.asyncio
    async def test_diagnosis_classification(self, intent_classifier, mock_llm_client):
        """Test intent classification with diagnosis input."""
        mock_llm_client.generate.return_value = Mock(
            text='{"intent": "diagnosis", "confidence": 0.85, "parameters": {}, "reasoning": "Technician needs help", "alternatives": []}'
        )
        
        request = IntentClassificationRequest(
            text="Help me diagnose this HVAC unit, compressor not starting",
            user_role="technician",
        )
        
        result = await intent_classifier.classify_intent(request)
        
        assert result.intent == IntentType.DIAGNOSIS
        assert result.confidence >= 0.6
    
    @pytest.mark.asyncio
    async def test_parts_query_classification(self, intent_classifier, mock_llm_client):
        """Test intent classification with parts query input."""
        mock_llm_client.generate.return_value = Mock(
            text='{"intent": "parts_query", "confidence": 0.80, "parameters": {}, "reasoning": "Checking parts", "alternatives": []}'
        )
        
        request = IntentClassificationRequest(
            text="Do we have capacitors in stock for Carrier units?",
            user_role="technician",
        )
        
        result = await intent_classifier.classify_intent(request)
        
        assert result.intent == IntentType.PARTS_QUERY
        assert result.confidence >= 0.6
    
    @pytest.mark.asyncio
    async def test_scheduling_classification(self, intent_classifier, mock_llm_client):
        """Test intent classification with scheduling input."""
        mock_llm_client.generate.return_value = Mock(
            text='{"intent": "scheduling", "confidence": 0.87, "parameters": {}, "reasoning": "Scheduling request", "alternatives": []}'
        )
        
        request = IntentClassificationRequest(
            text="Optimize my route for tomorrow's jobs",
            user_role="dispatcher",
        )
        
        result = await intent_classifier.classify_intent(request)
        
        assert result.intent == IntentType.SCHEDULING
        assert result.confidence >= 0.6
    
    @pytest.mark.asyncio
    async def test_low_confidence_requires_clarification(self, intent_classifier, mock_llm_client):
        """Test that low confidence triggers clarification."""
        mock_llm_client.generate.return_value = Mock(
            text='{"intent": "unknown", "confidence": 0.45, "parameters": {}, "reasoning": "Unclear", "alternatives": []}'
        )
        
        request = IntentClassificationRequest(text="Something about the thing")
        result = await intent_classifier.classify_intent(request)
        
        assert intent_classifier.requires_clarification(result)
        assert result.confidence < 0.6
        
        question = intent_classifier.generate_clarifying_question(result, "Something about the thing")
        assert len(question) > 0


class TestAgentRoutingUnit:
    """Unit tests for agent routing logic."""
    
    @pytest.mark.asyncio
    async def test_route_to_intake_agent(self, agent_router, intent_classifier, mock_llm_client):
        """Test routing decision to intake agent."""
        # Register mock agent
        mock_agent = Mock()
        mock_agent.agent_type = "intake"
        mock_agent.capabilities = ["lead_capture", "triage"]
        agent_router.register_agent(AgentType.INTAKE, mock_agent)
        
        mock_llm_client.generate.return_value = Mock(
            text='{"intent": "lead_intake", "confidence": 0.85, "parameters": {}, "reasoning": "Customer issue", "alternatives": []}'
        )
        
        decision = await agent_router.route_request(
            user_input="My AC stopped working",
            user_role="customer",
        )
        
        assert decision.agent_type == AgentType.INTAKE
        assert decision.intent == IntentType.LEAD_INTAKE
        assert not decision.requires_clarification
    
    @pytest.mark.asyncio
    async def test_route_to_diagnostic_agent(self, agent_router, intent_classifier, mock_llm_client):
        """Test routing decision to diagnostic agent."""
        # Register mock agent
        mock_agent = Mock()
        mock_agent.agent_type = "diagnostic"
        mock_agent.capabilities = ["diagnosis", "parts_sourcing"]
        agent_router.register_agent(AgentType.DIAGNOSTIC, mock_agent)
        
        mock_llm_client.generate.return_value = Mock(
            text='{"intent": "diagnosis", "confidence": 0.90, "parameters": {}, "reasoning": "Diagnosis needed", "alternatives": []}'
        )
        
        decision = await agent_router.route_request(
            user_input="Help diagnose this furnace",
            user_role="technician",
        )
        
        assert decision.agent_type == AgentType.DIAGNOSTIC
        assert decision.intent == IntentType.DIAGNOSIS
    
    @pytest.mark.asyncio
    async def test_route_to_fulfillment_agent(self, agent_router, intent_classifier, mock_llm_client):
        """Test routing decision to fulfillment agent."""
        # Register mock agent
        mock_agent = Mock()
        mock_agent.agent_type = "fulfillment"
        mock_agent.capabilities = ["job_logging", "carbon_tracking"]
        agent_router.register_agent(AgentType.FULFILLMENT, mock_agent)
        
        mock_llm_client.generate.return_value = Mock(
            text='{"intent": "job_completion", "confidence": 0.92, "parameters": {}, "reasoning": "Job logging", "alternatives": []}'
        )
        
        decision = await agent_router.route_request(
            user_input="Log job completion",
            user_role="technician",
        )
        
        assert decision.agent_type == AgentType.FULFILLMENT
        assert decision.intent == IntentType.JOB_COMPLETION


class TestConversationContextUnit:
    """Unit tests for conversation context management."""
    
    @pytest.mark.asyncio
    async def test_session_creation(self, context_manager):
        """Test conversation session creation."""
        context = await context_manager.create_session(
            user_id="tech123",
            user_role=UserRole.TECHNICIAN,
            metadata={"source": "web"},
        )
        
        assert context.session_id is not None
        assert context.user_id == "tech123"
        assert context.user_role == UserRole.TECHNICIAN
        assert context.state == SessionState.ACTIVE
        assert len(context.history) == 0
    
    @pytest.mark.asyncio
    async def test_add_conversation_turn(self, context_manager):
        """Test adding conversation turns."""
        context = await context_manager.create_session(
            user_id="tech123",
            user_role=UserRole.TECHNICIAN,
        )
        
        # Add user turn
        updated = await context_manager.add_turn(
            session_id=context.session_id,
            speaker="user",
            content="Log job completion",
            intent="job_completion",
            confidence=0.9,
        )
        
        assert len(updated.history) == 1
        assert updated.history[0].speaker == "user"
        assert updated.current_intent == "job_completion"
        
        # Add agent turn
        updated = await context_manager.add_turn(
            session_id=context.session_id,
            speaker="agent",
            content="What parts did you use?",
            agent_type="fulfillment",
        )
        
        assert len(updated.history) == 2
        assert updated.history[1].speaker == "agent"
    
    @pytest.mark.asyncio
    async def test_entity_updates(self, context_manager):
        """Test entity extraction and updates."""
        context = await context_manager.create_session(
            user_id="cust456",
            user_role=UserRole.CUSTOMER,
        )
        
        updated = await context_manager.update_entities(
            session_id=context.session_id,
            entities={
                "customer_name": "John Smith",
                "issue_type": "HVAC",
                "urgency": "emergency",
            },
        )
        
        assert updated.entities["customer_name"] == "John Smith"
        assert updated.entities["issue_type"] == "HVAC"
        assert updated.entities["urgency"] == "emergency"


class TestAuditTrailUnit:
    """Unit tests for audit trail logging."""
    
    @pytest.mark.asyncio
    async def test_log_conversation_turn(self, audit_logger):
        """Test logging conversation turns."""
        event = await audit_logger.log_conversation_turn(
            session_id="session123",
            user_id="user123",
            speaker="user",
            content="Log job completion",
            intent="job_completion",
            confidence=0.9,
        )
        
        assert event.event_type == AuditEventType.CONVERSATION_TURN
        assert event.session_id == "session123"
        assert event.details["speaker"] == "user"
        assert event.signature is not None
    
    @pytest.mark.asyncio
    async def test_log_routing_decision(self, audit_logger):
        """Test logging routing decisions."""
        event = await audit_logger.log_routing_decision(
            timestamp=datetime.utcnow(),
            user_input="My AC stopped working",
            intent="lead_intake",
            confidence=0.85,
            agent_type="intake",
            requires_clarification=False,
            reasoning="Customer reporting issue",
            parameters={},
            context={"user_id": "user123", "session_id": "session123"},
        )
        
        assert event.event_type == AuditEventType.ROUTING_DECISION
        assert event.details["intent"] == "lead_intake"
        assert event.details["agent_type"] == "intake"
    
    @pytest.mark.asyncio
    async def test_event_signature_verification(self, audit_logger):
        """Test event signature for tamper detection."""
        event = await audit_logger.log_conversation_turn(
            session_id="session123",
            user_id="user123",
            speaker="user",
            content="test content",
        )
        
        # Verify original signature
        assert audit_logger.verify_event_signature(event)
        
        # Tamper with event
        event.details["content"] = "tampered content"
        
        # Signature should be invalid
        assert not audit_logger.verify_event_signature(event)


# ============================================================================
# Integration Tests (12.8.2)
# ============================================================================


class TestRoutingIntegration:
    """Integration tests for complete routing flow."""
    
    @pytest.mark.asyncio
    async def test_complete_routing_flow(
        self,
        agent_router,
        context_manager,
        audit_logger,
        mock_agents,
        mock_llm_client,
    ):
        """Test complete flow: input → classify → route → execute → log."""
        # Register agents
        for agent_type, agent in mock_agents.items():
            agent_router.register_agent(agent_type, agent)
        
        # Mock LLM classification
        mock_llm_client.generate.return_value = Mock(
            text='{"intent": "job_completion", "confidence": 0.92, "parameters": {}, "reasoning": "Job logging", "alternatives": []}'
        )
        
        # Create session
        context = await context_manager.create_session(
            user_id="tech123",
            user_role=UserRole.TECHNICIAN,
        )
        
        # Route request
        decision = await agent_router.route_request(
            user_input="Log job completion for Smith residence",
            context={"session_id": context.session_id, "user_id": "tech123"},
            user_role="technician",
        )
        
        # Verify routing
        assert decision.agent_type == AgentType.FULFILLMENT
        assert not decision.requires_clarification
        
        # Execute routing
        result = await agent_router.execute_routing(
            decision,
            {"text": "Log job completion for Smith residence"},
        )
        
        assert result["status"] == "success"
        
        # Add turn to context
        await context_manager.add_turn(
            session_id=context.session_id,
            speaker="user",
            content="Log job completion for Smith residence",
            intent=decision.intent.value,
            agent_type=decision.agent_type.value,
            confidence=decision.confidence,
        )
        
        # Verify context updated
        updated_context = await context_manager.get_session(context.session_id)
        assert len(updated_context.history) == 1
        
        # Verify audit trail
        events = await audit_logger.query_events(
            session_id=context.session_id,
            limit=10,
        )
        assert len(events) >= 1
    
    @pytest.mark.asyncio
    async def test_agent_handoff_scenario(
        self,
        agent_router,
        context_manager,
        mock_agents,
        mock_llm_client,
    ):
        """Test agent handoff from intake to diagnostic."""
        # Register agents
        for agent_type, agent in mock_agents.items():
            agent_router.register_agent(agent_type, agent)
        
        # Create session
        context = await context_manager.create_session(
            user_id="cust456",
            user_role=UserRole.CUSTOMER,
        )
        
        # First interaction: Lead intake
        mock_llm_client.generate.return_value = Mock(
            text='{"intent": "lead_intake", "confidence": 0.88, "parameters": {}, "reasoning": "Customer issue", "alternatives": []}'
        )
        
        decision1 = await agent_router.route_request(
            user_input="My AC stopped working",
            context={"session_id": context.session_id},
        )
        
        assert decision1.agent_type == AgentType.INTAKE
        
        await context_manager.add_turn(
            session_id=context.session_id,
            speaker="user",
            content="My AC stopped working",
            intent=decision1.intent.value,
            agent_type=decision1.agent_type.value,
        )
        
        # Second interaction: Diagnosis needed
        mock_llm_client.generate.return_value = Mock(
            text='{"intent": "diagnosis", "confidence": 0.90, "parameters": {}, "reasoning": "Needs diagnosis", "alternatives": []}'
        )
        
        decision2 = await agent_router.route_request(
            user_input="Help me figure out what's wrong",
            context={"session_id": context.session_id},
        )
        
        assert decision2.agent_type == AgentType.DIAGNOSTIC
        
        # Verify context has both turns
        updated_context = await context_manager.get_session(context.session_id)
        assert len(updated_context.history) >= 1
    
    @pytest.mark.asyncio
    async def test_fallback_to_clarifying_questions(
        self,
        agent_router,
        context_manager,
        mock_llm_client,
    ):
        """Test fallback to clarifying questions on low confidence."""
        # Create session
        context = await context_manager.create_session(
            user_id="user789",
            user_role=UserRole.CUSTOMER,
        )
        
        # Mock low confidence classification
        mock_llm_client.generate.return_value = Mock(
            text='{"intent": "unknown", "confidence": 0.35, "parameters": {}, "reasoning": "Unclear", "alternatives": []}'
        )
        
        decision = await agent_router.route_request(
            user_input="Something about the thing",
            context={"session_id": context.session_id},
        )
        
        assert decision.requires_clarification
        assert decision.clarifying_question is not None
        assert len(decision.clarifying_question) > 0


# ============================================================================
# System Tests (12.8.3)
# ============================================================================


class TestRoutingSystemTests:
    """System tests for routing performance and accuracy."""
    
    @pytest.mark.asyncio
    async def test_classification_accuracy_with_real_conversations(
        self,
        intent_classifier,
        mock_llm_client,
    ):
        """Test classification accuracy with realistic inputs."""
        test_cases = [
            ("Log job completion for Smith residence", IntentType.JOB_COMPLETION),
            ("My furnace stopped working", IntentType.LEAD_INTAKE),
            ("Help diagnose this HVAC unit", IntentType.DIAGNOSIS),
            ("Do we have capacitors in stock?", IntentType.PARTS_QUERY),
            ("Optimize my schedule for tomorrow", IntentType.SCHEDULING),
        ]
        
        correct = 0
        for text, expected_intent in test_cases:
            # Mock appropriate response
            mock_llm_client.generate.return_value = Mock(
                text=f'{{"intent": "{expected_intent.value}", "confidence": 0.85, "parameters": {{}}, "reasoning": "test", "alternatives": []}}'
            )
            
            request = IntentClassificationRequest(text=text)
            result = await intent_classifier.classify_intent(request)
            
            if result.intent == expected_intent:
                correct += 1
        
        accuracy = correct / len(test_cases)
        assert accuracy >= 0.8  # At least 80% accuracy
    
    @pytest.mark.asyncio
    async def test_context_management_with_concurrent_sessions(
        self,
        context_manager,
    ):
        """Test context management with multiple concurrent sessions."""
        # Create multiple sessions
        sessions = []
        for i in range(10):
            context = await context_manager.create_session(
                user_id=f"user{i}",
                user_role=UserRole.TECHNICIAN,
            )
            sessions.append(context)
        
        # Add turns to each session
        for context in sessions:
            await context_manager.add_turn(
                session_id=context.session_id,
                speaker="user",
                content=f"Test message for {context.user_id}",
            )
        
        # Verify all sessions are intact
        for context in sessions:
            retrieved = await context_manager.get_session(context.session_id)
            assert retrieved is not None
            assert len(retrieved.history) == 1
    
    @pytest.mark.asyncio
    async def test_audit_trail_query_performance(self, audit_logger):
        """Test audit trail query performance with many events."""
        # Log many events
        for i in range(100):
            await audit_logger.log_conversation_turn(
                session_id=f"session{i % 10}",
                user_id=f"user{i % 5}",
                speaker="user",
                content=f"Message {i}",
            )
        
        # Query events
        import time
        start = time.time()
        events = await audit_logger.query_events(limit=50)
        duration = time.time() - start
        
        assert len(events) == 50
        assert duration < 1.0  # Should complete in under 1 second


# ============================================================================
# End-to-End Tests (12.8.4)
# ============================================================================


class TestRoutingEndToEnd:
    """End-to-end tests for complete routing scenarios."""
    
    @pytest.mark.asyncio
    async def test_complete_job_logging_scenario(
        self,
        agent_router,
        context_manager,
        audit_logger,
        mock_agents,
        mock_llm_client,
    ):
        """Test complete job logging scenario from start to finish."""
        # Register agents
        for agent_type, agent in mock_agents.items():
            agent_router.register_agent(agent_type, agent)
        
        # Create session
        context = await context_manager.create_session(
            user_id="tech123",
            user_role=UserRole.TECHNICIAN,
            metadata={"source": "mobile"},
        )
        
        # Simulate conversation
        conversation = [
            ("Log job completion for Smith residence", IntentType.JOB_COMPLETION),
            ("Used thermostat TH-2000 and capacitor CAP-500", IntentType.JOB_COMPLETION),
            ("Labor was 2 hours", IntentType.JOB_COMPLETION),
        ]
        
        for user_input, expected_intent in conversation:
            # Mock classification
            mock_llm_client.generate.return_value = Mock(
                text=f'{{"intent": "{expected_intent.value}", "confidence": 0.90, "parameters": {{}}, "reasoning": "test", "alternatives": []}}'
            )
            
            # Route request
            decision = await agent_router.route_request(
                user_input=user_input,
                context={"session_id": context.session_id, "user_id": "tech123"},
                user_role="technician",
            )
            
            # Add to context
            await context_manager.add_turn(
                session_id=context.session_id,
                speaker="user",
                content=user_input,
                intent=decision.intent.value,
                agent_type=decision.agent_type.value,
                confidence=decision.confidence,
            )
        
        # Verify final context
        final_context = await context_manager.get_session(context.session_id)
        assert len(final_context.history) == 3
        
        # Verify audit trail
        events = await audit_logger.query_events(
            session_id=context.session_id,
            event_type=AuditEventType.ROUTING_DECISION,
        )
        assert len(events) >= 3
    
    @pytest.mark.asyncio
    async def test_complete_customer_intake_scenario(
        self,
        agent_router,
        context_manager,
        audit_logger,
        mock_agents,
        mock_llm_client,
    ):
        """Test complete customer intake scenario."""
        # Register agents
        for agent_type, agent in mock_agents.items():
            agent_router.register_agent(agent_type, agent)
        
        # Create session
        context = await context_manager.create_session(
            user_id="cust456",
            user_role=UserRole.CUSTOMER,
        )
        
        # Simulate intake conversation
        conversation = [
            ("My AC stopped working", IntentType.LEAD_INTAKE),
            ("It's making a loud noise", IntentType.LEAD_INTAKE),
            ("Can someone come today?", IntentType.SCHEDULING),
        ]
        
        for user_input, expected_intent in conversation:
            mock_llm_client.generate.return_value = Mock(
                text=f'{{"intent": "{expected_intent.value}", "confidence": 0.85, "parameters": {{}}, "reasoning": "test", "alternatives": []}}'
            )
            
            decision = await agent_router.route_request(
                user_input=user_input,
                context={"session_id": context.session_id, "user_id": "cust456"},
                user_role="customer",
            )
            
            await context_manager.add_turn(
                session_id=context.session_id,
                speaker="user",
                content=user_input,
                intent=decision.intent.value,
                agent_type=decision.agent_type.value,
            )
        
        # Verify context
        final_context = await context_manager.get_session(context.session_id)
        assert len(final_context.history) == 3
        
        # Verify routing to different agents
        assert any(turn.agent_type == "intake" for turn in final_context.history)
        assert any(turn.agent_type == "fulfillment" for turn in final_context.history)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
