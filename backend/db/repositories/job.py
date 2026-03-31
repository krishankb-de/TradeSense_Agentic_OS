"""Job repository."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.models import Job
from backend.db.repositories.base import BaseRepository


class JobRepository(BaseRepository[Job]):
    """Repository for job operations."""

    def __init__(self, db: Session):
        """Initialize job repository."""
        super().__init__(Job, db)

    def get_by_customer(self, customer_id: UUID, skip: int = 0, limit: int = 100) -> List[Job]:
        """
        Get jobs by customer ID.

        Args:
            customer_id: Customer ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of jobs for the customer
        """
        stmt = (
            select(Job)
            .where(Job.customer_id == customer_id)
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def get_by_technician(self, technician_id: UUID, skip: int = 0, limit: int = 100) -> List[Job]:
        """
        Get jobs by technician ID.

        Args:
            technician_id: Technician ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of jobs for the technician
        """
        stmt = (
            select(Job)
            .where(Job.technician_id == technician_id)
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def get_by_status(self, status: str, skip: int = 0, limit: int = 100) -> List[Job]:
        """
        Get jobs by status.

        Args:
            status: Job status (scheduled, in_progress, completed, cancelled)
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of jobs with the specified status
        """
        stmt = (
            select(Job)
            .where(Job.status == status)
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def get_by_priority(self, priority: str, skip: int = 0, limit: int = 100) -> List[Job]:
        """
        Get jobs by priority.

        Args:
            priority: Job priority (emergency, high, normal, low)
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of jobs with the specified priority
        """
        stmt = (
            select(Job)
            .where(Job.priority == priority)
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def get_scheduled_between(
        self, start: datetime, end: datetime, skip: int = 0, limit: int = 100
    ) -> List[Job]:
        """
        Get jobs scheduled between two dates.

        Args:
            start: Start datetime
            end: End datetime
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of jobs scheduled in the date range
        """
        stmt = (
            select(Job)
            .where(Job.scheduled_start >= start)
            .where(Job.scheduled_start <= end)
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def get_by_lead(self, lead_id: UUID) -> Optional[Job]:
        """
        Get job by lead ID.

        Args:
            lead_id: Lead ID

        Returns:
            Job or None if not found
        """
        stmt = select(Job).where(Job.lead_id == lead_id)
        return self.db.scalar(stmt)
