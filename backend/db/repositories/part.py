"""Part repository."""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.models import Part
from backend.db.repositories.base import BaseRepository


class PartRepository(BaseRepository[Part]):
    """Repository for part operations."""

    def __init__(self, db: Session):
        """Initialize part repository."""
        super().__init__(Part, db)

    def get_by_part_number(self, part_number: str) -> Optional[Part]:
        """
        Get part by part number.

        Args:
            part_number: Part number

        Returns:
            Part or None if not found
        """
        stmt = select(Part).where(Part.part_number == part_number)
        return self.db.scalar(stmt)

    def get_by_category(self, category: str, skip: int = 0, limit: int = 100) -> List[Part]:
        """
        Get parts by category.

        Args:
            category: Part category
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of parts in the category
        """
        stmt = (
            select(Part)
            .where(Part.category == category)
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def get_low_stock(self, skip: int = 0, limit: int = 100) -> List[Part]:
        """
        Get parts with low stock (quantity <= reorder level).

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of parts with low stock
        """
        stmt = (
            select(Part)
            .where(Part.quantity_available <= Part.reorder_level)
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def search_by_name(self, name: str, skip: int = 0, limit: int = 100) -> List[Part]:
        """
        Search parts by name (case-insensitive).

        Args:
            name: Name to search for
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of matching parts
        """
        stmt = (
            select(Part)
            .where(Part.name.ilike(f"%{name}%"))
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def update_quantity(self, part_id: UUID, quantity_change: int) -> Optional[Part]:
        """
        Update part quantity (add or subtract).

        Args:
            part_id: Part ID
            quantity_change: Quantity to add (positive) or subtract (negative)

        Returns:
            Updated part or None if not found
        """
        part = self.get(part_id)
        if not part:
            return None

        part.quantity_available += quantity_change
        self.db.commit()
        self.db.refresh(part)
        return part
