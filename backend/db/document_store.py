"""
Document storage with PostgreSQL pgvector for TradeSense.

Provides vector storage for document embeddings with semantic search.

**Validates: Requirements 20.1, 20.2, 20.7**
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

Base = declarative_base()


# ============================================================================
# Database Models
# ============================================================================


class DocumentChunkModel(Base):
    """Database model for document chunks with embeddings."""
    
    __tablename__ = "document_chunks"
    
    id = Column(String, primary_key=True)
    content = Column(Text, nullable=False)
    source = Column(String, nullable=False, index=True)
    page = Column(Integer, nullable=True)
    section = Column(String, nullable=True)
    chunk_metadata = Column(JSON, default={})  # Renamed from 'metadata' to avoid SQLAlchemy conflict
    embedding_vector = Column(JSON, nullable=True)  # Store as JSON array for simplicity
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Create index on source for faster queries
    __table_args__ = (
        Index('idx_document_source', 'source'),
    )


# ============================================================================
# Document Store
# ============================================================================


class DocumentStore:
    """
    PostgreSQL-based document storage with vector search.
    
    Features:
    - Store document chunks with embeddings
    - Vector similarity search
    - Full-text search fallback
    - Source filtering
    
    **Validates: Requirements 20.1, 20.2, 20.7**
    """
    
    def __init__(self, database_url: str):
        """
        Initialize document store.
        
        Args:
            database_url: PostgreSQL connection URL
        """
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Create tables if they don't exist
        Base.metadata.create_all(self.engine)
        
        logger.info("Initialized DocumentStore with PostgreSQL")
    
    def store_chunk(
        self,
        chunk_id: str,
        content: str,
        source: str,
        embedding: List[float],
        page: Optional[int] = None,
        section: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Store a document chunk with its embedding.
        
        Args:
            chunk_id: Unique chunk identifier
            content: Text content
            source: Source document path
            embedding: Embedding vector
            page: Optional page number
            section: Optional section name
            metadata: Optional metadata dict
        
        Returns:
            True if stored successfully
        
        **Validates: Requirement 20.7**
        """
        try:
            session = self.SessionLocal()
            
            # Check if chunk already exists
            existing = session.query(DocumentChunkModel).filter_by(id=chunk_id).first()
            
            if existing:
                # Update existing chunk
                existing.content = content
                existing.source = source
                existing.embedding_vector = embedding
                existing.page = page
                existing.section = section
                existing.chunk_metadata = metadata or {}
                existing.updated_at = datetime.utcnow()
            else:
                # Create new chunk
                chunk = DocumentChunkModel(
                    id=chunk_id,
                    content=content,
                    source=source,
                    embedding_vector=embedding,
                    page=page,
                    section=section,
                    chunk_metadata=metadata or {},
                )
                session.add(chunk)
            
            session.commit()
            session.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Error storing chunk {chunk_id}: {e}")
            if session:
                session.rollback()
                session.close()
            return False
    
    def search_by_vector(
        self,
        query_embedding: List[float],
        max_results: int = 5,
        min_similarity: float = 0.5,
        source_filter: Optional[str] = None,
    ) -> List[Tuple[str, float]]:
        """
        Search for similar chunks using vector similarity.
        
        Args:
            query_embedding: Query embedding vector
            max_results: Maximum number of results
            min_similarity: Minimum similarity threshold
            source_filter: Optional source path filter
        
        Returns:
            List of (chunk_id, similarity_score) tuples
        
        **Validates: Requirements 20.2, 20.5**
        """
        try:
            session = self.SessionLocal()
            
            # Build query
            query = session.query(DocumentChunkModel)
            
            if source_filter:
                query = query.filter(DocumentChunkModel.source.contains(source_filter))
            
            # Get all chunks (we'll calculate similarity in Python)
            chunks = query.all()
            
            # Calculate cosine similarity for each chunk
            results = []
            for chunk in chunks:
                if chunk.embedding_vector:
                    similarity = self._cosine_similarity(
                        query_embedding,
                        chunk.embedding_vector
                    )
                    
                    if similarity >= min_similarity:
                        results.append((chunk.id, similarity))
            
            # Sort by similarity and limit
            results.sort(key=lambda x: x[1], reverse=True)
            results = results[:max_results]
            
            session.close()
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching by vector: {e}")
            if session:
                session.close()
            return []
    
    def get_chunk(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a chunk by ID.
        
        Args:
            chunk_id: Chunk identifier
        
        Returns:
            Chunk data dict or None
        """
        try:
            session = self.SessionLocal()
            
            chunk = session.query(DocumentChunkModel).filter_by(id=chunk_id).first()
            
            if not chunk:
                session.close()
                return None
            
            result = {
                "id": chunk.id,
                "content": chunk.content,
                "source": chunk.source,
                "page": chunk.page,
                "section": chunk.section,
                "metadata": chunk.chunk_metadata,
                "embedding": chunk.embedding_vector,
                "created_at": chunk.created_at.isoformat() if chunk.created_at else None,
                "updated_at": chunk.updated_at.isoformat() if chunk.updated_at else None,
            }
            
            session.close()
            
            return result
            
        except Exception as e:
            logger.error(f"Error retrieving chunk {chunk_id}: {e}")
            if session:
                session.close()
            return None
    
    def search_by_text(
        self,
        query: str,
        max_results: int = 5,
        source_filter: Optional[str] = None,
    ) -> List[str]:
        """
        Full-text search fallback.
        
        Args:
            query: Search query text
            max_results: Maximum number of results
            source_filter: Optional source path filter
        
        Returns:
            List of chunk IDs
        
        **Validates: Requirement 20.8**
        """
        try:
            session = self.SessionLocal()
            
            # Build query with text search
            query_obj = session.query(DocumentChunkModel).filter(
                DocumentChunkModel.content.contains(query)
            )
            
            if source_filter:
                query_obj = query_obj.filter(
                    DocumentChunkModel.source.contains(source_filter)
                )
            
            chunks = query_obj.limit(max_results).all()
            
            result = [chunk.id for chunk in chunks]
            
            session.close()
            
            return result
            
        except Exception as e:
            logger.error(f"Error in text search: {e}")
            if session:
                session.close()
            return []
    
    def delete_by_source(self, source: str) -> int:
        """
        Delete all chunks from a source document.
        
        Args:
            source: Source document path
        
        Returns:
            Number of chunks deleted
        """
        try:
            session = self.SessionLocal()
            
            count = session.query(DocumentChunkModel).filter_by(source=source).delete()
            
            session.commit()
            session.close()
            
            logger.info(f"Deleted {count} chunks from {source}")
            return count
            
        except Exception as e:
            logger.error(f"Error deleting chunks from {source}: {e}")
            if session:
                session.rollback()
                session.close()
            return 0
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get storage statistics."""
        try:
            session = self.SessionLocal()
            
            total_chunks = session.query(func.count(DocumentChunkModel.id)).scalar()
            total_sources = session.query(
                func.count(func.distinct(DocumentChunkModel.source))
            ).scalar()
            
            session.close()
            
            return {
                "total_chunks": total_chunks,
                "total_sources": total_sources,
            }
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            if session:
                session.close()
            return {"total_chunks": 0, "total_sources": 0}
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def _cosine_similarity(
        self,
        vec1: List[float],
        vec2: List[float],
    ) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)


# ============================================================================
# Factory Function
# ============================================================================


def create_document_store(database_url: str) -> DocumentStore:
    """
    Create and configure a document store.
    
    Args:
        database_url: PostgreSQL connection URL
    
    Returns:
        Configured DocumentStore instance
    """
    return DocumentStore(database_url)
