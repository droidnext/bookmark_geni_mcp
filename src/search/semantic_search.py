"""
High-level semantic search interface combining embeddings and vector storage.
"""
import logging
import hashlib
from typing import List, Dict, Any, Optional, Callable

from .vector_store import VectorStore
from .embeddings import EmbeddingGenerator
from .config import SearchConfig

logger = logging.getLogger(__name__)


class SemanticSearch:
    """
    High-level interface for semantic search operations.
    
    This class combines embedding generation and vector storage to provide
    a simple API for storing and searching documents.
    """
    
    def __init__(
        self,
        db_path: Optional[str] = None,
        collection_name: Optional[str] = None,
        config: Optional[SearchConfig] = None,
        id_generator: Optional[Callable[[str], str]] = None
    ):
        """
        Initialize semantic search.
        
        Args:
            db_path: Path to database (overrides config if provided)
            collection_name: Name of collection (overrides config if provided)
            config: SearchConfig object (uses defaults if not provided)
            id_generator: Custom function to generate IDs from text (optional)
        """
        # Use config or defaults
        if config is None:
            config = SearchConfig()
        
        # Override config with explicit parameters
        if db_path is not None:
            config.db_path = db_path
        if collection_name is not None:
            config.collection_name = collection_name
        
        self.config = config
        self.id_generator = id_generator or self._default_id_generator
        
        # Initialize embedding generator
        self.embedding_generator = EmbeddingGenerator(
            model_name=config.embedding_model
        )
        
        # Initialize vector store with embedding function
        self.vector_store = VectorStore(
            db_path=config.db_path,
            collection_name=config.collection_name,
            embedding_function=self.embedding_generator.embedding_function,
            distance_metric=config.distance_metric
        )
        
        logger.info(f"Initialized SemanticSearch with model: {config.embedding_model}")
    
    def _default_id_generator(self, text: str) -> str:
        """Generate a unique ID from text using MD5 hash."""
        return hashlib.md5(text.encode()).hexdigest()
    
    def store(
        self,
        doc_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Store a single document with automatic embedding generation.
        
        Args:
            doc_id: Unique document identifier
            text: Document text to embed and store
            metadata: Optional metadata dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            return self.vector_store.upsert(
                ids=[doc_id],
                documents=[text],
                metadatas=[metadata] if metadata else None
            )
        except Exception as e:
            logger.error(f"Error storing document {doc_id}: {e}")
            return False
    
    def store_batch(
        self,
        documents: List[Dict[str, Any]],
        id_field: str = "id",
        text_field: str = "text",
        metadata_fields: Optional[List[str]] = None
    ) -> int:
        """
        Store multiple documents in batch.
        
        Args:
            documents: List of document dictionaries
            id_field: Name of the ID field in document dicts
            text_field: Name of the text field in document dicts
            metadata_fields: Optional list of fields to include in metadata
                           (if None, all fields except id and text are included)
            
        Returns:
            Number of successfully stored documents
        """
        if not documents:
            return 0
        
        try:
            ids = []
            texts = []
            metadatas = []
            
            for doc in documents:
                if id_field not in doc or text_field not in doc:
                    logger.warning(f"Document missing required fields: {doc}")
                    continue
                
                doc_id = str(doc[id_field])
                text = str(doc[text_field])
                
                # Extract metadata
                if metadata_fields is None:
                    # Include all fields except id and text
                    metadata = {
                        k: v for k, v in doc.items()
                        if k not in [id_field, text_field]
                    }
                else:
                    # Include only specified fields
                    metadata = {
                        k: doc.get(k) for k in metadata_fields
                        if k in doc
                    }
                
                ids.append(doc_id)
                texts.append(text)
                metadatas.append(metadata)
            
            if not ids:
                return 0
            
            # Store in batches
            batch_size = self.config.batch_size
            success_count = 0
            
            for i in range(0, len(ids), batch_size):
                batch_ids = ids[i:i + batch_size]
                batch_texts = texts[i:i + batch_size]
                batch_metadatas = metadatas[i:i + batch_size]
                
                if self.vector_store.upsert(
                    ids=batch_ids,
                    documents=batch_texts,
                    metadatas=batch_metadatas
                ):
                    success_count += len(batch_ids)
            
            return success_count
            
        except Exception as e:
            logger.error(f"Error storing batch: {e}")
            return 0
    
    def search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        include_distances: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents using semantic search.
        
        Args:
            query: Search query text
            limit: Maximum number of results to return
            filters: Optional metadata filters (e.g., {"category": "science"})
            include_distances: Whether to include similarity distances in results
            
        Returns:
            List of matching documents with metadata and optional distances
        """
        try:
            # Query the vector store
            results = self.vector_store.query(
                query_texts=[query],
                n_results=limit,
                where=filters,
                include=["metadatas", "documents", "distances"]
            )
            
            # Format results
            documents = []
            if results["ids"] and len(results["ids"]) > 0:
                ids = results["ids"][0]
                metadatas = results["metadatas"][0] if results.get("metadatas") else []
                doc_texts = results["documents"][0] if results.get("documents") else []
                distances = results["distances"][0] if results.get("distances") else []
                
                for i, doc_id in enumerate(ids):
                    doc = {"id": doc_id}
                    
                    if i < len(doc_texts):
                        doc["text"] = doc_texts[i]
                    
                    if i < len(metadatas) and metadatas[i]:
                        doc["metadata"] = metadatas[i]
                    
                    if include_distances and i < len(distances):
                        doc["distance"] = distances[i]
                    
                    documents.append(doc)
            
            return documents
            
        except Exception as e:
            logger.error(f"Error searching: {e}")
            return []
    
    def get(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a document by ID.
        
        Args:
            doc_id: Document identifier
            
        Returns:
            Document dictionary or None if not found
        """
        try:
            results = self.vector_store.get(
                ids=[doc_id],
                include=["metadatas", "documents"]
            )
            
            if results["ids"] and len(results["ids"]) > 0:
                doc = {"id": results["ids"][0]}
                
                if results.get("documents") and len(results["documents"]) > 0:
                    doc["text"] = results["documents"][0]
                
                if results.get("metadatas") and len(results["metadatas"]) > 0:
                    doc["metadata"] = results["metadatas"][0]
                
                return doc
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting document {doc_id}: {e}")
            return None
    
    def delete(self, doc_id: str) -> bool:
        """
        Delete a document by ID.
        
        Args:
            doc_id: Document identifier
            
        Returns:
            True if successful, False otherwise
        """
        return self.vector_store.delete(ids=[doc_id])
    
    def delete_batch(self, doc_ids: List[str]) -> bool:
        """
        Delete multiple documents by ID.
        
        Args:
            doc_ids: List of document identifiers
            
        Returns:
            True if successful, False otherwise
        """
        return self.vector_store.delete(ids=doc_ids)
    
    def stats(self) -> Dict[str, Any]:
        """
        Get collection statistics.
        
        Returns:
            Dictionary with collection statistics
        """
        return {
            "total_documents": self.vector_store.count(),
            "collection_name": self.vector_store.collection_name,  # Use actual collection name
            "db_path": self.config.db_path,
            "embedding_model": self.config.embedding_model,
            "embedding_dimension": self.embedding_generator.dimension
        }
    
    def clear(self) -> bool:
        """
        Clear all documents from the collection.
        
        Returns:
            True if successful, False otherwise
        """
        return self.vector_store.clear()
