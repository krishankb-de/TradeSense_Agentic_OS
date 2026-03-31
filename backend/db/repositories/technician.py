"""Technician repository."""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.models import Technician
from backend.db.repositories.base import BaseRepository


class TechnicianRepository(BaseRepository[Technician]):
    """Repository for technician operations."""

    def __init__(self, db: Session):
        """Initialize technician repository."""
        super().__init__(Technician, db)

    def get_by_email(self, email: str) -> Optional[Technician]:
        """
        Get technician by email.

        Args:
            email: Technician email

        Returns:
            Technician or None if not found
        """
        stmt = select(Technician).where(Technician.email == email)
        return self.db.scalar(stmt)

    def get_by_status(self, status: str, skip: int = 0, limit: int = 100) -> List[Technician]:
        """
        Get technicians by status.

        Args:
            status: Technician status (available, busy, offline)
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of technicians with the specified status
        """
        stmt = (
            select(Technician)
            .where(Technician.status == status)
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def get_by_skill(self, skill: str, skip: int = 0, limit: int = 100) -> List[Technician]:
        """
        Get technicians with a specific skill.

        Args:
            skill: Skill to search for
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of technicians with the specified skill
        """
        stmt = (
            select(Technician)
            .where(Technician.skills.contains([skill]))
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def get_available(self, skip: int = 0, limit: int = 100) -> List[Technician]:
        """
        Get available technicians.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of available technicians
        """
        return self.get_by_status("available", skip, limit)
