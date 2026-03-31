"""Customer repository."""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.models import Customer
from backend.db.repositories.base import BaseRepository


class CustomerRepository(BaseRepository[Customer]):
    """Repository for customer operations."""

    def __init__(self, db: Session):
        """Initialize customer repository."""
        super().__init__(Customer, db)

    def get_by_email(self, email: str) -> Optional[Customer]:
        """
        Get customer by email.

        Args:
            email: Customer email

        Returns:
            Customer or None if not found
        """
        stmt = select(Customer).where(Customer.email == email)
        return self.db.scalar(stmt)

    def get_by_phone(self, phone: str) -> Optional[Customer]:
        """
        Get customer by phone.

        Args:
            phone: Customer phone

        Returns:
            Customer or None if not found
        """
        stmt = select(Customer).where(Customer.phone == phone)
        return self.db.scalar(stmt)

    def search_by_name(self, name: str, skip: int = 0, limit: int = 100) -> List[Customer]:
        """
        Search customers by name (case-insensitive).

        Args:
            name: Name to search for
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of matching customers
        """
        stmt = (
            select(Customer)
            .where(Customer.name.ilike(f"%{name}%"))
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())
