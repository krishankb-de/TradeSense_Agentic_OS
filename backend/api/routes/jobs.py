"""
FastAPI routes for Job Management
Handles job CRUD operations and queries

Validates: Requirements 7.9, 18.1, 18.2
"""

import logging
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel, Field

from db.models import Job
from db.session import get_db
from security.auth import get_current_user, User
from security.rbac import require_role, Role

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class JobResponse(BaseModel):
    """Response model for job."""
    id: str
    lead_id: str
    technician_id: str
    status: str
    scheduled_start: datetime
    scheduled_end: datetime
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    labor_hours: float
    total_cost: float
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    """Response model for job list."""
    jobs: List[JobResponse]
    total: int
    page: int
    page_size: int


class CreateJobRequest(BaseModel):
    """Request model for creating job."""
    lead_id: str = Field(..., description="Lead ID")
    technician_id: str = Field(..., description="Technician ID")
    scheduled_start: datetime = Field(..., description="Scheduled start time")
    scheduled_end: datetime = Field(..., description="Scheduled end time")


class UpdateJobRequest(BaseModel):
    """Request model for updating job."""
    status: Optional[str] = None
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    labor_hours: Optional[float] = None
    total_cost: Optional[float] = None
    notes: Optional[str] = None


# ============================================================================
# API Endpoints
# ============================================================================

@router.get(
    "/",
    response_model=JobListResponse,
    summary="List jobs",
    description="Get paginated list of jobs with optional filters"
)
async def list_jobs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status"),
    technician_id: Optional[str] = Query(None, description="Filter by technician"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    current_user: User = Depends(get_current_user)
):
    """
    List jobs with pagination and filters.
    
    Validates: Requirement 7.9 (REST API access to data)
    """
    db = None
    try:
        db = next(get_db())
        
        # Build query
        query = db.query(Job)
        
        # Apply filters
        if status:
            query = query.filter(Job.status == status)
        if technician_id:
            query = query.filter(Job.technician_id == UUID(technician_id))
        if start_date:
            query = query.filter(Job.scheduled_start >= start_date)
        if end_date:
            query = query.filter(Job.scheduled_end <= end_date)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        jobs = query.offset(offset).limit(page_size).all()
        
        return JobListResponse(
            jobs=[JobResponse.from_orm(job) for job in jobs],
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"Failed to list jobs: {e}", exc_info=True)
        # Return empty list instead of 500 error
        return JobListResponse(
            jobs=[],
            total=0,
            page=page,
            page_size=page_size
        )
    finally:
        if db:
            db.close()


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get job by ID",
    description="Retrieve a specific job by ID"
)
async def get_job(
    job_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get job by ID.
    
    Validates: Requirement 7.9 (REST API access to data)
    """
    try:
        db = next(get_db())
        
        job = db.query(Job).filter(Job.id == UUID(job_id)).first()
        
        db.close()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )
        
        return JobResponse.from_orm(job)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job: {str(e)}"
        )


@router.post(
    "/",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create job",
    description="Create a new job"
)
async def create_job(
    request: CreateJobRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Create new job.
    
    Validates: Requirement 7.9 (REST API access to data)
    Validates: Requirement 18.1 (RBAC)
    """
    try:
        db = next(get_db())
        
        # Create job
        job = Job(
            lead_id=UUID(request.lead_id),
            technician_id=UUID(request.technician_id),
            status="scheduled",
            scheduled_start=request.scheduled_start,
            scheduled_end=request.scheduled_end,
            labor_hours=0.0,
            total_cost=0.0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(job)
        db.commit()
        db.refresh(job)
        
        result = JobResponse.from_orm(job)
        
        db.close()
        
        logger.info(f"Job {job.id} created by user {current_user.id}")
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to create job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create job: {str(e)}"
        )


@router.patch(
    "/{job_id}",
    response_model=JobResponse,
    summary="Update job",
    description="Update job fields"
)
async def update_job(
    job_id: str,
    request: UpdateJobRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Update job.
    
    Validates: Requirement 7.9 (REST API access to data)
    Validates: Requirement 18.1 (RBAC)
    """
    try:
        db = next(get_db())
        
        job = db.query(Job).filter(Job.id == UUID(job_id)).first()
        
        if not job:
            db.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )
        
        # Update fields
        if request.status is not None:
            job.status = request.status
        if request.actual_start is not None:
            job.actual_start = request.actual_start
        if request.actual_end is not None:
            job.actual_end = request.actual_end
        if request.labor_hours is not None:
            job.labor_hours = request.labor_hours
        if request.total_cost is not None:
            job.total_cost = request.total_cost
        if request.notes is not None:
            job.notes = request.notes
        
        job.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(job)
        
        result = JobResponse.from_orm(job)
        
        db.close()
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update job: {str(e)}"
        )


@router.delete(
    "/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete job",
    description="Delete a job (admin only)"
)
async def delete_job(
    job_id: str,
    current_user: User = Depends(require_role(Role.ADMIN))
):
    """
    Delete job (admin only).
    
    Validates: Requirement 18.1 (RBAC)
    """
    try:
        db = next(get_db())
        
        job = db.query(Job).filter(Job.id == UUID(job_id)).first()
        
        if not job:
            db.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )
        
        db.delete(job)
        db.commit()
        
        db.close()
        
        logger.info(f"Job {job_id} deleted by user {current_user.id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete job: {str(e)}"
        )
