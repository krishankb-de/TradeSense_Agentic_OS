"""Lead repository."""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.models import Lead
from backend.db.repositories.base import BaseRepository


class LeadRepository(BaseRepository[Lead]):
    """Repository for lead operations."""

    def __init__(self, db: Session):
        """Initialize lead repository."""
        super().__init__(Lead, db)

    def get_by_customer(self, customer_id: UUID, skip: int = 0, limit: int = 100) -> List[Lead]:
        """
        Get leads by customer ID.

        Args:
            customer_id: Customer ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of leads for the customer
        """
        stmt = (
            select(Lead)
            .where(Lead.customer_id == customer_id)
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def get_by_status(self, status: str, skip: int = 0, limit: int = 100) -> List[Lead]:
        """
        Get leads by status.

        Args:
            status: Lead status (new, contacted, converted, closed)
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of leads with the specified status
        """
        stmt = (
            select(Lead)
            .where(Lead.status == status)
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def get_by_urgency(self, urgency: str, skip: int = 0, limit: int = 100) -> List[Lead]:
        """
        Get leads by urgency.

        Args:
            urgency: Lead urgency (emergency, urgent, routine)
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of leads with the specified urgency
        """
        stmt = (
            select(Lead)
            .where(Lead.urgency == urgency)
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def get_by_source(self, source: str, skip: int = 0, limit: int = 100) -> List[Lead]:
        """
        Get leads by source.

        Args:
            source: Lead source (voice, sms, web)
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of leads from the specified source
        """
        stmt = (
            select(Lead)
            .where(Lead.source == source)
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())
