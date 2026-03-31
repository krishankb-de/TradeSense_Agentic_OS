"""
FastAPI routes for Intake Agent
Handles lead capture, triage, and notification endpoints

Validates: Requirements 4.1, 4.2, 4.8, 4.10
"""

import logging
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field

from agents.intake import (
    IntakeAgent,
    LeadInput,
    LeadSource,
    UrgencyLevel,
    CustomerInfo,
    GeoLocation,
    TriageResult,
    PartQuery,
    PartAvailability,
    create_intake_agent,
)
from llm.unified_client import create_unified_llm_client
from notifications import (
    create_email_notifier,
    create_web_push_notifier,
    create_discord_notifier,
)
from db.models import Lead, Technician
from db.session import get_db
import os

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/intake", tags=["intake"])


# ============================================================================
# Request/Response Models
# ============================================================================

class CaptureLeadRequest(BaseModel):
    """Request model for lead capture."""
    source: LeadSource = Field(..., description="Lead source channel")
    customer_name: Optional[str] = Field(None, description="Customer name")
    customer_email: Optional[str] = Field(None, description="Customer email")
    customer_phone: Optional[str] = Field(None, description="Customer phone")
    customer_address: Optional[str] = Field(None, description="Customer address")
    issue_description: str = Field(..., description="Description of the issue")
    urgency: Optional[UrgencyLevel] = Field(None, description="Urgency level (if known)")
    location: Optional[GeoLocation] = Field(None, description="Service location")
    raw_text: Optional[str] = Field(None, description="Raw transcription/text")


class CaptureLeadResponse(BaseModel):
    """Response model for lead capture."""
    lead_id: str = Field(..., description="Created lead ID")
    customer_id: str = Field(..., description="Customer ID")
    status: str = Field(..., description="Lead status")
    message: str = Field(..., description="Success message")


class TriageLeadRequest(BaseModel):
    """Request model for lead triage."""
    lead_id: str = Field(..., description="Lead ID to triage")


class TriageLeadResponse(BaseModel):
    """Response model for lead triage."""
    lead_id: str = Field(..., description="Lead ID")
    triage_result: TriageResult = Field(..., description="Triage classification result")
    message: str = Field(..., description="Success message")


class CreateLeadAndNotifyRequest(BaseModel):
    """Request model for creating lead and sending notifications."""
    source: LeadSource = Field(..., description="Lead source channel")
    customer_name: Optional[str] = Field(None, description="Customer name")
    customer_email: Optional[str] = Field(None, description="Customer email")
    customer_phone: Optional[str] = Field(None, description="Customer phone")
    customer_address: Optional[str] = Field(None, description="Customer address")
    issue_description: str = Field(..., description="Description of the issue")
    urgency: Optional[UrgencyLevel] = Field(None, description="Urgency level (if known)")
    location: Optional[GeoLocation] = Field(None, description="Service location")
    raw_text: Optional[str] = Field(None, description="Raw transcription/text")
    assigned_technician_id: Optional[str] = Field(None, description="Assigned technician ID")


class CreateLeadAndNotifyResponse(BaseModel):
    """Response model for creating lead and sending notifications."""
    lead_id: str = Field(..., description="Created lead ID")
    customer_id: str = Field(..., description="Customer ID")
    triage_result: TriageResult = Field(..., description="Triage classification result")
    notifications_sent: int = Field(..., description="Number of notifications sent")
    status: str = Field(..., description="Lead status")
    message: str = Field(..., description="Success message")


class CheckPartsRequest(BaseModel):
    """Request model for checking parts availability."""
    parts: List[PartQuery] = Field(..., description="List of parts to check")


class CheckPartsResponse(BaseModel):
    """Response model for parts availability."""
    parts: List[PartAvailability] = Field(..., description="Parts availability information")
    available_count: int = Field(..., description="Number of available parts")
    total_count: int = Field(..., description="Total number of parts checked")


# ============================================================================
# Dependency Injection
# ============================================================================

def get_intake_agent() -> IntakeAgent:
    """
    Dependency injection for Intake Agent.
    
    Returns:
        Configured IntakeAgent instance
    """
    # Create LLM client
    llm_client = create_unified_llm_client()
    
    # Create notification services (optional)
    email_notifier = None
    push_notifier = None
    discord_notifier = None
    
    # Email notifier
    if os.getenv("SMTP_HOST"):
        try:
            email_notifier = create_email_notifier(
                smtp_host=os.getenv("SMTP_HOST"),
                smtp_port=int(os.getenv("SMTP_PORT", "587")),
                smtp_username=os.getenv("SMTP_USERNAME"),
                smtp_password=os.getenv("SMTP_PASSWORD"),
                from_email=os.getenv("FROM_EMAIL", "noreply@tradesense.com"),
                from_name=os.getenv("FROM_NAME", "TradeSense"),
                use_tls=os.getenv("SMTP_USE_TLS", "true").lower() == "true",
            )
            logger.info("Email notifier configured")
        except Exception as e:
            logger.warning(f"Failed to configure email notifier: {e}")
    
    # Web push notifier
    if os.getenv("VAPID_PRIVATE_KEY"):
        try:
            push_notifier = create_web_push_notifier(
                vapid_private_key=os.getenv("VAPID_PRIVATE_KEY"),
                vapid_public_key=os.getenv("VAPID_PUBLIC_KEY"),
                vapid_subject=os.getenv("VAPID_SUBJECT", "mailto:admin@tradesense.com"),
            )
            logger.info("Web push notifier configured")
        except Exception as e:
            logger.warning(f"Failed to configure web push notifier: {e}")
    
    # Discord notifier
    if os.getenv("DISCORD_WEBHOOK_URL"):
        try:
            discord_notifier = create_discord_notifier(
                webhook_url=os.getenv("DISCORD_WEBHOOK_URL"),
                username=os.getenv("DISCORD_BOT_USERNAME", "TradeSense Bot"),
                avatar_url=os.getenv("DISCORD_BOT_AVATAR_URL"),
            )
            logger.info("Discord notifier configured")
        except Exception as e:
            logger.warning(f"Failed to configure Discord notifier: {e}")
    
    # Create intake agent
    return create_intake_agent(
        llm_client=llm_client,
        email_notifier=email_notifier,
        push_notifier=push_notifier,
        discord_notifier=discord_notifier,
    )


# ============================================================================
# API Endpoints
# ============================================================================

@router.post(
    "/capture",
    response_model=CaptureLeadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Capture new lead",
    description="Capture a new lead from voice/SMS/web source and create lead record"
)
async def capture_lead(
    request: CaptureLeadRequest,
    agent: IntakeAgent = Depends(get_intake_agent)
) -> CaptureLeadResponse:
    """
    Capture new lead from voice/SMS/web source.
    
    Validates: Requirement 4.1 (Lead capture from voice/SMS/web)
    """
    try:
        logger.info(f"Capturing lead from {request.source}")
        
        # Build lead input
        lead_input = LeadInput(
            source=request.source,
            customer_info=CustomerInfo(
                name=request.customer_name,
                email=request.customer_email,
                phone=request.customer_phone,
                address=request.customer_address,
            ),
            issue_description=request.issue_description,
            urgency=request.urgency,
            location=request.location,
            raw_text=request.raw_text,
        )
        
        # Capture lead
        lead = await agent.capture_lead(lead_input)
        
        return CaptureLeadResponse(
            lead_id=str(lead.id),
            customer_id=str(lead.customer_id),
            status=lead.status,
            message=f"Lead captured successfully from {request.source}"
        )
        
    except Exception as e:
        logger.error(f"Failed to capture lead: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to capture lead: {str(e)}"
        )


@router.post(
    "/triage",
    response_model=TriageLeadResponse,
    summary="Triage lead",
    description="Classify urgency and service type for a lead"
)
async def triage_lead(
    request: TriageLeadRequest,
    agent: IntakeAgent = Depends(get_intake_agent)
) -> TriageLeadResponse:
    """
    Triage lead and classify urgency/service type.
    
    Validates: Requirement 4.3, 4.4 (Classify urgency within 60 seconds)
    """
    try:
        logger.info(f"Triaging lead {request.lead_id}")
        
        # Get lead from database
        db = next(get_db())
        try:
            lead = db.query(Lead).filter(Lead.id == UUID(request.lead_id)).first()
            if not lead:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Lead {request.lead_id} not found"
                )
        finally:
            db.close()
        
        # Triage lead
        triage_result = await agent.triage_lead(lead)
        
        return TriageLeadResponse(
            lead_id=str(lead.id),
            triage_result=triage_result,
            message=f"Lead triaged successfully: {triage_result.service_type} ({triage_result.urgency.value})"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to triage lead: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to triage lead: {str(e)}"
        )


@router.post(
    "/create-and-notify",
    response_model=CreateLeadAndNotifyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create lead and send notifications",
    description="Create lead, triage, and send notifications to customer and technicians"
)
async def create_lead_and_notify(
    request: CreateLeadAndNotifyRequest,
    agent: IntakeAgent = Depends(get_intake_agent)
) -> CreateLeadAndNotifyResponse:
    """
    Create lead record and send all notifications.
    
    Validates: Requirement 4.8 (Create lead records in PostgreSQL database)
    Validates: Requirement 4.9 (Notify assigned technicians via SMS or push notification)
    Validates: Requirement 4.10 (Use CrewAI role-based collaboration)
    """
    try:
        logger.info(f"Creating lead and sending notifications from {request.source}")
        
        # Build lead input
        lead_input = LeadInput(
            source=request.source,
            customer_info=CustomerInfo(
                name=request.customer_name,
                email=request.customer_email,
                phone=request.customer_phone,
                address=request.customer_address,
            ),
            issue_description=request.issue_description,
            urgency=request.urgency,
            location=request.location,
            raw_text=request.raw_text,
        )
        
        # Capture and triage lead
        lead = await agent.capture_lead(lead_input)
        triage_result = await agent.triage_lead(lead)
        
        # Get assigned technician if provided
        assigned_technician = None
        if request.assigned_technician_id:
            db = next(get_db())
            try:
                assigned_technician = db.query(Technician).filter(
                    Technician.id == UUID(request.assigned_technician_id)
                ).first()
                if not assigned_technician:
                    logger.warning(f"Technician {request.assigned_technician_id} not found")
            finally:
                db.close()
        
        # Send notifications
        notification_count = 0
        
        # Notify technician if assigned
        if assigned_technician:
            success = await agent.notify_technician_assignment(lead, assigned_technician, triage_result)
            if success:
                notification_count += 1
        
        # Notify customer
        success = await agent.notify_customer_confirmation(lead, assigned_technician)
        if success:
            notification_count += 1
        
        # Notify team
        success = await agent.notify_team_new_lead(lead, triage_result)
        if success:
            notification_count += 1
        
        # Send emergency alert if needed
        if lead.urgency == "emergency":
            success = await agent.notify_emergency_alert(lead, triage_result)
            if success:
                notification_count += 1
        
        return CreateLeadAndNotifyResponse(
            lead_id=str(lead.id),
            customer_id=str(lead.customer_id),
            triage_result=triage_result,
            notifications_sent=notification_count,
            status=lead.status,
            message=f"Lead created and {notification_count} notifications sent"
        )
        
    except Exception as e:
        logger.error(f"Failed to create lead and notify: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create lead and notify: {str(e)}"
        )


@router.post(
    "/check-parts",
    response_model=CheckPartsResponse,
    summary="Check parts availability",
    description="Check availability of parts in inventory"
)
async def check_parts_availability(
    request: CheckPartsRequest,
    agent: IntakeAgent = Depends(get_intake_agent)
) -> CheckPartsResponse:
    """
    Check parts availability in inventory.
    
    Validates: Requirement 4.6 (Query InvenTree API for initial parts availability)
    """
    try:
        logger.info(f"Checking availability for {len(request.parts)} parts")
        
        # Check parts availability
        parts_availability = await agent.check_parts_availability(request.parts)
        
        # Count available parts
        available_count = sum(1 for p in parts_availability if p.is_available)
        
        return CheckPartsResponse(
            parts=parts_availability,
            available_count=available_count,
            total_count=len(parts_availability)
        )
        
    except Exception as e:
        logger.error(f"Failed to check parts availability: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check parts availability: {str(e)}"
        )


@router.get(
    "/statistics",
    summary="Get intake agent statistics",
    description="Get statistics about lead capture and triage performance"
)
async def get_statistics(
    agent: IntakeAgent = Depends(get_intake_agent)
) -> dict:
    """Get intake agent statistics."""
    return agent.get_statistics()
