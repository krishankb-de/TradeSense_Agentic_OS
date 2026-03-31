"""Base repository with common CRUD operations."""

from typing import Generic, List, Optional, Type, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.db.session import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Base repository with common CRUD operations."""

    def __init__(self, model: Type[ModelType], db: Session):
        """
        Initialize repository.

        Args:
            model: SQLAlchemy model class
            db: Database session
        """
        self.model = model
        self.db = db

    def get(self, id: UUID) -> Optional[ModelType]:
        """
        Get entity by ID.

        Args:
            id: Entity ID

        Returns:
            Entity or None if not found
        """
        return self.db.get(self.model, id)

    def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """
        Get all entities with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of entities
        """
        stmt = select(self.model).offset(skip).limit(limit)
        return list(self.db.scalars(stmt).all())

    def create(self, **kwargs) -> ModelType:
        """
        Create new entity.

        Args:
            **kwargs: Entity attributes

        Returns:
            Created entity

        Raises:
            SQLAlchemyError: If creation fails
        """
        try:
            entity = self.model(**kwargs)
            self.db.add(entity)
            self.db.commit()
            self.db.refresh(entity)
            return entity
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e

    def update(self, id: UUID, **kwargs) -> Optional[ModelType]:
        """
        Update entity by ID.

        Args:
            id: Entity ID
            **kwargs: Attributes to update

        Returns:
            Updated entity or None if not found

        Raises:
            SQLAlchemyError: If update fails
        """
        try:
            entity = self.get(id)
            if not entity:
                return None

            for key, value in kwargs.items():
                if hasattr(entity, key):
                    setattr(entity, key, value)

            self.db.commit()
            self.db.refresh(entity)
            return entity
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e

    def delete(self, id: UUID) -> bool:
        """
        Delete entity by ID.

        Args:
            id: Entity ID

        Returns:
            True if deleted, False if not found

        Raises:
            SQLAlchemyError: If deletion fails
        """
        try:
            entity = self.get(id)
            if not entity:
                return False

            self.db.delete(entity)
            self.db.commit()
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e

    def retry_transaction(self, func, max_retries: int = 3):
        """
        Execute function with transaction retry logic.

        Args:
            func: Function to execute
            max_retries: Maximum number of retries

        Returns:
            Function result

        Raises:
            SQLAlchemyError: If all retries fail
        """
        for attempt in range(max_retries):
            try:
                result = func()
                self.db.commit()
                return result
            except SQLAlchemyError as e:
                self.db.rollback()
                if attempt == max_retries - 1:
                    raise e
                continue
