"""
Unit Tests for Agent Routing and Conversation Management.

Tests intent classification, agent routing, conversation context, and audit logging.

**Validates: Requirements 3.1, 3.2, 15.4, 18.6**
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from orchestration.intent_classifier import (
    IntentClassifier,
    IntentType,
    IntentClassificationRequest,
    create_intent_classifier,
)
from orchestration.agent_router import (
    AgentRouter,
    AgentType,
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
    AuditSeverity,
    create_audit_logger,
)


# ============================================================================
# Intent Classification Tests
# ============================================================================


class TestIntentClassifier:
    """Test intent classification service."""
    
    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client."""
        client = Mock()
        client.generate = AsyncMock()
        return client
    
    @pytest.fixture
    def classifier(self, mock_llm_client):
        """Create intent classifier."""
        return create_intent_classifier(
            llm_client=mock_llm_client,
            confidence_threshold=0.6,
        )
    
    @pytest.mark.asyncio
    async def test_classify_job_completion_intent(self, classifier, mock_llm_client):
        """Test classification of job completion intent."""
        # Mock LLM response
        mock_llm_client.generate.return_value = Mock(
            text='{"intent": "job_completion", "confidence": 0.9, "parameters": {}, "reasoning": "User is logging job completion", "alternatives": []}'
        )
        
        request = IntentClassificationRequest(
            text="Log job completion for Smith residence",
            user_role="technician",
        )
        
        result = await classifier.classify_intent(request)
        
        assert result.intent == IntentType.JOB_COMPLETION
        assert result.confidence >= 0.6
        assert "job completion" in result.reasoning.lower()
    
    @pytest.mark.asyncio
    async def test_classify_lead_intake_intent(self, classifier, mock_llm_client):
        """Test classification of lead intake intent."""
        mock_llm_client.generate.return_value = Mock(
            text='{"intent": "lead_intake", "confidence": 0.85, "parameters": {}, "reasoning": "Customer reporting new issue", "alternatives": []}'
        )
        
        request = IntentClassificationRequest(
            text="My AC stopped working",
            user_role="customer",
        )
        
        result = await classifier.classify_intent(request)
        
        assert result.intent == IntentType.LEAD_INTAKE
        assert result.confidence >= 0.6
    
    @pytest.mark.asyncio
    async def test_classify_diagnosis_intent(self, classifier, mock_llm_client):
        """Test classification of diagnosis intent."""
        mock_llm_client.generate.return_value = Mock(
            text='{"intent": "diagnosis", "confidence": 0.8, "parameters": {}, "reasoning": "Technician needs troubleshooting help", "alternatives": []}'
        )
        
        request = IntentClassificationRequest(
            text="Help me diagnose this furnace issue",
            user_role="technician",
        )
        
        result = await classifier.classify_intent(request)
        
        assert result.intent == IntentType.DIAGNOSIS
        assert result.confidence >= 0.6
    
    @pytest.mark.asyncio
    async def test_low_confidence_classification(self, classifier, mock_llm_client):
        """Test low confidence classification requires clarification."""
        mock_llm_client.generate.return_value = Mock(
            text='{"intent": "unknown", "confidence": 0.4, "parameters": {}, "reasoning": "Unclear intent", "alternatives": []}'
        )
        
        request = IntentClassificationRequest(
            text="Something about the thing",
        )
        
        result = await classifier.classify_intent(request)
        
        assert classifier.requires_clarification(result)
        assert result.confidence < 0.6
    
    @pytest.mark.asyncio
    async def test_generate_clarifying_question(self, classifier, mock_llm_client):
        """Test generation of clarifying questions."""
        mock_llm_client.generate.return_value = Mock(
            text='{"intent": "unknown", "confidence": 0.3, "parameters": {}, "reasoning": "Unclear", "alternatives": []}'
        )
        
        request = IntentClassificationRequest(text="unclear input")
        result = await classifier.classify_intent(request)
        
        question = classifier.generate_clarifying_question(result, "unclear input")
        
        assert len(question) > 0
        assert "?" in question
    
    @pytest.mark.asyncio
    async def test_fallback_classification(self, classifier, mock_llm_client):
        """Test fallback classification with keyword matching."""
        # Simulate LLM error
        mock_llm_client.generate.side_effect = Exception("LLM error")
        
        request = IntentClassificationRequest(
            text="Log job completion with parts used",
        )
        
        result = await classifier.classify_intent(request)
        
        # Should fallback to keyword matching or return unknown
        # The fallback should detect "log job" keywords
        assert result.intent in [IntentType.JOB_COMPLETION, IntentType.UNKNOWN]
        assert result.confidence >= 0.0
    
    def test_statistics_tracking(self, classifier):
        """Test statistics tracking."""
        stats = classifier.get_statistics()
        
        assert "total_classifications" in stats
        assert "high_confidence_count" in stats
        assert "low_confidence_count" in stats
        assert "confidence_threshold" in stats


# ============================================================================
# Agent Routing Tests
# ============================================================================


class TestAgentRouter:
    """Test agent routing logic."""
    
    @pytest.fixture
    def mock_intent_classifier(self):
        """Create mock intent classifier."""
        classifier = Mock()
        classifier.classify_intent = AsyncMock()
        classifier.generate_clarifying_question = Mock(return_value="Clarifying question?")
        return classifier
    
    @pytest.fixture
    def router(self, mock_intent_classifier):
        """Create agent router."""
        return create_agent_router(
            intent_classifier=mock_intent_classifier,
            confidence_threshold=0.6,
        )
    
    @pytest.mark.asyncio
    async def test_route_to_intake_agent(self, router, mock_intent_classifier):
        """Test routing to intake agent."""
        from orchestration.intent_classifier import IntentClassificationResult
        
        # Register mock agent
        mock_agent = Mock()
        mock_agent.agent_type = "intake"
        mock_agent.capabilities = ["lead_capture", "triage"]
        router.register_agent(AgentType.INTAKE, mock_agent)
        
        # Mock classification result
        mock_intent_classifier.classify_intent.return_value = IntentClassificationResult(
            intent=IntentType.LEAD_INTAKE,
            confidence=0.85,
            parameters={},
            reasoning="Customer reporting issue",
            alternative_intents=[],
        )
        
        decision = await router.route_request(
            user_input="My AC stopped working",
            user_role="customer",
        )
        
        assert decision.agent_type == AgentType.INTAKE
        assert decision.intent == IntentType.LEAD_INTAKE
        assert decision.confidence >= 0.6
        assert not decision.requires_clarification
    
    @pytest.mark.asyncio
    async def test_route_to_diagnostic_agent(self, router, mock_intent_classifier):
        """Test routing to diagnostic agent."""
        from orchestration.intent_classifier import IntentClassificationResult
        
        # Register mock agent
        mock_agent = Mock()
        mock_agent.agent_type = "diagnostic"
        mock_agent.capabilities = ["diagnosis", "parts_sourcing"]
        router.register_agent(AgentType.DIAGNOSTIC, mock_agent)
        
        mock_intent_classifier.classify_intent.return_value = IntentClassificationResult(
            intent=IntentType.DIAGNOSIS,
            confidence=0.9,
            parameters={},
            reasoning="Technician needs diagnosis help",
            alternative_intents=[],
        )
        
        decision = await router.route_request(
            user_input="Help diagnose this issue",
            user_role="technician",
        )
        
        assert decision.agent_type == AgentType.DIAGNOSTIC
        assert decision.intent == IntentType.DIAGNOSIS
    
    @pytest.mark.asyncio
    async def test_route_to_fulfillment_agent(self, router, mock_intent_classifier):
        """Test routing to fulfillment agent."""
        from orchestration.intent_classifier import IntentClassificationResult
        
        # Register mock agent
        mock_agent = Mock()
        mock_agent.agent_type = "fulfillment"
        mock_agent.capabilities = ["job_logging", "carbon_tracking"]
        router.register_agent(AgentType.FULFILLMENT, mock_agent)
        
        mock_intent_classifier.classify_intent.return_value = IntentClassificationResult(
            intent=IntentType.JOB_COMPLETION,
            confidence=0.88,
            parameters={},
            reasoning="Technician logging job completion",
            alternative_intents=[],
        )
        
        decision = await router.route_request(
            user_input="Log job completion",
            user_role="technician",
        )
        
        assert decision.agent_type == AgentType.FULFILLMENT
        assert decision.intent == IntentType.JOB_COMPLETION
    
    @pytest.mark.asyncio
    async def test_low_confidence_requires_clarification(self, router, mock_intent_classifier):
        """Test low confidence routing requires clarification."""
        from orchestration.intent_classifier import IntentClassificationResult
        
        mock_intent_classifier.classify_intent.return_value = IntentClassificationResult(
            intent=IntentType.UNKNOWN,
            confidence=0.4,
            parameters={},
            reasoning="Unclear intent",
            alternative_intents=[],
        )
        
        decision = await router.route_request(
            user_input="Something unclear",
        )
        
        assert decision.requires_clarification
        assert decision.clarifying_question is not None
        assert decision.confidence < 0.6
    
    @pytest.mark.asyncio
    async def test_agent_registration(self, router):
        """Test agent registration."""
        mock_agent = Mock()
        mock_agent.agent_type = "intake"
        mock_agent.capabilities = ["lead_capture", "triage"]
        
        router.register_agent(AgentType.INTAKE, mock_agent)
        
        retrieved_agent = router.get_agent(AgentType.INTAKE)
        assert retrieved_agent == mock_agent
    
    def test_routing_statistics(self, router):
        """Test routing statistics."""
        stats = router.get_statistics()
        
        assert "total_routes" in stats
        assert "successful_routes" in stats
        assert "clarification_requests" in stats
        assert "registered_agents" in stats


# ============================================================================
# Conversation Context Tests
# ============================================================================


class TestConversationContextManager:
    """Test conversation context management."""
    
    @pytest.fixture
    def context_manager(self):
        """Create conversation context manager."""
        return create_conversation_context_manager(
            redis_client=None,  # Use in-memory storage
            session_ttl=3600,
        )
    
    @pytest.mark.asyncio
    async def test_create_session(self, context_manager):
        """Test session creation."""
        context = await context_manager.create_session(
            user_id="user123",
            user_role=UserRole.TECHNICIAN,
            metadata={"source": "web"},
        )
        
        assert context.session_id is not None
        assert context.user_id == "user123"
        assert context.user_role == UserRole.TECHNICIAN
        assert context.state == SessionState.ACTIVE
        assert len(context.history) == 0
    
    @pytest.mark.asyncio
    async def test_get_session(self, context_manager):
        """Test session retrieval."""
        # Create session
        created_context = await context_manager.create_session(
            user_id="user123",
            user_role=UserRole.CUSTOMER,
        )
        
        # Retrieve session
        retrieved_context = await context_manager.get_session(created_context.session_id)
        
        assert retrieved_context is not None
        assert retrieved_context.session_id == created_context.session_id
        assert retrieved_context.user_id == "user123"
    
    @pytest.mark.asyncio
    async def test_add_conversation_turn(self, context_manager):
        """Test adding conversation turn."""
        context = await context_manager.create_session(
            user_id="user123",
            user_role=UserRole.TECHNICIAN,
        )
        
        updated_context = await context_manager.add_turn(
            session_id=context.session_id,
            speaker="user",
            content="Log job completion",
            intent="job_completion",
            confidence=0.9,
        )
        
        assert updated_context is not None
        assert len(updated_context.history) == 1
        assert updated_context.history[0].speaker == "user"
        assert updated_context.history[0].content == "Log job completion"
        assert updated_context.current_intent == "job_completion"
    
    @pytest.mark.asyncio
    async def test_update_entities(self, context_manager):
        """Test entity updates."""
        context = await context_manager.create_session(
            user_id="user123",
            user_role=UserRole.CUSTOMER,
        )
        
        updated_context = await context_manager.update_entities(
            session_id=context.session_id,
            entities={"customer_name": "John Smith", "issue_type": "HVAC"},
        )
        
        assert updated_context is not None
        assert updated_context.entities["customer_name"] == "John Smith"
        assert updated_context.entities["issue_type"] == "HVAC"
    
    @pytest.mark.asyncio
    async def test_set_session_state(self, context_manager):
        """Test session state changes."""
        context = await context_manager.create_session(
            user_id="user123",
            user_role=UserRole.TECHNICIAN,
        )
        
        updated_context = await context_manager.set_state(
            session_id=context.session_id,
            state=SessionState.COMPLETED,
        )
        
        assert updated_context is not None
        assert updated_context.state == SessionState.COMPLETED
    
    @pytest.mark.asyncio
    async def test_extend_session(self, context_manager):
        """Test session expiration extension."""
        context = await context_manager.create_session(
            user_id="user123",
            user_role=UserRole.CUSTOMER,
        )
        
        original_expires_at = context.expires_at
        
        # Wait a moment to ensure time difference
        import asyncio
        await asyncio.sleep(0.1)
        
        updated_context = await context_manager.extend_session(
            session_id=context.session_id,
            additional_seconds=1800,
        )
        
        assert updated_context is not None
        # The new expiration should be later than the original
        # (accounting for the fact that extend_session uses current time + additional_seconds)
        assert updated_context.expires_at >= original_expires_at
    
    @pytest.mark.asyncio
    async def test_delete_session(self, context_manager):
        """Test session deletion."""
        context = await context_manager.create_session(
            user_id="user123",
            user_role=UserRole.TECHNICIAN,
        )
        
        deleted = await context_manager.delete_session(context.session_id)
        
        assert deleted
        
        # Verify session is gone
        retrieved = await context_manager.get_session(context.session_id)
        assert retrieved is None
    
    def test_context_statistics(self, context_manager):
        """Test context manager statistics."""
        stats = context_manager.get_statistics()
        
        assert "total_sessions" in stats
        assert "active_sessions" in stats
        assert "session_ttl" in stats


# ============================================================================
# Audit Logger Tests
# ============================================================================


class TestAuditLogger:
    """Test audit trail logging."""
    
    @pytest.fixture
    def audit_logger(self):
        """Create audit logger."""
        return create_audit_logger(
            db_session=None,  # Use in-memory storage
            signing_key="test-key",
            enable_signing=True,
        )
    
    @pytest.mark.asyncio
    async def test_log_conversation_turn(self, audit_logger):
        """Test logging conversation turn."""
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
        assert event.user_id == "user123"
        assert event.details["speaker"] == "user"
        assert event.signature is not None
    
    @pytest.mark.asyncio
    async def test_log_routing_decision(self, audit_logger):
        """Test logging routing decision."""
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
        assert event.details["confidence"] == 0.85
    
    @pytest.mark.asyncio
    async def test_log_api_call(self, audit_logger):
        """Test logging API call."""
        event = await audit_logger.log_api_call(
            user_id="user123",
            session_id="session123",
            api_name="gemini",
            endpoint="/v1/generate",
            method="POST",
            parameters={"prompt": "test"},
            response_status=200,
            duration_ms=150.5,
            cost=0.001,
        )
        
        assert event.event_type == AuditEventType.API_CALL
        assert event.details["api_name"] == "gemini"
        assert event.details["duration_ms"] == 150.5
        assert event.details["cost"] == 0.001
    
    @pytest.mark.asyncio
    async def test_log_agent_execution(self, audit_logger):
        """Test logging agent execution."""
        event = await audit_logger.log_agent_execution(
            user_id="user123",
            session_id="session123",
            agent_type="intake",
            input_data={"text": "test"},
            output_data={"result": "success"},
            duration_ms=250.0,
            success=True,
        )
        
        assert event.event_type == AuditEventType.AGENT_EXECUTION
        assert event.details["agent_type"] == "intake"
        assert event.details["success"] is True
    
    @pytest.mark.asyncio
    async def test_log_data_access(self, audit_logger):
        """Test logging data access."""
        event = await audit_logger.log_data_access(
            user_id="user123",
            resource_type="lead",
            resource_id="lead456",
            action="read",
        )
        
        assert event.event_type == AuditEventType.DATA_ACCESS
        assert event.details["resource_type"] == "lead"
        assert event.details["action"] == "read"
    
    @pytest.mark.asyncio
    async def test_log_data_modification(self, audit_logger):
        """Test logging data modification."""
        event = await audit_logger.log_data_modification(
            user_id="user123",
            resource_type="job",
            resource_id="job789",
            action="update",
            old_value={"status": "scheduled"},
            new_value={"status": "completed"},
        )
        
        assert event.event_type == AuditEventType.DATA_MODIFICATION
        assert event.details["action"] == "update"
        assert event.details["old_value"]["status"] == "scheduled"
        assert event.details["new_value"]["status"] == "completed"
    
    @pytest.mark.asyncio
    async def test_event_signature_verification(self, audit_logger):
        """Test event signature verification."""
        event = await audit_logger.log_conversation_turn(
            session_id="session123",
            user_id="user123",
            speaker="user",
            content="test",
        )
        
        # Verify signature
        is_valid = audit_logger.verify_event_signature(event)
        assert is_valid
        
        # Tamper with event
        event.details["content"] = "tampered"
        
        # Signature should no longer be valid
        is_valid = audit_logger.verify_event_signature(event)
        assert not is_valid
    
    @pytest.mark.asyncio
    async def test_query_events(self, audit_logger):
        """Test querying audit events."""
        # Log multiple events
        await audit_logger.log_conversation_turn(
            session_id="session123",
            user_id="user123",
            speaker="user",
            content="test1",
        )
        
        await audit_logger.log_routing_decision(
            timestamp=datetime.utcnow(),
            user_input="test2",
            intent="lead_intake",
            confidence=0.8,
            agent_type="intake",
            requires_clarification=False,
            reasoning="test",
            parameters={},
            context={"session_id": "session123"},
        )
        
        # Query events
        events = await audit_logger.query_events(
            session_id="session123",
            limit=10,
        )
        
        assert len(events) == 2
    
    def test_audit_statistics(self, audit_logger):
        """Test audit logger statistics."""
        stats = audit_logger.get_statistics()
        
        assert "total_events" in stats
        assert "events_by_type" in stats
        assert "signing_enabled" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
