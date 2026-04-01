"""
FastAPI routes for Technician Management
Handles technician CRUD operations and queries

Validates: Requirements 7.9, 18.1, 18.2
"""

import logging
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel, Field

from db.models import Technician
from db.session import get_db
from security.auth import get_current_user, User
from security.rbac import require_role, Role

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class TechnicianResponse(BaseModel):
    """Response model for technician."""
    id: str
    name: str
    email: str
    phone: str
    skills: List[str]
    status: str
    current_location: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TechnicianListResponse(BaseModel):
    """Response model for technician list."""
    technicians: List[TechnicianResponse]
    total: int
    page: int
    page_size: int


class CreateTechnicianRequest(BaseModel):
    """Request model for creating technician."""
    name: str = Field(..., description="Technician name")
    email: str = Field(..., description="Email address")
    phone: str = Field(..., description="Phone number")
    skills: List[str] = Field(default=[], description="List of skills")


class UpdateTechnicianRequest(BaseModel):
    """Request model for updating technician."""
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    skills: Optional[List[str]] = None
    status: Optional[str] = None
    current_location: Optional[dict] = None


# ============================================================================
# API Endpoints
# ============================================================================

@router.get(
    "/",
    response_model=TechnicianListResponse,
    summary="List technicians",
    description="Get paginated list of technicians with optional filters"
)
async def list_technicians(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status"),
    skill: Optional[str] = Query(None, description="Filter by skill"),
    current_user: User = Depends(get_current_user)
):
    """
    List technicians with pagination and filters.
    
    Validates: Requirement 7.9 (REST API access to data)
    """
    try:
        db = next(get_db())
        
        # Build query
        query = db.query(Technician)
        
        # Apply filters
        if status:
            query = query.filter(Technician.status == status)
        if skill:
            # Filter by skill (assuming skills is a JSON array)
            query = query.filter(Technician.skills.contains([skill]))
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        technicians = query.offset(offset).limit(page_size).all()
        
        db.close()
        
        return TechnicianListResponse(
            technicians=[TechnicianResponse.from_orm(tech) for tech in technicians],
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"Failed to list technicians: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list technicians: {str(e)}"
        )


@router.get(
    "/{technician_id}",
    response_model=TechnicianResponse,
    summary="Get technician by ID",
    description="Retrieve a specific technician by ID"
)
async def get_technician(
    technician_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get technician by ID.
    
    Validates: Requirement 7.9 (REST API access to data)
    """
    try:
        db = next(get_db())
        
        technician = db.query(Technician).filter(Technician.id == UUID(technician_id)).first()
        
        db.close()
        
        if not technician:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Technician {technician_id} not found"
            )
        
        return TechnicianResponse.from_orm(technician)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get technician: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get technician: {str(e)}"
        )


@router.post(
    "/",
    response_model=TechnicianResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create technician",
    description="Create a new technician (admin only)"
)
async def create_technician(
    request: CreateTechnicianRequest,
    current_user: User = Depends(require_role(Role.ADMIN))
):
    """
    Create new technician (admin only).
    
    Validates: Requirement 7.9 (REST API access to data)
    Validates: Requirement 18.1 (RBAC)
    """
    try:
        db = next(get_db())
        
        # Create technician
        technician = Technician(
            name=request.name,
            email=request.email,
            phone=request.phone,
            skills=request.skills,
            status="available",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(technician)
        db.commit()
        db.refresh(technician)
        
        result = TechnicianResponse.from_orm(technician)
        
        db.close()
        
        logger.info(f"Technician {technician.id} created by user {current_user.id}")
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to create technician: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create technician: {str(e)}"
        )


@router.patch(
    "/{technician_id}",
    response_model=TechnicianResponse,
    summary="Update technician",
    description="Update technician fields"
)
async def update_technician(
    technician_id: str,
    request: UpdateTechnicianRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Update technician.
    
    Validates: Requirement 7.9 (REST API access to data)
    Validates: Requirement 18.1 (RBAC)
    """
    try:
        db = next(get_db())
        
        technician = db.query(Technician).filter(Technician.id == UUID(technician_id)).first()
        
        if not technician:
            db.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Technician {technician_id} not found"
            )
        
        # Update fields
        if request.name is not None:
            technician.name = request.name
        if request.email is not None:
            technician.email = request.email
        if request.phone is not None:
            technician.phone = request.phone
        if request.skills is not None:
            technician.skills = request.skills
        if request.status is not None:
            technician.status = request.status
        if request.current_location is not None:
            technician.current_location = request.current_location
        
        technician.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(technician)
        
        result = TechnicianResponse.from_orm(technician)
        
        db.close()
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update technician: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update technician: {str(e)}"
        )


@router.delete(
    "/{technician_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete technician",
    description="Delete a technician (admin only)"
)
async def delete_technician(
    technician_id: str,
    current_user: User = Depends(require_role(Role.ADMIN))
):
    """
    Delete technician (admin only).
    
    Validates: Requirement 18.1 (RBAC)
    """
    try:
        db = next(get_db())
        
        technician = db.query(Technician).filter(Technician.id == UUID(technician_id)).first()
        
        if not technician:
            db.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Technician {technician_id} not found"
            )
        
        db.delete(technician)
        db.commit()
        
        db.close()
        
        logger.info(f"Technician {technician_id} deleted by user {current_user.id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete technician: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete technician: {str(e)}"
        )
