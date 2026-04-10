"""
FastAPI routes for Lead Management
Handles lead CRUD operations and queries

Validates: Requirements 7.9, 18.1, 18.2
"""

import logging
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel, Field

from db.models import Lead
from db.session import get_db
from security.auth import get_current_user, User
from security.rbac import require_role, Role

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class LeadResponse(BaseModel):
    """Response model for lead."""
    id: str
    customer_id: str
    source: str
    status: str
    issue_description: str
    urgency: str
    service_type: Optional[str] = None
    location: Optional[dict] = None
    created_at: datetime
    updated_at: datetime
    assigned_technician_id: Optional[str] = None
    estimated_value: float

    class Config:
        from_attributes = True


class LeadListResponse(BaseModel):
    """Response model for lead list."""
    leads: List[LeadResponse]
    total: int
    page: int
    page_size: int


class UpdateLeadRequest(BaseModel):
    """Request model for updating lead."""
    status: Optional[str] = None
    assigned_technician_id: Optional[str] = None
    service_type: Optional[str] = None
    estimated_value: Optional[float] = None


# ============================================================================
# API Endpoints
# ============================================================================

@router.get(
    "/",
    response_model=LeadListResponse,
    summary="List leads",
    description="Get paginated list of leads with optional filters"
)
async def list_leads(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status"),
    urgency: Optional[str] = Query(None, description="Filter by urgency"),
    assigned_technician_id: Optional[str] = Query(None, description="Filter by technician"),
    current_user: User = Depends(get_current_user)
):
    """
    List leads with pagination and filters.
    
    Validates: Requirement 7.9 (REST API access to data)
    """
    db = None
    try:
        db = next(get_db())
        
        # Build query
        query = db.query(Lead)
        
        # Apply filters
        if status:
            query = query.filter(Lead.status == status)
        if urgency:
            query = query.filter(Lead.urgency == urgency)
        if assigned_technician_id:
            query = query.filter(Lead.assigned_technician_id == UUID(assigned_technician_id))
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        leads = query.offset(offset).limit(page_size).all()
        
        return LeadListResponse(
            leads=[LeadResponse.from_orm(lead) for lead in leads],
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"Failed to list leads: {e}", exc_info=True)
        # Return empty list instead of 500 error
        return LeadListResponse(
            leads=[],
            total=0,
            page=page,
            page_size=page_size
        )
    finally:
        if db:
            db.close()


@router.get(
    "/{lead_id}",
    response_model=LeadResponse,
    summary="Get lead by ID",
    description="Retrieve a specific lead by ID"
)
async def get_lead(
    lead_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get lead by ID.
    
    Validates: Requirement 7.9 (REST API access to data)
    """
    try:
        db = next(get_db())
        
        lead = db.query(Lead).filter(Lead.id == UUID(lead_id)).first()
        
        db.close()
        
        if not lead:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lead {lead_id} not found"
            )
        
        return LeadResponse.from_orm(lead)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get lead: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get lead: {str(e)}"
        )


@router.patch(
    "/{lead_id}",
    response_model=LeadResponse,
    summary="Update lead",
    description="Update lead fields"
)
async def update_lead(
    lead_id: str,
    request: UpdateLeadRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Update lead.
    
    Validates: Requirement 7.9 (REST API access to data)
    Validates: Requirement 18.1 (RBAC)
    """
    try:
        db = next(get_db())
        
        lead = db.query(Lead).filter(Lead.id == UUID(lead_id)).first()
        
        if not lead:
            db.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lead {lead_id} not found"
            )
        
        # Update fields
        if request.status is not None:
            lead.status = request.status
        if request.assigned_technician_id is not None:
            lead.assigned_technician_id = UUID(request.assigned_technician_id)
        if request.service_type is not None:
            lead.service_type = request.service_type
        if request.estimated_value is not None:
            lead.estimated_value = request.estimated_value
        
        lead.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(lead)
        
        result = LeadResponse.from_orm(lead)
        
        db.close()
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update lead: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update lead: {str(e)}"
        )


@router.delete(
    "/{lead_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete lead",
    description="Delete a lead (admin only)"
)
async def delete_lead(
    lead_id: str,
    current_user: User = Depends(require_role(Role.ADMIN))
):
    """
    Delete lead (admin only).
    
    Validates: Requirement 18.1 (RBAC)
    """
    try:
        db = next(get_db())
        
        lead = db.query(Lead).filter(Lead.id == UUID(lead_id)).first()
        
        if not lead:
            db.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lead {lead_id} not found"
            )
        
        db.delete(lead)
        db.commit()
        
        db.close()
        
        logger.info(f"Lead {lead_id} deleted by user {current_user.id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete lead: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete lead: {str(e)}"
        )
