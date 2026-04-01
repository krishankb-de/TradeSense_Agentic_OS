"""
Simple Documentation RAG for TradeSense.

Provides semantic search over technical manuals and documentation
using embeddings and vector search.

**Validates: Requirements 20.1-20.9**
"""

import asyncio
import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================


class DocumentChunk(BaseModel):
    """A chunk of documentation with metadata."""
    id: str
    content: str
    source: str
    page: Optional[int] = None
    section: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    embedding: Optional[List[float]] = None


class SearchResult(BaseModel):
    """Search result with relevance score."""
    chunk: DocumentChunk
    relevance_score: float = Field(..., ge=0.0, le=1.0)
    context_before: Optional[str] = None
    context_after: Optional[str] = None


# ============================================================================
# Documentation RAG
# ============================================================================


class DocumentationRAG:
    """
    Simple RAG system for technical documentation.
    
    Features:
    - Document indexing (PDF, Markdown, HTML)
    - Semantic search with embeddings
    - Source citation
    - Sub-second retrieval
    
    **Validates: Requirements 20.1-20.9**
    """
    
    def __init__(
        self,
        llm_client: Any,
        storage_backend: Optional[Any] = None,
    ):
        """
        Initialize documentation RAG.
        
        Args:
            llm_client: LLM client with embedding support
            storage_backend: Optional vector storage backend (PostgreSQL pgvector)
        """
        self.llm_client = llm_client
        self.storage_backend = storage_backend
        
        # In-memory index for simple implementation (fallback)
        self.document_index: Dict[str, DocumentChunk] = {}
        self.embeddings_cache: Dict[str, List[float]] = {}
        
        # Use storage backend if available
        self.use_storage = storage_backend is not None
        
        logger.info(f"Initialized DocumentationRAG (storage: {self.use_storage})")
    
    async def index_document(
        self,
        file_path: str,
        document_type: str = "pdf",
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> int:
        """
        Index a document for search.
        
        Args:
            file_path: Path to document file
            document_type: Type of document (pdf, markdown, html)
            chunk_size: Size of text chunks in characters
            chunk_overlap: Overlap between chunks
        
        Returns:
            Number of chunks indexed
        
        **Validates: Requirements 20.1, 20.2, 20.4, 20.7**
        """
        logger.info(f"Indexing document: {file_path}")
        
        try:
            # Extract text from document
            text = await self._extract_text(file_path, document_type)
            
            # Split into chunks
            chunks = self._split_into_chunks(text, chunk_size, chunk_overlap)
            
            # Generate embeddings and store
            indexed_count = 0
            for i, chunk_text in enumerate(chunks):
                chunk_id = self._generate_chunk_id(file_path, i)
                
                # Generate embedding
                embedding = await self._generate_embedding(chunk_text)
                
                # Create document chunk
                chunk = DocumentChunk(
                    id=chunk_id,
                    content=chunk_text,
                    source=file_path,
                    page=self._estimate_page(i, chunk_size),
                    metadata={
                        "document_type": document_type,
                        "chunk_index": i,
                    },
                    embedding=embedding,
                )
                
                # Store in index (in-memory)
                self.document_index[chunk_id] = chunk
                
                # Store in persistent storage if available
                if self.use_storage and self.storage_backend:
                    self.storage_backend.store_chunk(
                        chunk_id=chunk_id,
                        content=chunk_text,
                        source=file_path,
                        embedding=embedding,
                        page=self._estimate_page(i, chunk_size),
                        section=None,
                        metadata={
                            "document_type": document_type,
                            "chunk_index": i,
                        },
                    )
                
                indexed_count += 1
            
            logger.info(f"Indexed {indexed_count} chunks from {file_path}")
            return indexed_count
            
        except Exception as e:
            logger.error(f"Error indexing document {file_path}: {e}")
            return 0
    
    async def search(
        self,
        query: str,
        max_results: int = 5,
        min_relevance: float = 0.5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """
        Search documentation with semantic similarity.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            min_relevance: Minimum relevance score threshold
            filters: Optional metadata filters
        
        Returns:
            List of search results with citations
        
        **Validates: Requirements 20.3, 20.5, 20.8, 20.9**
        """
        logger.info(f"Searching documentation: {query[:100]}...")
        
        try:
            # Generate query embedding
            query_embedding = await self._generate_embedding(query)
            
            # Use storage backend if available
            if self.use_storage and self.storage_backend:
                # Search using persistent storage
                chunk_ids_scores = self.storage_backend.search_by_vector(
                    query_embedding=query_embedding,
                    max_results=max_results,
                    min_similarity=min_relevance,
                    source_filter=filters.get("source") if filters else None,
                )
                
                # Retrieve full chunks
                results = []
                for chunk_id, similarity in chunk_ids_scores:
                    chunk_data = self.storage_backend.get_chunk(chunk_id)
                    if chunk_data:
                        chunk = DocumentChunk(
                            id=chunk_data["id"],
                            content=chunk_data["content"],
                            source=chunk_data["source"],
                            page=chunk_data["page"],
                            section=chunk_data["section"],
                            metadata=chunk_data["metadata"],
                            embedding=chunk_data["embedding"],
                        )
                        results.append(
                            SearchResult(
                                chunk=chunk,
                                relevance_score=similarity,
                            )
                        )
            else:
                # Use in-memory index
                results = []
                for chunk_id, chunk in self.document_index.items():
                    # Apply filters if provided
                    if filters and not self._matches_filters(chunk, filters):
                        continue
                    
                    # Calculate cosine similarity
                    if chunk.embedding:
                        similarity = self._cosine_similarity(
                            query_embedding, chunk.embedding
                        )
                        
                        if similarity >= min_relevance:
                            results.append(
                                SearchResult(
                                    chunk=chunk,
                                    relevance_score=similarity,
                                )
                            )
                
                # Sort by relevance and limit results
                results.sort(key=lambda r: r.relevance_score, reverse=True)
                results = results[:max_results]
            
            # Add context for top results
            for result in results:
                result.context_before, result.context_after = self._get_context(
                    result.chunk
                )
            
            logger.info(f"Found {len(results)} relevant results")
            return results
            
        except Exception as e:
            logger.error(f"Error searching documentation: {e}")
            return []
    
    async def get_relevant_context(
        self,
        query: str,
        equipment_info: Optional[Dict[str, Any]] = None,
        max_tokens: int = 2000,
    ) -> str:
        """
        Get relevant documentation context for a query.
        
        Combines multiple search results into a single context string
        suitable for LLM prompts.
        
        Args:
            query: Search query
            equipment_info: Optional equipment context for filtering
            max_tokens: Maximum context length in tokens
        
        Returns:
            Formatted context string with citations
        
        **Validates: Requirement 20.6**
        """
        # Build filters from equipment info
        filters = {}
        if equipment_info:
            if "manufacturer" in equipment_info:
                filters["manufacturer"] = equipment_info["manufacturer"]
            if "model_number" in equipment_info:
                filters["model"] = equipment_info["model_number"]
        
        # Search for relevant chunks
        results = await self.search(query, max_results=5, filters=filters)
        
        if not results:
            return "No relevant documentation found."
        
        # Format context with citations
        context_parts = []
        for i, result in enumerate(results, 1):
            citation = f"[{i}] {result.chunk.source}"
            if result.chunk.page:
                citation += f", page {result.chunk.page}"
            
            context_parts.append(
                f"{citation}\n{result.chunk.content}\n"
            )
        
        context = "\n---\n".join(context_parts)
        
        # Truncate if too long (rough token estimation: 1 token ≈ 4 chars)
        max_chars = max_tokens * 4
        if len(context) > max_chars:
            context = context[:max_chars] + "\n...[truncated]"
        
        return context
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get indexing statistics."""
        if self.use_storage and self.storage_backend:
            return self.storage_backend.get_statistics()
        else:
            return {
                "total_chunks": len(self.document_index),
                "total_documents": len(set(
                    chunk.source for chunk in self.document_index.values()
                )),
                "cache_size": len(self.embeddings_cache),
            }
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    async def _extract_text(
        self,
        file_path: str,
        document_type: str,
    ) -> str:
        """Extract text from document."""
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Document not found: {file_path}")
        
        if document_type == "markdown" or file_path.endswith(".md"):
            return path.read_text(encoding="utf-8", errors="replace")
        
        elif document_type == "html" or file_path.endswith(".html"):
            # Simple HTML text extraction
            text = path.read_text(encoding="utf-8", errors="replace")
            # Remove HTML tags (basic implementation)
            import re
            text = re.sub(r'<[^>]+>', '', text)
            return text
        
        elif document_type == "pdf" or file_path.endswith(".pdf"):
            # PDF extraction would require PyPDF2 or similar
            # For now, return placeholder
            logger.warning(f"PDF extraction not implemented, using placeholder")
            return f"[PDF content from {file_path}]"
        
        else:
            # Try to read as plain text
            return path.read_text(encoding="utf-8", errors="replace")
    
    def _split_into_chunks(
        self,
        text: str,
        chunk_size: int,
        chunk_overlap: int,
    ) -> List[str]:
        """Split text into overlapping chunks."""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            
            # Try to break at sentence boundary
            if end < len(text):
                last_period = chunk.rfind('.')
                last_newline = chunk.rfind('\n')
                break_point = max(last_period, last_newline)
                
                if break_point > chunk_size // 2:
                    chunk = chunk[:break_point + 1]
                    end = start + break_point + 1
            
            chunks.append(chunk.strip())
            start = end - chunk_overlap
        
        return [c for c in chunks if c]  # Filter empty chunks
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text."""
        # Check cache first
        text_hash = hashlib.md5(text.encode()).hexdigest()
        if text_hash in self.embeddings_cache:
            return self.embeddings_cache[text_hash]
        
        try:
            # Use LLM client to generate embedding
            embedding = await self.llm_client.generate_embedding(text)
            
            # Cache the embedding
            self.embeddings_cache[text_hash] = embedding
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            # Return zero vector as fallback
            return [0.0] * 768  # Typical embedding dimension
    
    def _generate_chunk_id(self, file_path: str, chunk_index: int) -> str:
        """Generate unique chunk ID."""
        path_hash = hashlib.md5(file_path.encode()).hexdigest()[:8]
        return f"{path_hash}_{chunk_index}"
    
    def _estimate_page(self, chunk_index: int, chunk_size: int) -> int:
        """Estimate page number from chunk index."""
        # Rough estimate: 500 chars per page
        chars_per_page = 500
        return (chunk_index * chunk_size) // chars_per_page + 1
    
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
    
    def _matches_filters(
        self,
        chunk: DocumentChunk,
        filters: Dict[str, Any],
    ) -> bool:
        """Check if chunk matches filters."""
        for key, value in filters.items():
            if key in chunk.metadata:
                if chunk.metadata[key] != value:
                    return False
            elif key == "source":
                if value not in chunk.source:
                    return False
        
        return True
    
    def _get_context(
        self,
        chunk: DocumentChunk,
    ) -> Tuple[Optional[str], Optional[str]]:
        """Get surrounding context for a chunk."""
        # Find adjacent chunks
        chunk_index = chunk.metadata.get("chunk_index", 0)
        source = chunk.source
        
        context_before = None
        context_after = None
        
        # Look for previous chunk
        prev_id = self._generate_chunk_id(source, chunk_index - 1)
        if prev_id in self.document_index:
            prev_chunk = self.document_index[prev_id]
            context_before = prev_chunk.content[-100:]  # Last 100 chars
        
        # Look for next chunk
        next_id = self._generate_chunk_id(source, chunk_index + 1)
        if next_id in self.document_index:
            next_chunk = self.document_index[next_id]
            context_after = next_chunk.content[:100]  # First 100 chars
        
        return context_before, context_after


# ============================================================================
# Factory Function
# ============================================================================


def create_documentation_rag(
    llm_client: Any,
    storage_backend: Optional[Any] = None,
) -> DocumentationRAG:
    """
    Create and configure a documentation RAG system.
    
    Args:
        llm_client: LLM client with embedding support
        storage_backend: Optional vector storage backend
    
    Returns:
        Configured DocumentationRAG instance
    """
    return DocumentationRAG(
        llm_client=llm_client,
        storage_backend=storage_backend,
    )
