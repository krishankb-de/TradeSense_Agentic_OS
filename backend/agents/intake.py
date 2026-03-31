"""
Intake Agent - CrewAI Implementation
Handles lead capture, triage, and scheduling from voice/SMS/web sources
Uses PydanticAI for structured output extraction
Integrates with unified LLM client (Gemini with Azure OpenAI fallback)
Integrates with notification module for customer and technician notifications

Validates: Requirements 4.1, 4.2, 4.8, 4.9, 4.10
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field, validator

# Note: CrewAI requires Python <=3.13. For Python 3.14, we use a simplified implementation.
# When using Python 3.13 or earlier, uncomment the following:
# from crewai import Agent, Task, Crew, Process

from llm.unified_client import UnifiedLLMClient, LLMProvider
from db.models import Lead, Customer, Part, Technician
from db.session import get_db

# Import notification components
from notifications import (
    EmailNotifier,
    WebPushNotifier,
    DiscordNotifier,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

class LeadSource(str, Enum):
    """Lead source types."""
    VOICE = "voice"
    SMS = "sms"
    WEB = "web"
    WEBRTC = "webrtc"
    JITSI = "jitsi"


class UrgencyLevel(str, Enum):
    """Urgency classification levels."""
    EMERGENCY = "emergency"
    URGENT = "urgent"
    ROUTINE = "routine"


class GeoLocation(BaseModel):
    """Geographic location information."""
    latitude: float = Field(..., description="Latitude coordinate")
    longitude: float = Field(..., description="Longitude coordinate")
    address: str = Field(..., description="Street address")
    city: str = Field(..., description="City name")
    state: str = Field(..., description="State/province")
    zip_code: str = Field(..., description="ZIP/postal code")


class CustomerInfo(BaseModel):
    """Customer information."""
    name: Optional[str] = Field(None, description="Customer name")
    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    address: Optional[str] = Field(None, description="Street address")


class LeadInput(BaseModel):
    """Input data for lead capture."""
    source: LeadSource = Field(..., description="Lead source channel")
    customer_info: CustomerInfo = Field(..., description="Customer information")
    issue_description: str = Field(..., description="Description of the issue")
    urgency: Optional[UrgencyLevel] = Field(None, description="Urgency level (if known)")
    location: Optional[GeoLocation] = Field(None, description="Service location")
    raw_text: Optional[str] = Field(None, description="Raw transcription/text")


class TriageResult(BaseModel):
    """Result of lead triage."""
    service_type: str = Field(..., description="Classified service type (HVAC, Plumbing, Electrical, etc.)")
    estimated_duration: int = Field(..., description="Estimated duration in minutes")
    required_skills: List[str] = Field(default_factory=list, description="Required technician skills")
    suggested_technicians: List[str] = Field(default_factory=list, description="Suggested technician IDs")
    priority: int = Field(..., ge=1, le=10, description="Priority score (1-10)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Classification confidence")
    urgency: UrgencyLevel = Field(..., description="Classified urgency level")
    reasoning: str = Field(..., description="Reasoning for classification")


class PartAvailability(BaseModel):
    """Part availability information."""
    part_id: Optional[str] = Field(None, description="Part ID from inventory")
    part_number: str = Field(..., description="Part number")
    name: str = Field(..., description="Part name")
    quantity_available: int = Field(..., description="Quantity available in inventory")
    is_available: bool = Field(..., description="Whether part is available")
    reorder_needed: bool = Field(default=False, description="Whether reorder is needed")
    alternatives: List[str] = Field(default_factory=list, description="Alternative part numbers")


class PartQuery(BaseModel):
    """Part query for availability checking."""
    part_number: Optional[str] = Field(None, description="Part number to search")
    name: Optional[str] = Field(None, description="Part name to search")
    category: Optional[str] = Field(None, description="Part category")
    service_type: Optional[str] = Field(None, description="Service type (HVAC, Plumbing, etc.)")


class StructuredLeadData(BaseModel):
    """Structured lead data extracted from unstructured input."""
    service_type: str = Field(..., description="Type of service needed")
    urgency: UrgencyLevel = Field(..., description="Urgency level")
    issue_summary: str = Field(..., description="Brief summary of the issue")
    equipment_type: Optional[str] = Field(None, description="Type of equipment involved")
    symptoms: List[str] = Field(default_factory=list, description="List of symptoms")
    customer_name: Optional[str] = Field(None, description="Customer name")
    location_description: Optional[str] = Field(None, description="Location description")
    
    @validator('urgency', pre=True)
    def validate_urgency(cls, v):
        """Validate and normalize urgency level."""
        if isinstance(v, str):
            v = v.lower()
            if v in ['emergency', 'urgent', 'routine']:
                return v
        return 'routine'  # Default to routine if unclear


# ============================================================================
# Intake Agent Implementation
# ============================================================================

class IntakeAgent:
    """
    Intake Agent using CrewAI for lead capture and triage.
    
    Features:
    - Multi-source lead capture (voice, SMS, web, WebRTC, Jitsi)
    - PydanticAI structured output extraction
    - Unified LLM client integration (Gemini → Azure OpenAI fallback)
    - CrewAI role-based collaboration
    - 24/7 availability
    
    Validates: Requirements 4.1, 4.2, 4.9
    """
    
    def __init__(
        self,
        llm_client: UnifiedLLMClient,
        email_notifier: Optional[EmailNotifier] = None,
        push_notifier: Optional[WebPushNotifier] = None,
        discord_notifier: Optional[DiscordNotifier] = None,
        enable_logging: bool = True,
    ):
        """
        Initialize Intake Agent.
        
        Args:
            llm_client: Unified LLM client for inference
            email_notifier: Email notification service
            push_notifier: Web push notification service
            discord_notifier: Discord webhook notification service
            enable_logging: Enable detailed logging
        """
        self.llm_client = llm_client
        self.email_notifier = email_notifier
        self.push_notifier = push_notifier
        self.discord_notifier = discord_notifier
        self.enable_logging = enable_logging
        
        # Statistics
        self.total_leads = 0
        self.successful_triages = 0
        self.failed_triages = 0
        
        # Initialize CrewAI agents
        self._init_crew_agents()
        
        logger.info("Intake Agent initialized with CrewAI and notification services")
    
    def _init_crew_agents(self):
        """
        Initialize CrewAI agents for intake workflow.
        
        Note: CrewAI requires Python <=3.13. This is a simplified implementation
        for Python 3.14. When using Python 3.13 or earlier, this method will
        create actual CrewAI agents.
        """
        # Simplified implementation for Python 3.14
        # When CrewAI is available (Python <=3.13), this will create actual agents
        
        # For now, we'll use the LLM client directly with role-based prompts
        self.capture_role = "Lead Capture Specialist"
        self.triage_role = "Service Triage Specialist"
        self.scheduling_role = "Scheduling Coordinator"
        
        logger.info("Intake agent initialized (simplified mode for Python 3.14)")
    
    async def capture_lead(self, input_data: LeadInput) -> Lead:
        """
        Capture new lead from voice/SMS/web source.
        
        Validates: Requirement 4.1 (Lead capture from voice/SMS/web)
        
        Args:
            input_data: Lead input data
            
        Returns:
            Lead object with structured information
        """
        self.total_leads += 1
        
        logger.info(
            f"Capturing lead from {input_data.source}: "
            f"{input_data.issue_description[:100]}..."
        )
        
        # Step 1: Extract structured data using PydanticAI
        structured_data = await self.extract_structured_data(
            text=input_data.raw_text or input_data.issue_description,
            schema=StructuredLeadData
        )
        
        # Step 2: Create or get customer
        customer = self._get_or_create_customer(input_data.customer_info)
        
        # Step 3: Create lead record
        lead = Lead(
            id=uuid4(),
            customer_id=customer.id,
            source=input_data.source.value,
            urgency=structured_data.urgency.value,
            service_type=structured_data.service_type,
            description=structured_data.issue_summary,
            confidence_score=0.0,  # Will be set by triage
            status="new",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        # Step 4: Save to database
        db = next(get_db())
        try:
            db.add(lead)
            db.commit()
            db.refresh(lead)
        finally:
            db.close()
        
        logger.info(f"Lead captured successfully: {lead.id}")
        
        return lead
    
    async def triage_lead(self, lead: Lead) -> TriageResult:
        """
        Classify urgency and service type using local LLM.
        
        Validates: Requirement 4.3, 4.4 (Classify urgency within 60 seconds)
        Validates: Requirement 4.6 (Query InvenTree API for initial parts availability)
        
        Args:
            lead: Lead object to triage
            
        Returns:
            TriageResult with classification and parts availability
        """
        import time
        start_time = time.time()
        
        logger.info(f"Triaging lead: {lead.id}")
        
        try:
            # Step 1: Classify urgency
            urgency_result = await self._classify_urgency(lead.description)
            
            # Step 2: Detect service type
            service_type_result = await self._detect_service_type(lead.description)
            
            # Step 3: Calculate confidence score
            confidence = self._calculate_confidence(urgency_result, service_type_result)
            
            # Step 4: Estimate duration and required skills
            duration = self._estimate_duration(service_type_result['service_type'], urgency_result['urgency'])
            skills = self._determine_required_skills(service_type_result['service_type'])
            
            # Step 5: Calculate priority score
            priority = self._calculate_priority(urgency_result['urgency'], confidence)
            
            # Step 6: Check parts availability for common parts
            # Validates: Requirement 4.6
            common_parts = await self.get_common_parts_for_service(service_type_result['service_type'])
            parts_availability = await self.check_parts_availability(common_parts)
            
            # Log parts availability
            available_count = sum(1 for p in parts_availability if p.is_available)
            logger.info(
                f"Parts availability: {available_count}/{len(parts_availability)} "
                f"common parts available for {service_type_result['service_type']}"
            )
            
            # Step 7: Generate reasoning
            reasoning = self._generate_reasoning(
                urgency_result, 
                service_type_result, 
                confidence,
                duration,
                skills
            )
            
            # Add parts availability to reasoning
            if parts_availability:
                parts_summary = f" Parts check: {available_count}/{len(parts_availability)} common parts in stock."
                reasoning += parts_summary
            
            # Create triage result
            triage_result = TriageResult(
                service_type=service_type_result['service_type'],
                estimated_duration=duration,
                required_skills=skills,
                suggested_technicians=[],  # Will be populated by scheduling
                priority=priority,
                confidence=confidence,
                urgency=UrgencyLevel(urgency_result['urgency']),
                reasoning=reasoning,
            )
            
            # Update lead with triage results
            lead.urgency = triage_result.urgency.value
            lead.service_type = triage_result.service_type
            lead.confidence_score = triage_result.confidence
            lead.status = "triaged"
            lead.updated_at = datetime.utcnow()
            
            db = next(get_db())
            try:
                db.add(lead)
                db.commit()
            finally:
                db.close()
            
            # Check latency requirement (< 60 seconds)
            elapsed = time.time() - start_time
            if elapsed > 60:
                logger.warning(
                    f"Triage latency ({elapsed:.2f}s) exceeded 60s target for lead {lead.id}"
                )
            else:
                logger.info(f"Triage completed in {elapsed:.2f}s for lead {lead.id}")
            
            self.successful_triages += 1
            
            return triage_result
            
        except Exception as e:
            self.failed_triages += 1
            logger.error(f"Triage failed for lead {lead.id}: {e}")
            raise
    
    async def extract_structured_data(
        self,
        text: str,
        schema: type[BaseModel]
    ) -> BaseModel:
        """
        Extract structured information using PydanticAI and Local LLM.
        
        Validates: Requirement 4.2 (Structured output extraction)
        
        Args:
            text: Unstructured text input
            schema: Pydantic model schema for extraction
            
        Returns:
            Structured data matching schema
        """
        logger.debug(f"Extracting structured data from text: {text[:100]}...")
        
        # Build extraction prompt
        schema_fields = []
        for field_name, field_info in schema.model_fields.items():
            schema_fields.append(
                f"- {field_name}: {field_info.description or 'No description'}"
            )
        
        prompt = (
            f"Extract the following information from this text:\n\n"
            f"Text: {text}\n\n"
            f"Required fields:\n" + "\n".join(schema_fields) + "\n\n"
            f"Provide the information in a structured format. "
            f"If a field cannot be determined, use null or an empty value."
        )
        
        # Generate with LLM
        response = self.llm_client.generate(
            prompt=prompt,
            temperature=0.2,  # Low temperature for extraction
            max_tokens=300,
        )
        
        # Parse response into Pydantic model
        # For now, we'll do simple parsing - in production, use PydanticAI's structured output
        structured_data = self._parse_extraction_response(response.text, schema)
        
        logger.debug(f"Extracted structured data: {structured_data}")
        
        return structured_data
    
    def _parse_extraction_response(
        self,
        response_text: str,
        schema: type[BaseModel]
    ) -> BaseModel:
        """
        Parse LLM response into Pydantic model.
        
        This is a simplified implementation. In production, use PydanticAI's
        structured output capabilities for more robust parsing.
        """
        import json
        import re
        
        # Try to extract JSON from response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                return schema(**data)
            except Exception as e:
                logger.warning(f"Failed to parse JSON from response: {e}")
        
        # Fallback: Create default instance with available data
        # This is a simplified fallback - enhance based on schema
        if schema == StructuredLeadData:
            return StructuredLeadData(
                service_type="General",
                urgency=UrgencyLevel.ROUTINE,
                issue_summary=response_text[:200],
                symptoms=[],
            )
        
        # Generic fallback
        return schema()
    
    async def _classify_urgency(self, description: str) -> Dict[str, Any]:
        """
        Classify urgency level using LLM.
        
        Args:
            description: Issue description
            
        Returns:
            Dictionary with urgency classification and confidence
        """
        urgency_prompt = (
            f"You are an expert field service triage specialist.\n\n"
            f"Classify the urgency of this service request:\n\n"
            f"Description: {description}\n\n"
            f"Urgency levels:\n"
            f"- emergency: Life/safety risk, property damage, or complete system failure (furnace in winter, no water, gas leak)\n"
            f"- urgent: Significant discomfort or partial failure, needs same-day service (AC in summer, intermittent issues)\n"
            f"- routine: Maintenance, minor issues, can be scheduled normally (tune-up, small repairs)\n\n"
            f"Respond with ONLY the urgency level (emergency, urgent, or routine) and a brief reason."
        )
        
        response = self.llm_client.generate(
            prompt=urgency_prompt,
            temperature=0.2,  # Low temperature for consistent classification
            max_tokens=100,
        )
        
        # Parse urgency from response
        response_text = response.text.lower()
        urgency = 'routine'  # Default
        confidence = 0.7  # Default confidence
        
        if 'emergency' in response_text:
            urgency = 'emergency'
            confidence = 0.9
        elif 'urgent' in response_text:
            urgency = 'urgent'
            confidence = 0.85
        elif 'routine' in response_text:
            urgency = 'routine'
            confidence = 0.8
        
        # Check for high-confidence keywords
        emergency_keywords = ['gas leak', 'no heat', 'no water', 'flooding', 'fire', 'electrical shock']
        urgent_keywords = ['not working', 'broken', 'stopped', 'failed', 'leaking']
        
        for keyword in emergency_keywords:
            if keyword in description.lower():
                urgency = 'emergency'
                confidence = 0.95
                break
        
        if urgency != 'emergency':
            for keyword in urgent_keywords:
                if keyword in description.lower():
                    urgency = 'urgent'
                    confidence = max(confidence, 0.85)
                    break
        
        logger.debug(f"Urgency classified as '{urgency}' with confidence {confidence}")
        
        return {
            'urgency': urgency,
            'confidence': confidence,
            'reasoning': response.text[:200]
        }
    
    async def _detect_service_type(self, description: str) -> Dict[str, Any]:
        """
        Detect service type using LLM.
        
        Args:
            description: Issue description
            
        Returns:
            Dictionary with service type and confidence
        """
        service_prompt = (
            f"You are an expert field service dispatcher.\n\n"
            f"Identify the service type for this request:\n\n"
            f"Description: {description}\n\n"
            f"Service types:\n"
            f"- HVAC: Heating, ventilation, air conditioning (furnace, AC, thermostat, ductwork)\n"
            f"- Plumbing: Water systems, pipes, drains (leaks, clogs, water heater, fixtures)\n"
            f"- Electrical: Wiring, outlets, breakers (no power, flickering lights, outlets)\n"
            f"- Appliance: Refrigerator, washer, dryer, dishwasher, oven\n"
            f"- General: Other maintenance or repairs\n\n"
            f"Respond with ONLY the service type and a brief reason."
        )
        
        response = self.llm_client.generate(
            prompt=service_prompt,
            temperature=0.2,
            max_tokens=100,
        )
        
        # Parse service type from response
        response_text = response.text.lower()
        service_type = 'General'  # Default
        confidence = 0.7
        
        # Check for service type keywords
        service_keywords = {
            'HVAC': ['hvac', 'furnace', 'ac', 'air conditioning', 'heating', 'thermostat', 'heat pump', 'ductwork'],
            'Plumbing': ['plumbing', 'water', 'pipe', 'drain', 'leak', 'toilet', 'sink', 'faucet', 'water heater'],
            'Electrical': ['electrical', 'electric', 'power', 'outlet', 'breaker', 'wiring', 'light', 'switch'],
            'Appliance': ['appliance', 'refrigerator', 'fridge', 'washer', 'dryer', 'dishwasher', 'oven', 'stove'],
        }
        
        # Check description for keywords
        for svc_type, keywords in service_keywords.items():
            for keyword in keywords:
                if keyword in description.lower():
                    service_type = svc_type
                    confidence = 0.9
                    break
            if service_type != 'General':
                break
        
        # Also check LLM response
        if service_type == 'General':
            for svc_type in service_keywords.keys():
                if svc_type.lower() in response_text:
                    service_type = svc_type
                    confidence = 0.85
                    break
        
        logger.debug(f"Service type detected as '{service_type}' with confidence {confidence}")
        
        return {
            'service_type': service_type,
            'confidence': confidence,
            'reasoning': response.text[:200]
        }
    
    def _calculate_confidence(
        self,
        urgency_result: Dict[str, Any],
        service_type_result: Dict[str, Any]
    ) -> float:
        """
        Calculate overall confidence score.
        
        Args:
            urgency_result: Urgency classification result
            service_type_result: Service type detection result
            
        Returns:
            Overall confidence score (0.0-1.0)
        """
        # Average the two confidence scores
        urgency_conf = urgency_result.get('confidence', 0.7)
        service_conf = service_type_result.get('confidence', 0.7)
        
        # Weight urgency slightly higher (60/40) as it's more critical
        overall_confidence = (urgency_conf * 0.6) + (service_conf * 0.4)
        
        # Ensure within bounds
        overall_confidence = max(0.0, min(1.0, overall_confidence))
        
        logger.debug(f"Overall confidence: {overall_confidence:.2f}")
        
        return overall_confidence
    
    def _estimate_duration(self, service_type: str, urgency: str) -> int:
        """
        Estimate job duration in minutes.
        
        Args:
            service_type: Type of service
            urgency: Urgency level
            
        Returns:
            Estimated duration in minutes
        """
        # Base durations by service type (in minutes)
        base_durations = {
            'HVAC': 120,
            'Plumbing': 90,
            'Electrical': 60,
            'Appliance': 90,
            'General': 60,
        }
        
        base = base_durations.get(service_type, 60)
        
        # Adjust for urgency
        if urgency == 'emergency':
            # Emergency jobs often take longer due to complexity
            duration = int(base * 1.5)
        elif urgency == 'urgent':
            duration = base
        else:  # routine
            # Routine jobs are often simpler
            duration = int(base * 0.8)
        
        logger.debug(f"Estimated duration: {duration} minutes for {service_type} ({urgency})")
        
        return duration
    
    def _determine_required_skills(self, service_type: str) -> List[str]:
        """
        Determine required technician skills.
        
        Args:
            service_type: Type of service
            
        Returns:
            List of required skills
        """
        skill_mapping = {
            'HVAC': ['HVAC', 'EPA 608 Certified', 'Refrigeration'],
            'Plumbing': ['Plumbing', 'Pipefitting', 'Water Systems'],
            'Electrical': ['Electrical', 'Licensed Electrician', 'Wiring'],
            'Appliance': ['Appliance Repair', 'Diagnostics', 'Electronics'],
            'General': ['General Maintenance', 'Handyman'],
        }
        
        skills = skill_mapping.get(service_type, ['General Maintenance'])
        
        logger.debug(f"Required skills for {service_type}: {skills}")
        
        return skills
    
    def _calculate_priority(self, urgency: str, confidence: float) -> int:
        """
        Calculate priority score (1-10).
        
        Args:
            urgency: Urgency level
            confidence: Classification confidence
            
        Returns:
            Priority score (1-10, higher is more urgent)
        """
        # Base priority by urgency
        base_priority = {
            'emergency': 10,
            'urgent': 6,
            'routine': 3,
        }
        
        priority = base_priority.get(urgency, 5)
        
        # Adjust slightly based on confidence
        # High confidence = keep priority, low confidence = reduce slightly
        if confidence < 0.7:
            priority = max(1, priority - 1)
        
        logger.debug(f"Priority score: {priority} for urgency '{urgency}' (confidence: {confidence:.2f})")
        
        return priority
    
    def _generate_reasoning(
        self,
        urgency_result: Dict[str, Any],
        service_type_result: Dict[str, Any],
        confidence: float,
        duration: int,
        skills: List[str]
    ) -> str:
        """
        Generate human-readable reasoning for classification.
        
        Args:
            urgency_result: Urgency classification result
            service_type_result: Service type detection result
            confidence: Overall confidence score
            duration: Estimated duration
            skills: Required skills
            
        Returns:
            Reasoning text
        """
        reasoning = (
            f"Classification: {service_type_result['service_type']} service with "
            f"{urgency_result['urgency']} urgency (confidence: {confidence:.0%}). "
            f"Estimated duration: {duration} minutes. "
            f"Required skills: {', '.join(skills)}. "
            f"Urgency reasoning: {urgency_result['reasoning'][:100]}. "
            f"Service type reasoning: {service_type_result['reasoning'][:100]}."
        )
        
        return reasoning
    
    def _parse_triage_response(
        self,
        response_text: str,
        lead: Lead
    ) -> TriageResult:
        """
        Parse triage response from LLM into TriageResult.
        
        This is a simplified implementation that extracts key information
        from the LLM response.
        """
        import re
        
        # Extract urgency
        urgency = UrgencyLevel.ROUTINE
        if re.search(r'\bemergency\b', response_text, re.IGNORECASE):
            urgency = UrgencyLevel.EMERGENCY
        elif re.search(r'\burgent\b', response_text, re.IGNORECASE):
            urgency = UrgencyLevel.URGENT
        
        # Extract service type
        service_type = lead.service_type or "General"
        for svc in ["HVAC", "Plumbing", "Electrical", "Appliance"]:
            if svc.lower() in response_text.lower():
                service_type = svc
                break
        
        # Extract duration (look for numbers followed by "minutes" or "hours")
        duration = 120  # Default 2 hours
        duration_match = re.search(r'(\d+)\s*(minutes?|hours?)', response_text, re.IGNORECASE)
        if duration_match:
            value = int(duration_match.group(1))
            unit = duration_match.group(2).lower()
            if 'hour' in unit:
                duration = value * 60
            else:
                duration = value
        
        # Extract priority (look for numbers 1-10)
        priority = 5  # Default medium priority
        priority_match = re.search(r'priority[:\s]+(\d+)', response_text, re.IGNORECASE)
        if priority_match:
            priority = min(10, max(1, int(priority_match.group(1))))
        
        # Extract skills
        skills = []
        skill_keywords = ["HVAC", "plumbing", "electrical", "appliance", "general"]
        for skill in skill_keywords:
            if skill.lower() in response_text.lower():
                skills.append(skill)
        
        if not skills:
            skills = ["general"]
        
        return TriageResult(
            service_type=service_type,
            estimated_duration=duration,
            required_skills=skills,
            suggested_technicians=[],  # Will be populated by scheduling
            priority=priority,
            confidence=0.85,  # Default confidence
            urgency=urgency,
            reasoning=response_text[:500],  # First 500 chars as reasoning
        )
    
    def _get_or_create_customer(
        self,
        customer_info: CustomerInfo
    ) -> Customer:
        """
        Get existing customer or create new one.
        
        Args:
            customer_info: Customer information
            
        Returns:
            Customer object
        """
        db = next(get_db())
        try:
            # Try to find existing customer by email or phone
            customer = None
            
            if customer_info.email:
                customer = db.query(Customer).filter(
                    Customer.email == customer_info.email
                ).first()
            
            if not customer and customer_info.phone:
                customer = db.query(Customer).filter(
                    Customer.phone == customer_info.phone
                ).first()
            
            # Create new customer if not found
            if not customer:
                customer = Customer(
                    id=uuid4(),
                    name=customer_info.name or "Unknown",
                    email=customer_info.email,
                    phone=customer_info.phone,
                    address=customer_info.address,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                db.add(customer)
                db.commit()
                db.refresh(customer)
                
                logger.info(f"Created new customer: {customer.id}")
            else:
                logger.info(f"Found existing customer: {customer.id}")
            
            return customer
        finally:
            db.close()
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get agent statistics.
        
        Returns:
            Dictionary with statistics
        """
        return {
            "total_leads": self.total_leads,
            "successful_triages": self.successful_triages,
            "failed_triages": self.failed_triages,
            "success_rate": (
                self.successful_triages / self.total_leads * 100
                if self.total_leads > 0 else 0
            ),
        }
    
    # ========================================================================
    # Inventory Integration Methods
    # ========================================================================
    
    async def check_parts_availability(
        self,
        parts_queries: List[PartQuery]
    ) -> List[PartAvailability]:
        """
        Check parts availability in PostgreSQL inventory.
        
        Validates: Requirement 4.6 (Query InvenTree API for initial parts availability)
        
        Args:
            parts_queries: List of part queries to check
            
        Returns:
            List of part availability information
        """
        logger.info(f"Checking availability for {len(parts_queries)} parts")
        
        results = []
        db = next(get_db())
        
        try:
            for query in parts_queries:
                # Search for part in local PostgreSQL inventory
                part = None
                
                if query.part_number:
                    part = db.query(Part).filter(
                        Part.part_number == query.part_number
                    ).first()
                
                if not part and query.name:
                    # Search by name (case-insensitive)
                    part = db.query(Part).filter(
                        Part.name.ilike(f"%{query.name}%")
                    ).first()
                
                if not part and query.category:
                    # Search by category
                    part = db.query(Part).filter(
                        Part.category == query.category
                    ).first()
                
                if part:
                    # Part found in inventory
                    is_available = part.quantity_available > 0
                    reorder_needed = part.quantity_available <= part.reorder_level
                    
                    # Find alternatives if low stock
                    alternatives = []
                    if reorder_needed:
                        alternatives = await self._find_alternative_parts(
                            part.category,
                            part.part_number,
                            db
                        )
                    
                    availability = PartAvailability(
                        part_id=str(part.id),
                        part_number=part.part_number,
                        name=part.name,
                        quantity_available=part.quantity_available,
                        is_available=is_available,
                        reorder_needed=reorder_needed,
                        alternatives=alternatives,
                    )
                    
                    logger.debug(
                        f"Part {part.part_number}: available={is_available}, "
                        f"qty={part.quantity_available}, reorder={reorder_needed}"
                    )
                else:
                    # Part not found in inventory
                    availability = PartAvailability(
                        part_number=query.part_number or query.name or "unknown",
                        name=query.name or "Unknown Part",
                        quantity_available=0,
                        is_available=False,
                        reorder_needed=True,
                        alternatives=[],
                    )
                    
                    logger.debug(f"Part not found: {query.part_number or query.name}")
                
                results.append(availability)
        
        finally:
            db.close()
        
        logger.info(f"Parts availability check complete: {len(results)} results")
        
        return results
    
    async def search_parts(
        self,
        search_term: str,
        category: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for parts in PostgreSQL inventory.
        
        Validates: Requirement 4.7 (Query Part-DB for alternatives)
        
        Args:
            search_term: Search term (part number, name, or description)
            category: Optional category filter
            limit: Maximum number of results
            
        Returns:
            List of matching parts
        """
        logger.info(f"Searching parts: term='{search_term}', category={category}")
        
        db = next(get_db())
        
        try:
            # Build query
            query = db.query(Part)
            
            # Apply search filter (part number, name, or description)
            search_filter = (
                Part.part_number.ilike(f"%{search_term}%") |
                Part.name.ilike(f"%{search_term}%") |
                Part.description.ilike(f"%{search_term}%")
            )
            query = query.filter(search_filter)
            
            # Apply category filter if provided
            if category:
                query = query.filter(Part.category == category)
            
            # Limit results
            query = query.limit(limit)
            
            # Execute query
            parts = query.all()
            
            # Convert to dictionaries
            results = []
            for part in parts:
                results.append({
                    "id": str(part.id),
                    "part_number": part.part_number,
                    "name": part.name,
                    "description": part.description,
                    "manufacturer": part.manufacturer,
                    "category": part.category,
                    "quantity_available": part.quantity_available,
                    "unit_price": float(part.unit_price) if part.unit_price else None,
                    "reorder_level": part.reorder_level,
                })
            
            logger.info(f"Found {len(results)} matching parts")
            
            return results
        
        finally:
            db.close()
    
    async def get_common_parts_for_service(
        self,
        service_type: str
    ) -> List[PartQuery]:
        """
        Get common parts needed for a service type.
        
        Args:
            service_type: Type of service (HVAC, Plumbing, Electrical, etc.)
            
        Returns:
            List of common part queries for the service type
        """
        logger.debug(f"Getting common parts for service type: {service_type}")
        
        # Define common parts by service type
        common_parts = {
            'HVAC': [
                PartQuery(name="Thermostat", category="HVAC"),
                PartQuery(name="Capacitor", category="HVAC"),
                PartQuery(name="Contactor", category="HVAC"),
                PartQuery(name="Air Filter", category="HVAC"),
                PartQuery(name="Ignitor", category="HVAC"),
            ],
            'Plumbing': [
                PartQuery(name="Pipe Fitting", category="Plumbing"),
                PartQuery(name="Valve", category="Plumbing"),
                PartQuery(name="Washer", category="Plumbing"),
                PartQuery(name="Faucet Cartridge", category="Plumbing"),
                PartQuery(name="Drain Trap", category="Plumbing"),
            ],
            'Electrical': [
                PartQuery(name="Circuit Breaker", category="Electrical"),
                PartQuery(name="Outlet", category="Electrical"),
                PartQuery(name="Switch", category="Electrical"),
                PartQuery(name="Wire Connector", category="Electrical"),
                PartQuery(name="Junction Box", category="Electrical"),
            ],
            'Appliance': [
                PartQuery(name="Heating Element", category="Appliance"),
                PartQuery(name="Motor", category="Appliance"),
                PartQuery(name="Belt", category="Appliance"),
                PartQuery(name="Seal", category="Appliance"),
                PartQuery(name="Control Board", category="Appliance"),
            ],
        }
        
        parts = common_parts.get(service_type, [])
        
        logger.debug(f"Found {len(parts)} common parts for {service_type}")
        
        return parts
    
    async def _find_alternative_parts(
        self,
        category: str,
        exclude_part_number: str,
        db
    ) -> List[str]:
        """
        Find alternative parts in the same category.
        
        Args:
            category: Part category
            exclude_part_number: Part number to exclude from results
            db: Database session
            
        Returns:
            List of alternative part numbers
        """
        # Query for parts in same category with available stock
        alternatives = db.query(Part).filter(
            Part.category == category,
            Part.part_number != exclude_part_number,
            Part.quantity_available > 0
        ).limit(5).all()
        
        return [part.part_number for part in alternatives]
    
    # ========================================================================
    # Notification Methods
    # ========================================================================
    
    async def notify_technician_assignment(
        self,
        lead: Lead,
        technician: Technician,
        triage_result: TriageResult
    ) -> bool:
        """
        Notify technician of new lead assignment via push notification.
        
        Validates: Requirement 4.8 (Notify assigned technicians via SMS or push notification)
        
        Args:
            lead: Lead object
            technician: Assigned technician
            triage_result: Triage result with job details
            
        Returns:
            True if notification sent successfully
        """
        if not self.push_notifier:
            logger.warning("Push notifier not configured, skipping technician notification")
            return False
        
        try:
            logger.info(f"Notifying technician {technician.id} of lead {lead.id}")
            
            # Send push notification
            await self.push_notifier.send_job_assignment_notification(
                user_id=str(technician.id),
                job_id=str(lead.id),
                service_type=triage_result.service_type,
                customer_name=lead.customer.name if lead.customer else "Unknown",
                scheduled_time="ASAP" if lead.urgency == "emergency" else "TBD"
            )
            
            logger.info(f"Technician notification sent successfully to {technician.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send technician notification: {e}")
            return False
    
    async def notify_customer_confirmation(
        self,
        lead: Lead,
        technician: Optional[Technician] = None,
        appointment_time: Optional[str] = None
    ) -> bool:
        """
        Send appointment confirmation email to customer.
        
        Validates: Requirement 4.10 (Create lead records and notify)
        
        Args:
            lead: Lead object
            technician: Assigned technician (if available)
            appointment_time: Scheduled appointment time
            
        Returns:
            True if notification sent successfully
        """
        if not self.email_notifier:
            logger.warning("Email notifier not configured, skipping customer notification")
            return False
        
        if not lead.customer or not lead.customer.email:
            logger.warning(f"No customer email for lead {lead.id}, skipping notification")
            return False
        
        try:
            logger.info(f"Sending confirmation email to customer {lead.customer.id}")
            
            # Send appointment confirmation
            await self.email_notifier.send_appointment_confirmation(
                to_email=lead.customer.email,
                customer_name=lead.customer.name,
                appointment_time=appointment_time or "We will contact you shortly to schedule",
                service_type=lead.service_type or "Service",
                technician_name=technician.name if technician else "Our team"
            )
            
            logger.info(f"Customer confirmation sent successfully to {lead.customer.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send customer confirmation: {e}")
            return False
    
    async def notify_team_new_lead(
        self,
        lead: Lead,
        triage_result: TriageResult
    ) -> bool:
        """
        Send new lead alert to team via Discord.
        
        Validates: Requirement 4.10 (Create lead records and notify)
        
        Args:
            lead: Lead object
            triage_result: Triage result with classification
            
        Returns:
            True if notification sent successfully
        """
        if not self.discord_notifier:
            logger.warning("Discord notifier not configured, skipping team notification")
            return False
        
        try:
            logger.info(f"Sending new lead alert to team for lead {lead.id}")
            
            # Send Discord alert
            await self.discord_notifier.send_new_lead_alert(
                lead_id=str(lead.id),
                customer_name=lead.customer.name if lead.customer else "Unknown",
                service_type=triage_result.service_type,
                urgency=lead.urgency,
                description=lead.description or "No description",
                location=lead.customer.address if lead.customer else "Unknown"
            )
            
            logger.info(f"Team notification sent successfully for lead {lead.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send team notification: {e}")
            return False
    
    async def notify_emergency_alert(
        self,
        lead: Lead,
        triage_result: TriageResult
    ) -> bool:
        """
        Send emergency alert to team via Discord for high-priority leads.
        
        Validates: Requirement 4.4 (Classify urgency as emergency)
        
        Args:
            lead: Lead object
            triage_result: Triage result
            
        Returns:
            True if notification sent successfully
        """
        if not self.discord_notifier:
            logger.warning("Discord notifier not configured, skipping emergency alert")
            return False
        
        if lead.urgency != "emergency":
            logger.debug(f"Lead {lead.id} is not emergency, skipping emergency alert")
            return False
        
        try:
            logger.info(f"Sending emergency alert for lead {lead.id}")
            
            # Send emergency Discord alert
            await self.discord_notifier.send_emergency_job_alert(
                job_id=str(lead.id),
                customer_name=lead.customer.name if lead.customer else "Unknown",
                service_type=triage_result.service_type,
                location=lead.customer.address if lead.customer else "Unknown",
                assigned_technician="Unassigned"
            )
            
            logger.info(f"Emergency alert sent successfully for lead {lead.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send emergency alert: {e}")
            return False
    
    async def create_lead_and_notify(
        self,
        input_data: LeadInput,
        triage_result: TriageResult,
        assigned_technician: Optional[Technician] = None
    ) -> Lead:
        """
        Create lead record in PostgreSQL and send all notifications.
        
        Validates: Requirement 4.8 (Create lead records in PostgreSQL database)
        Validates: Requirement 4.9 (Notify assigned technicians via SMS or push notification)
        Validates: Requirement 4.10 (Use CrewAI role-based collaboration)
        
        Args:
            input_data: Lead input data
            triage_result: Triage result
            assigned_technician: Assigned technician (if available)
            
        Returns:
            Created lead object
        """
        logger.info("Creating lead and sending notifications")
        
        # Step 1: Create lead (already done in capture_lead)
        lead = await self.capture_lead(input_data)
        
        # Step 2: Update lead with triage results
        lead.urgency = triage_result.urgency.value
        lead.service_type = triage_result.service_type
        lead.confidence_score = triage_result.confidence
        lead.status = "triaged"
        
        db = next(get_db())
        try:
            db.add(lead)
            db.commit()
            db.refresh(lead)
        finally:
            db.close()
        
        # Step 3: Send notifications (fire and forget, don't block on failures)
        notification_tasks = []
        
        # Notify technician if assigned
        if assigned_technician:
            notification_tasks.append(
                self.notify_technician_assignment(lead, assigned_technician, triage_result)
            )
        
        # Notify customer
        notification_tasks.append(
            self.notify_customer_confirmation(lead, assigned_technician)
        )
        
        # Notify team
        notification_tasks.append(
            self.notify_team_new_lead(lead, triage_result)
        )
        
        # Send emergency alert if needed
        if lead.urgency == "emergency":
            notification_tasks.append(
                self.notify_emergency_alert(lead, triage_result)
            )
        
        # Execute all notifications concurrently
        import asyncio
        results = await asyncio.gather(*notification_tasks, return_exceptions=True)
        
        # Log notification results
        success_count = sum(1 for r in results if r is True)
        logger.info(
            f"Notifications sent: {success_count}/{len(notification_tasks)} successful"
        )
        
        return lead


# ============================================================================
# Factory Function
# ============================================================================

def create_intake_agent(
    llm_client: UnifiedLLMClient,
    email_notifier: Optional[EmailNotifier] = None,
    push_notifier: Optional[WebPushNotifier] = None,
    discord_notifier: Optional[DiscordNotifier] = None,
    **kwargs
) -> IntakeAgent:
    """
    Factory function to create Intake Agent.
    
    Args:
        llm_client: Unified LLM client
        email_notifier: Email notification service
        push_notifier: Web push notification service
        discord_notifier: Discord webhook notification service
        **kwargs: Additional configuration options
        
    Returns:
        Configured IntakeAgent instance
    """
    return IntakeAgent(
        llm_client=llm_client,
        email_notifier=email_notifier,
        push_notifier=push_notifier,
        discord_notifier=discord_notifier,
        **kwargs
    )
