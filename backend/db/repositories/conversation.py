"""Conversation repository."""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.models import Conversation, ConversationTurn
from backend.db.repositories.base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    """Repository for conversation operations."""

    def __init__(self, db: Session):
        """Initialize conversation repository."""
        super().__init__(Conversation, db)

    def get_by_session_id(self, session_id: str) -> Optional[Conversation]:
        """
        Get conversation by session ID.

        Args:
            session_id: Session ID

        Returns:
            Conversation or None if not found
        """
        stmt = select(Conversation).where(Conversation.session_id == session_id)
        return self.db.scalar(stmt)

    def get_by_customer(self, customer_id: UUID, skip: int = 0, limit: int = 100) -> List[Conversation]:
        """
        Get conversations by customer ID.

        Args:
            customer_id: Customer ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of conversations for the customer
        """
        stmt = (
            select(Conversation)
            .where(Conversation.customer_id == customer_id)
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def get_by_job(self, job_id: UUID, skip: int = 0, limit: int = 100) -> List[Conversation]:
        """
        Get conversations by job ID.

        Args:
            job_id: Job ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of conversations for the job
        """
        stmt = (
            select(Conversation)
            .where(Conversation.job_id == job_id)
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def get_by_status(self, status: str, skip: int = 0, limit: int = 100) -> List[Conversation]:
        """
        Get conversations by status.

        Args:
            status: Conversation status (active, completed, abandoned)
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of conversations with the specified status
        """
        stmt = (
            select(Conversation)
            .where(Conversation.status == status)
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def add_turn(
        self,
        conversation_id: UUID,
        turn_number: int,
        speaker: str,
        message: str,
        intent: Optional[str] = None,
        confidence_score: Optional[float] = None,
    ) -> ConversationTurn:
        """
        Add a turn to a conversation.

        Args:
            conversation_id: Conversation ID
            turn_number: Turn number
            speaker: Speaker (user, agent)
            message: Message text
            intent: Intent classification
            confidence_score: Confidence score

        Returns:
            Created conversation turn
        """
        turn = ConversationTurn(
            conversation_id=conversation_id,
            turn_number=turn_number,
            speaker=speaker,
            message=message,
            intent=intent,
            confidence_score=confidence_score,
        )
        self.db.add(turn)
        self.db.commit()
        self.db.refresh(turn)
        return turn

    def get_turns(self, conversation_id: UUID) -> List[ConversationTurn]:
        """
        Get all turns for a conversation.

        Args:
            conversation_id: Conversation ID

        Returns:
            List of conversation turns ordered by turn number
        """
        stmt = (
            select(ConversationTurn)
            .where(ConversationTurn.conversation_id == conversation_id)
            .order_by(ConversationTurn.turn_number)
        )
        return list(self.db.scalars(stmt).all())
