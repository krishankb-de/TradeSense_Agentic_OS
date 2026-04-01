"""
Unit tests for documentation management system.

Tests document indexing, semantic search, and retrieval.

**Validates: Requirements 20.1-20.9**
"""

import pytest
import asyncio
from pathlib import Path
from typing import List
import tempfile
import os

from backend.agents.documentation_rag import (
    DocumentationRAG,
    DocumentChunk,
    SearchResult,
    create_documentation_rag,
)
from backend.db.document_store import DocumentStore, create_document_store


# ============================================================================
# Mock LLM Client
# ============================================================================


class MockLLMClient:
    """Mock LLM client for testing."""
    
    def __init__(self, embedding_dim: int = 768):
        self.embedding_dim = embedding_dim
        self.call_count = 0
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate mock embedding based on text hash."""
        self.call_count += 1
        
        # Generate deterministic embedding from text
        hash_val = hash(text)
        embedding = []
        for i in range(self.embedding_dim):
            val = ((hash_val + i) % 1000) / 1000.0
            embedding.append(val)
        
        # Normalize
        magnitude = sum(v * v for v in embedding) ** 0.5
        if magnitude > 0:
            embedding = [v / magnitude for v in embedding]
        
        return embedding


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_llm_client():
    """Create mock LLM client."""
    return MockLLMClient()


@pytest.fixture
def temp_doc_dir():
    """Create temporary directory with test documents."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test markdown file
        md_file = Path(tmpdir) / "test_manual.md"
        md_file.write_text("""
# Equipment Manual

## Section 1: Installation

To install the equipment, follow these steps:
1. Connect power supply
2. Attach mounting brackets
3. Secure with provided screws

## Section 2: Operation

The equipment operates at 120V AC. Press the power button to start.
Normal operation temperature is 20-25°C.

## Section 3: Troubleshooting

If the equipment fails to start:
- Check power connection
- Verify voltage is correct
- Inspect fuse
""")
        
        # Create test HTML file
        html_file = Path(tmpdir) / "test_guide.html"
        html_file.write_text("""
<html>
<head><title>Repair Guide</title></head>
<body>
<h1>Repair Procedures</h1>
<p>This guide covers common repair procedures.</p>
<h2>Replacing Components</h2>
<p>Always disconnect power before replacing components.</p>
<p>Use proper ESD protection when handling electronic parts.</p>
</body>
</html>
""")
        
        yield tmpdir


@pytest.fixture
def doc_rag(mock_llm_client):
    """Create DocumentationRAG instance."""
    return create_documentation_rag(llm_client=mock_llm_client)


@pytest.fixture
def doc_store():
    """Create in-memory document store for testing."""
    # Use SQLite in-memory database
    store = create_document_store("sqlite:///:memory:")
    return store


@pytest.fixture
def doc_rag_with_storage(mock_llm_client, doc_store):
    """Create DocumentationRAG with persistent storage."""
    return create_documentation_rag(
        llm_client=mock_llm_client,
        storage_backend=doc_store,
    )


# ============================================================================
# Test 20.1: Document Indexing
# **Validates: Requirements 20.1, 20.2, 20.4, 20.7**
# ============================================================================


class TestDocumentIndexing:
    """Test document indexing pipeline."""
    
    @pytest.mark.asyncio
    async def test_index_markdown_document(self, doc_rag, temp_doc_dir):
        """Test indexing a markdown document."""
        md_file = Path(temp_doc_dir) / "test_manual.md"
        
        count = await doc_rag.index_document(
            file_path=str(md_file),
            document_type="markdown",
            chunk_size=200,
            chunk_overlap=20,
        )
        
        assert count > 0, "Should index at least one chunk"
        
        stats = doc_rag.get_statistics()
        assert stats["total_chunks"] == count
        assert stats["total_documents"] == 1
    
    @pytest.mark.asyncio
    async def test_index_html_document(self, doc_rag, temp_doc_dir):
        """Test indexing an HTML document."""
        html_file = Path(temp_doc_dir) / "test_guide.html"
        
        count = await doc_rag.index_document(
            file_path=str(html_file),
            document_type="html",
            chunk_size=150,
        )
        
        assert count > 0, "Should index at least one chunk"
    
    @pytest.mark.asyncio
    async def test_index_multiple_documents(self, doc_rag, temp_doc_dir):
        """Test indexing multiple documents."""
        md_file = Path(temp_doc_dir) / "test_manual.md"
        html_file = Path(temp_doc_dir) / "test_guide.html"
        
        count1 = await doc_rag.index_document(str(md_file), "markdown")
        count2 = await doc_rag.index_document(str(html_file), "html")
        
        stats = doc_rag.get_statistics()
        assert stats["total_chunks"] == count1 + count2
        assert stats["total_documents"] == 2
    
    @pytest.mark.asyncio
    async def test_index_with_storage_backend(
        self, doc_rag_with_storage, temp_doc_dir
    ):
        """Test indexing with persistent storage."""
        md_file = Path(temp_doc_dir) / "test_manual.md"
        
        count = await doc_rag_with_storage.index_document(
            file_path=str(md_file),
            document_type="markdown",
        )
        
        assert count > 0
        
        # Verify storage
        stats = doc_rag_with_storage.get_statistics()
        assert stats["total_chunks"] == count
    
    @pytest.mark.asyncio
    async def test_chunk_size_and_overlap(self, doc_rag, temp_doc_dir):
        """Test chunk size and overlap parameters."""
        md_file = Path(temp_doc_dir) / "test_manual.md"
        
        # Small chunks
        count_small = await doc_rag.index_document(
            str(md_file), "markdown", chunk_size=100, chunk_overlap=10
        )
        
        # Reset
        doc_rag.document_index.clear()
        
        # Large chunks
        count_large = await doc_rag.index_document(
            str(md_file), "markdown", chunk_size=500, chunk_overlap=50
        )
        
        # Smaller chunks should produce more chunks
        assert count_small > count_large
    
    @pytest.mark.asyncio
    async def test_index_nonexistent_file(self, doc_rag):
        """Test indexing nonexistent file."""
        count = await doc_rag.index_document(
            file_path="/nonexistent/file.md",
            document_type="markdown",
        )
        
        assert count == 0, "Should return 0 for nonexistent file"


# ============================================================================
# Test 20.2: Semantic Search
# **Validates: Requirements 20.3, 20.5, 20.8, 20.9**
# ============================================================================


class TestSemanticSearch:
    """Test semantic search functionality."""
    
    @pytest.mark.asyncio
    async def test_basic_search(self, doc_rag, temp_doc_dir):
        """Test basic semantic search."""
        md_file = Path(temp_doc_dir) / "test_manual.md"
        await doc_rag.index_document(str(md_file), "markdown")
        
        results = await doc_rag.search(
            query="How to install equipment?",
            max_results=3,
        )
        
        assert len(results) > 0, "Should find relevant results"
        assert all(isinstance(r, SearchResult) for r in results)
        assert all(0 <= r.relevance_score <= 1 for r in results)
    
    @pytest.mark.asyncio
    async def test_search_relevance_threshold(self, doc_rag, temp_doc_dir):
        """Test minimum relevance threshold."""
        md_file = Path(temp_doc_dir) / "test_manual.md"
        await doc_rag.index_document(str(md_file), "markdown")
        
        # High threshold
        results_high = await doc_rag.search(
            query="installation steps",
            min_relevance=0.8,
        )
        
        # Low threshold
        results_low = await doc_rag.search(
            query="installation steps",
            min_relevance=0.3,
        )
        
        # Lower threshold should return more results
        assert len(results_low) >= len(results_high)
    
    @pytest.mark.asyncio
    async def test_search_max_results(self, doc_rag, temp_doc_dir):
        """Test max results limit."""
        md_file = Path(temp_doc_dir) / "test_manual.md"
        await doc_rag.index_document(str(md_file), "markdown", chunk_size=100)
        
        results = await doc_rag.search(
            query="equipment",
            max_results=2,
            min_relevance=0.0,
        )
        
        assert len(results) <= 2, "Should respect max_results limit"
    
    @pytest.mark.asyncio
    async def test_search_with_filters(self, doc_rag, temp_doc_dir):
        """Test search with metadata filters."""
        md_file = Path(temp_doc_dir) / "test_manual.md"
        html_file = Path(temp_doc_dir) / "test_guide.html"
        
        await doc_rag.index_document(str(md_file), "markdown")
        await doc_rag.index_document(str(html_file), "html")
        
        # Search with source filter
        results = await doc_rag.search(
            query="repair",
            filters={"source": "test_guide.html"},
        )
        
        # All results should be from filtered source
        for result in results:
            assert "test_guide.html" in result.chunk.source
    
    @pytest.mark.asyncio
    async def test_search_with_storage_backend(
        self, doc_rag_with_storage, temp_doc_dir
    ):
        """Test search using persistent storage."""
        md_file = Path(temp_doc_dir) / "test_manual.md"
        await doc_rag_with_storage.index_document(str(md_file), "markdown")
        
        results = await doc_rag_with_storage.search(
            query="troubleshooting",
            max_results=3,
        )
        
        assert len(results) > 0
    
    @pytest.mark.asyncio
    async def test_search_returns_sorted_results(self, doc_rag, temp_doc_dir):
        """Test that results are sorted by relevance."""
        md_file = Path(temp_doc_dir) / "test_manual.md"
        await doc_rag.index_document(str(md_file), "markdown")
        
        results = await doc_rag.search(
            query="power supply connection",
            max_results=5,
            min_relevance=0.0,
        )
        
        # Check that results are sorted in descending order
        for i in range(len(results) - 1):
            assert results[i].relevance_score >= results[i + 1].relevance_score


# ============================================================================
# Test 20.3: Source Citation and Context
# **Validates: Requirement 20.6**
# ============================================================================


class TestSourceCitation:
    """Test source citation and context extraction."""
    
    @pytest.mark.asyncio
    async def test_search_results_include_source(self, doc_rag, temp_doc_dir):
        """Test that search results include source information."""
        md_file = Path(temp_doc_dir) / "test_manual.md"
        await doc_rag.index_document(str(md_file), "markdown")
        
        results = await doc_rag.search(query="installation")
        
        for result in results:
            assert result.chunk.source is not None
            assert len(result.chunk.source) > 0
    
    @pytest.mark.asyncio
    async def test_get_relevant_context(self, doc_rag, temp_doc_dir):
        """Test getting relevant context with citations."""
        md_file = Path(temp_doc_dir) / "test_manual.md"
        await doc_rag.index_document(str(md_file), "markdown")
        
        context = await doc_rag.get_relevant_context(
            query="How to troubleshoot equipment?",
            max_tokens=1000,
        )
        
        assert len(context) > 0
        assert "[1]" in context, "Should include citation markers"
        assert "test_manual.md" in context, "Should include source file"
    
    @pytest.mark.asyncio
    async def test_context_includes_page_numbers(self, doc_rag, temp_doc_dir):
        """Test that context includes page numbers when available."""
        md_file = Path(temp_doc_dir) / "test_manual.md"
        await doc_rag.index_document(str(md_file), "markdown")
        
        context = await doc_rag.get_relevant_context(query="operation")
        
        # Should include page information
        assert "page" in context.lower() or "[" in context
    
    @pytest.mark.asyncio
    async def test_context_with_equipment_filter(self, doc_rag, temp_doc_dir):
        """Test context retrieval with equipment filtering."""
        md_file = Path(temp_doc_dir) / "test_manual.md"
        await doc_rag.index_document(str(md_file), "markdown")
        
        context = await doc_rag.get_relevant_context(
            query="installation",
            equipment_info={"manufacturer": "TestCorp", "model_number": "X100"},
        )
        
        assert len(context) > 0
    
    @pytest.mark.asyncio
    async def test_context_truncation(self, doc_rag, temp_doc_dir):
        """Test that context is truncated to max_tokens."""
        md_file = Path(temp_doc_dir) / "test_manual.md"
        await doc_rag.index_document(str(md_file), "markdown", chunk_size=100)
        
        context = await doc_rag.get_relevant_context(
            query="equipment",
            max_tokens=50,  # Very small limit
        )
        
        # Should be truncated (rough estimate: 1 token ≈ 4 chars)
        assert len(context) <= 50 * 4 + 100  # Allow some margin


# ============================================================================
# Test 20.4: Document Store
# **Validates: Requirements 20.1, 20.2, 20.7**
# ============================================================================


class TestDocumentStore:
    """Test PostgreSQL document store."""
    
    def test_store_and_retrieve_chunk(self, doc_store):
        """Test storing and retrieving a chunk."""
        chunk_id = "test_chunk_1"
        content = "This is test content for the chunk."
        source = "/path/to/test.md"
        embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        
        # Store chunk
        success = doc_store.store_chunk(
            chunk_id=chunk_id,
            content=content,
            source=source,
            embedding=embedding,
            page=1,
            section="Introduction",
            metadata={"test": "value"},
        )
        
        assert success, "Should store chunk successfully"
        
        # Retrieve chunk
        retrieved = doc_store.get_chunk(chunk_id)
        
        assert retrieved is not None
        assert retrieved["id"] == chunk_id
        assert retrieved["content"] == content
        assert retrieved["source"] == source
        assert retrieved["page"] == 1
        assert retrieved["section"] == "Introduction"
        assert retrieved["metadata"]["test"] == "value"
    
    def test_update_existing_chunk(self, doc_store):
        """Test updating an existing chunk."""
        chunk_id = "test_chunk_2"
        
        # Store initial chunk
        doc_store.store_chunk(
            chunk_id=chunk_id,
            content="Original content",
            source="/test.md",
            embedding=[0.1, 0.2],
        )
        
        # Update chunk
        doc_store.store_chunk(
            chunk_id=chunk_id,
            content="Updated content",
            source="/test.md",
            embedding=[0.3, 0.4],
        )
        
        # Retrieve and verify
        retrieved = doc_store.get_chunk(chunk_id)
        assert retrieved["content"] == "Updated content"
    
    def test_vector_search(self, doc_store):
        """Test vector similarity search."""
        # Store multiple chunks with different embeddings
        doc_store.store_chunk(
            "chunk1", "Content about installation",
            "/manual.md", [1.0, 0.0, 0.0]
        )
        doc_store.store_chunk(
            "chunk2", "Content about operation",
            "/manual.md", [0.0, 1.0, 0.0]
        )
        doc_store.store_chunk(
            "chunk3", "Content about troubleshooting",
            "/manual.md", [0.0, 0.0, 1.0]
        )
        
        # Search with query similar to chunk1
        results = doc_store.search_by_vector(
            query_embedding=[0.9, 0.1, 0.0],
            max_results=2,
            min_similarity=0.5,
        )
        
        assert len(results) > 0
        assert results[0][0] == "chunk1", "Should find most similar chunk"
    
    def test_text_search_fallback(self, doc_store):
        """Test full-text search fallback."""
        doc_store.store_chunk(
            "chunk1", "Installation instructions for equipment",
            "/manual.md", [0.1, 0.2]
        )
        doc_store.store_chunk(
            "chunk2", "Operation procedures",
            "/manual.md", [0.3, 0.4]
        )
        
        results = doc_store.search_by_text(
            query="installation",
            max_results=5,
        )
        
        assert len(results) > 0
        assert "chunk1" in results
    
    def test_delete_by_source(self, doc_store):
        """Test deleting chunks by source."""
        source = "/test_manual.md"
        
        # Store multiple chunks
        doc_store.store_chunk("c1", "Content 1", source, [0.1])
        doc_store.store_chunk("c2", "Content 2", source, [0.2])
        doc_store.store_chunk("c3", "Content 3", "/other.md", [0.3])
        
        # Delete by source
        count = doc_store.delete_by_source(source)
        
        assert count == 2, "Should delete 2 chunks"
        
        # Verify deletion
        assert doc_store.get_chunk("c1") is None
        assert doc_store.get_chunk("c2") is None
        assert doc_store.get_chunk("c3") is not None
    
    def test_get_statistics(self, doc_store):
        """Test getting storage statistics."""
        # Store chunks from different sources
        doc_store.store_chunk("c1", "Content", "/doc1.md", [0.1])
        doc_store.store_chunk("c2", "Content", "/doc1.md", [0.2])
        doc_store.store_chunk("c3", "Content", "/doc2.md", [0.3])
        
        stats = doc_store.get_statistics()
        
        assert stats["total_chunks"] == 3
        assert stats["total_sources"] == 2


# ============================================================================
# Test 20.5: Performance Requirements
# **Validates: Requirement 20.5**
# ============================================================================


class TestPerformance:
    """Test performance requirements."""
    
    @pytest.mark.asyncio
    async def test_search_latency(self, doc_rag, temp_doc_dir):
        """Test that search completes in sub-second time."""
        import time
        
        md_file = Path(temp_doc_dir) / "test_manual.md"
        await doc_rag.index_document(str(md_file), "markdown")
        
        start = time.time()
        results = await doc_rag.search(query="installation")
        elapsed = time.time() - start
        
        assert elapsed < 1.0, f"Search took {elapsed:.3f}s, should be <1s"
    
    @pytest.mark.asyncio
    async def test_indexing_performance(self, doc_rag, temp_doc_dir):
        """Test indexing performance."""
        import time
        
        md_file = Path(temp_doc_dir) / "test_manual.md"
        
        start = time.time()
        count = await doc_rag.index_document(str(md_file), "markdown")
        elapsed = time.time() - start
        
        # Should index reasonably fast
        assert elapsed < 5.0, f"Indexing took {elapsed:.3f}s"
        assert count > 0


# ============================================================================
# Test 20.6: Integration Tests
# **Validates: Requirements 20.1-20.9**
# ============================================================================


class TestIntegration:
    """Integration tests for complete workflows."""
    
    @pytest.mark.asyncio
    async def test_complete_indexing_and_search_workflow(
        self, doc_rag, temp_doc_dir
    ):
        """Test complete workflow: index → search → retrieve context."""
        # Index documents
        md_file = Path(temp_doc_dir) / "test_manual.md"
        html_file = Path(temp_doc_dir) / "test_guide.html"
        
        count1 = await doc_rag.index_document(str(md_file), "markdown")
        count2 = await doc_rag.index_document(str(html_file), "html")
        
        assert count1 > 0 and count2 > 0
        
        # Search
        results = await doc_rag.search(query="repair procedures")
        assert len(results) > 0
        
        # Get context
        context = await doc_rag.get_relevant_context(query="repair procedures")
        assert len(context) > 0
        assert "repair" in context.lower() or "Repair" in context
    
    @pytest.mark.asyncio
    async def test_workflow_with_persistent_storage(
        self, doc_rag_with_storage, temp_doc_dir
    ):
        """Test workflow with persistent storage backend."""
        md_file = Path(temp_doc_dir) / "test_manual.md"
        
        # Index
        count = await doc_rag_with_storage.index_document(str(md_file), "markdown")
        assert count > 0
        
        # Search
        results = await doc_rag_with_storage.search(query="troubleshooting")
        assert len(results) > 0
        
        # Verify persistence
        stats = doc_rag_with_storage.get_statistics()
        assert stats["total_chunks"] == count
    
    @pytest.mark.asyncio
    async def test_multiple_searches_use_cache(self, doc_rag, temp_doc_dir):
        """Test that embeddings are cached for repeated queries."""
        md_file = Path(temp_doc_dir) / "test_manual.md"
        await doc_rag.index_document(str(md_file), "markdown")
        
        # First search
        await doc_rag.search(query="installation")
        initial_cache_size = len(doc_rag.embeddings_cache)
        
        # Second search with same query
        await doc_rag.search(query="installation")
        final_cache_size = len(doc_rag.embeddings_cache)
        
        # Cache size should not increase (query embedding reused)
        assert final_cache_size == initial_cache_size


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
