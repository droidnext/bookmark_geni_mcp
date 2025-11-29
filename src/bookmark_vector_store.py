"""
Bookmark-specific wrapper around the generic semantic search module.

This provides backward compatibility with the existing BookmarkVectorStore API
while delegating to the new search module internally.
"""
import logging
from typing import List, Dict, Any, Optional
from src.search import SemanticSearch, SearchConfig

logger = logging.getLogger(__name__)


class BookmarkVectorStore:
    """
    Bookmark-specific vector store wrapping the generic SemanticSearch module.
    
    This class maintains backward compatibility with the original BookmarkVectorStore
    API while using the new reusable search module internally.
    """
    
    def __init__(self, db_path: str, collection_name: str = "bookmark_geni"):
        """
        Initialize the bookmark vector store.
        
        Args:
            db_path: Path to ChromaDB storage directory
            collection_name: Name of the ChromaDB collection
        """
        self.db_path = db_path
        self.collection_name = collection_name
        
        # Initialize semantic search with bookmark configuration
        config = SearchConfig(
            db_path=db_path,
            collection_name=collection_name,
            embedding_model="all-MiniLM-L6-v2",
            distance_metric="cosine"
        )
        
        self.search = SemanticSearch(config=config)
        
        # For backward compatibility, expose some internal components
        self.embedding_function = self.search.embedding_generator.embedding_function
        self.collection = self.search.vector_store.collection
        self.client = self.search.vector_store.client
    
    def _generate_id(self, url: str, browser: str) -> str:
        """Generate a unique ID for a bookmark."""
        import hashlib
        unique_string = f"{url}:{browser}"
        return hashlib.md5(unique_string.encode()).hexdigest()
    
    def _create_embedding_text(self, bookmark: Dict[str, Any]) -> str:
        """
        Create text for embedding from bookmark metadata.
        
        Args:
            bookmark: Bookmark dictionary with url, name, description, content, folder, browser
            
        Returns:
            Combined text string for embedding
        """
        parts = []
        
        if bookmark.get("url"):
            parts.append(f"URL: {bookmark['url']}")
        if bookmark.get("name"):
            parts.append(f"Title: {bookmark['name']}")
        if bookmark.get("description"):
            parts.append(f"Description: {bookmark['description']}")
        if bookmark.get("content"):
            # Include first 1000 chars of content for embedding
            content_preview = bookmark['content'][:1000]
            parts.append(f"Content: {content_preview}")
        if bookmark.get("folder"):
            parts.append(f"Folder: {bookmark['folder']}")
        if bookmark.get("browser"):
            parts.append(f"Browser: {bookmark['browser']}")
        
        return " | ".join(parts)
    
    def store_bookmark(self, bookmark: Dict[str, Any]) -> bool:
        """
        Store a bookmark in the vector database.
        
        Args:
            bookmark: Bookmark dictionary with url, name, description, folder, browser
            
        Returns:
            True if successful, False otherwise
        """
        try:
            bookmark_id = self._generate_id(bookmark["url"], bookmark["browser"])
            embedding_text = self._create_embedding_text(bookmark)
            
            # Prepare metadata
            metadata = {
                "url": bookmark.get("url", ""),
                "name": bookmark.get("name", ""),
                "description": bookmark.get("description", ""),
                "content": bookmark.get("content", ""),
                "folder": bookmark.get("folder", ""),
                "browser": bookmark.get("browser", ""),
                "timestamp": bookmark.get("timestamp", "")
            }
            
            return self.search.store(
                doc_id=bookmark_id,
                text=embedding_text,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error storing bookmark {bookmark.get('url', 'unknown')}: {e}")
            return False
    
    def store_bookmarks(self, bookmarks: List[Dict[str, Any]]) -> int:
        """
        Store multiple bookmarks in batch.
        
        Args:
            bookmarks: List of bookmark dictionaries
            
        Returns:
            Number of successfully stored bookmarks
        """
        if not bookmarks:
            return 0
        
        try:
            # Prepare documents for batch storage
            documents = []
            for bookmark in bookmarks:
                try:
                    bookmark_id = self._generate_id(bookmark["url"], bookmark["browser"])
                    embedding_text = self._create_embedding_text(bookmark)
                    
                    doc = {
                        "id": bookmark_id,
                        "text": embedding_text,
                        "url": bookmark.get("url", ""),
                        "name": bookmark.get("name", ""),
                        "description": bookmark.get("description", ""),
                        "content": bookmark.get("content", ""),
                        "folder": bookmark.get("folder", ""),
                        "browser": bookmark.get("browser", ""),
                        "timestamp": bookmark.get("timestamp", "")
                    }
                    documents.append(doc)
                except Exception as e:
                    logger.error(f"Error preparing bookmark: {e}")
                    continue
            
            if not documents:
                return 0
            
            # Store using batch operation
            return self.search.store_batch(
                documents,
                id_field="id",
                text_field="text",
                metadata_fields=["url", "name", "description", "content", "folder", "browser", "timestamp"]
            )
            
        except Exception as e:
            logger.error(f"Error storing bookmarks batch: {e}")
            return 0
    
    def query_bookmarks(
        self,
        query: str,
        where: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        n_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Query bookmarks using semantic search.
        
        Args:
            query: Search query string
            where: Optional metadata filtering dictionary (e.g., {"browser": "Chrome"})
            limit: Maximum number of results to return
            n_results: Number of results to retrieve (for backward compatibility)
            
        Returns:
            List of matching bookmarks with metadata
        """
        try:
            # Use the smaller of limit and n_results
            actual_limit = min(limit, n_results) if n_results else limit
            
            # Search using semantic search
            results = self.search.search(
                query=query,
                limit=actual_limit,
                filters=where,
                include_distances=True
            )
            
            # Convert to bookmark format
            bookmarks = []
            for result in results:
                metadata = result.get("metadata", {})
                bookmark = {
                    "id": result["id"],
                    "url": metadata.get("url", ""),
                    "name": metadata.get("name", ""),
                    "description": metadata.get("description", ""),
                    "content": metadata.get("content", ""),
                    "folder": metadata.get("folder", ""),
                    "browser": metadata.get("browser", ""),
                    "timestamp": metadata.get("timestamp", ""),
                    "distance": result.get("distance", 0.0)
                }
                bookmarks.append(bookmark)
            
            return bookmarks
            
        except Exception as e:
            logger.error(f"Error querying bookmarks: {e}")
            return []
    
    def update_bookmark_description(self, url: str, browser: str, description: str) -> bool:
        """
        Update the description for an existing bookmark.
        
        Args:
            url: Bookmark URL
            browser: Browser name 
            description: New description text
            
        Returns:
            True if successful, False otherwise
        """
        try:
            bookmark_id = self._generate_id(url, browser)
            
            # Get existing bookmark
            existing_doc = self.search.get(bookmark_id)
            if not existing_doc:
                logger.warning(f"Bookmark not found: {url} ({browser})")
                return False
            
            # Update metadata with new description
            metadata = existing_doc.get("metadata", {})
            metadata["description"] = description
            
            # Recreate embedding text with new description
            bookmark_for_embedding = {
                "url": metadata.get("url", url),
                "name": metadata.get("name", ""),
                "description": description,
                "content": metadata.get("content", ""),
                "folder": metadata.get("folder", ""),
                "browser": metadata.get("browser", browser)
            }
            embedding_text = self._create_embedding_text(bookmark_for_embedding)
            
            # Store updated bookmark
            return self.search.store(
                doc_id=bookmark_id,
                text=embedding_text,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error updating bookmark description {url}: {e}")
            return False
    
    def update_bookmark_descriptions(self, updates: List[Dict[str, str]]) -> int:
        """
        Update descriptions for multiple bookmarks.
        
        Args:
            updates: List of dicts with keys: url, browser, description
            
        Returns:
            Number of successfully updated bookmarks
        """
        updated_count = 0
        for update in updates:
            if self.update_bookmark_description(
                update.get("url", ""),
                update.get("browser", ""),
                update.get("description", "")
            ):
                updated_count += 1
        return updated_count
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection."""
        try:
            stats = self.search.stats()
            return {
                "total_bookmarks": stats["total_documents"],
                "collection_name": self.collection_name,
                "db_path": self.db_path
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {"total_bookmarks": 0}
    
    def delete_bookmark(self, url: str, browser: str) -> bool:
        """
        Delete a bookmark from the database.
        
        Args:
            url: Bookmark URL
            browser: Browser name
            
        Returns:
            True if successful, False otherwise
        """
        try:
            bookmark_id = self._generate_id(url, browser)
            return self.search.delete(bookmark_id)
        except Exception as e:
            logger.error(f"Error deleting bookmark {url}: {e}")
            return False
    
    def clear_collection(self) -> bool:
        """Clear all bookmarks from the collection."""
        try:
            return self.search.clear()
        except Exception as e:
            logger.error(f"Error clearing collection: {e}")
            return False
    
    def url_exists(self, url: str, browser: str) -> bool:
        """
        Check if a URL already exists in the database.
        
        Args:
            url: Bookmark URL
            browser: Browser name
            
        Returns:
            True if URL exists, False otherwise
        """
        try:
            bookmark_id = self._generate_id(url, browser)
            doc = self.search.get(bookmark_id)
            return doc is not None
        except Exception as e:
            logger.error(f"Error checking if URL exists {url}: {e}")
            return False
    
    def _has_valid_description(self, description: str) -> bool:
        """
        Check if a description is valid (not empty and not indicating failure/skip).
        
        Args:
            description: Description string to check
            
        Returns:
            True if description is valid, False otherwise
        """
        if not description or not description.strip():
            return False
        
        description_lower = description.lower().strip()
        
        # Check for failure/skip indicators
        skip_indicators = [
            "skipped:",
            "summary unavailable",
            "summary generation failed",
            "failed to fetch",
            "no meaningful text",
            "authentication",
            "access denied",
            "not accessible"
        ]
        
        for indicator in skip_indicators:
            if indicator in description_lower:
                return False
        
        return len(description.strip()) > 10
    
    def get_existing_urls(self, bookmarks: List[Dict[str, Any]]) -> set:
        """
        Get set of URLs that already exist in the database AND have valid descriptions.
        
        Args:
            bookmarks: List of bookmark dictionaries with 'url' and 'browser' keys
            
        Returns:
            Set of (url, browser) tuples that exist with valid descriptions
        """
        existing = set()
        try:
            for bookmark in bookmarks:
                url = bookmark.get("url", "")
                browser = bookmark.get("browser", "")
                if not url or not browser:
                    continue
                
                bookmark_id = self._generate_id(url, browser)
                doc = self.search.get(bookmark_id)
                
                if doc:
                    metadata = doc.get("metadata", {})
                    description = metadata.get("description", "")
                    
                    if self._has_valid_description(description):
                        existing.add((url, browser))
                    else:
                        logger.debug(f"URL {url} exists but has invalid description, will reprocess")
        
        except Exception as e:
            logger.error(f"Error getting existing URLs: {e}")
        
        return existing
    
    def export_to_pickle(self, pickle_path: str) -> bool:
        """
        Export all embeddings and metadata to a pickle file.
        
        Args:
            pickle_path: Path to save the pickle file
            
        Returns:
            True if successful, False otherwise
        """
        return self.search.vector_store.export_to_pickle(pickle_path)
    
    def import_from_pickle(self, pickle_path: str, embedding_function=None) -> bool:
        """
        Import embeddings and metadata from a pickle file.
        
        Args:
            pickle_path: Path to the pickle file
            embedding_function: Embedding function (optional, for compatibility)
            
        Returns:
            True if successful, False otherwise
        """
        return self.search.vector_store.import_from_pickle(pickle_path)
