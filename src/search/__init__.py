"""
Reusable semantic search module with ChromaDB and sentence transformers.

This module provides a clean interface for semantic search operations including:
- Document storage with embeddings
- Semantic search/retrieval
- Metadata management
- Vector database operations

Example Usage:
    from search import SemanticSearch
    
    # Initialize search
    search = SemanticSearch(db_path="./my_db", collection_name="documents")
    
    # Store documents
    search.store(
        doc_id="doc1",
        text="Machine learning is a subset of artificial intelligence",
        metadata={"category": "AI", "source": "wiki"}
    )
    
    # Search
    results = search.search("what is AI?", limit=5)
    for result in results:
        print(result["text"], result["distance"])
"""

from .semantic_search import SemanticSearch
from .vector_store import VectorStore
from .embeddings import EmbeddingGenerator
from .config import SearchConfig

__all__ = [
    "SemanticSearch",
    "VectorStore",
    "EmbeddingGenerator",
    "SearchConfig",
]

__version__ = "1.0.0"
