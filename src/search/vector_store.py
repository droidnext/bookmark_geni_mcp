"""
Generic vector store using ChromaDB for semantic search.
"""
import os
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
import hashlib
import logging
import pickle
import numpy as np

logger = logging.getLogger(__name__)


class VectorStore:
    """Generic vector database for storing and querying document embeddings."""
    
    def __init__(
        self,
        db_path: str,
        collection_name: str = "documents",
        embedding_function=None,
        distance_metric: str = "cosine"
    ):
        """
        Initialize the vector store.
        
        Args:
            db_path: Path to ChromaDB storage directory
            collection_name: Name of the ChromaDB collection
            embedding_function: ChromaDB embedding function (optional)
            distance_metric: Distance metric for similarity ("cosine", "l2", "ip")
        """
        self.db_path = db_path
        self.collection_name = collection_name
        self.embedding_function = embedding_function
        self.distance_metric = distance_metric
        self.client = None
        self.collection = None
        self._initialize()
    
    def _initialize(self):
        """Initialize ChromaDB client and collection."""
        try:
            # Create directory if it doesn't exist
            os.makedirs(self.db_path, exist_ok=True)
            
            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(
                path=self.db_path,
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Get or create collection
            metadata = {"description": "Generic document vector store"}
            if self.distance_metric == "cosine":
                metadata["hnsw:space"] = "cosine"
            elif self.distance_metric == "l2":
                metadata["hnsw:space"] = "l2"
            elif self.distance_metric == "ip":
                metadata["hnsw:space"] = "ip"
            
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function,
                metadata=metadata
            )
            
            logger.info(f"Initialized vector store: {self.collection_name}")
            
        except Exception as e:
            logger.error(f"Error initializing ChromaDB: {e}")
            raise
    
    def add(
        self,
        ids: List[str],
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        embeddings: Optional[List[List[float]]] = None
    ) -> bool:
        """
        Add documents to the vector store.
        
        Args:
            ids: List of unique document IDs
            documents: List of document texts for embedding
            metadatas: Optional list of metadata dictionaries
            embeddings: Optional pre-computed embeddings (skips embedding generation)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure metadata values are valid types for ChromaDB
            if metadatas:
                cleaned_metadatas = []
                for metadata in metadatas:
                    cleaned = {}
                    for k, v in metadata.items():
                        if v is None:
                            cleaned[k] = ""
                        elif isinstance(v, (str, int, float, bool)):
                            cleaned[k] = v
                        else:
                            cleaned[k] = str(v)
                    cleaned_metadatas.append(cleaned)
                metadatas = cleaned_metadatas
            
            # Add to collection
            if embeddings:
                self.collection.add(
                    ids=ids,
                    embeddings=embeddings,
                    metadatas=metadatas
                )
            else:
                self.collection.add(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding documents: {e}")
            return False
    
    def upsert(
        self,
        ids: List[str],
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        embeddings: Optional[List[List[float]]] = None
    ) -> bool:
        """
        Upsert (add or update) documents in the vector store.
        
        Args:
            ids: List of unique document IDs
            documents: List of document texts for embedding
            metadatas: Optional list of metadata dictionaries
            embeddings: Optional pre-computed embeddings
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure metadata values are valid types for ChromaDB
            if metadatas:
                cleaned_metadatas = []
                for metadata in metadatas:
                    cleaned = {}
                    for k, v in metadata.items():
                        if v is None:
                            cleaned[k] = ""
                        elif isinstance(v, (str, int, float, bool)):
                            cleaned[k] = v
                        else:
                            cleaned[k] = str(v)
                    cleaned_metadatas.append(cleaned)
                metadatas = cleaned_metadatas
            
            # Upsert to collection
            if embeddings:
                self.collection.upsert(
                    ids=ids,
                    embeddings=embeddings,
                    metadatas=metadatas
                )
            else:
                self.collection.upsert(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Error upserting documents: {e}")
            return False
    
    def query(
        self,
        query_texts: Optional[List[str]] = None,
        query_embeddings: Optional[List[List[float]]] = None,
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None,
        include: List[str] = ["metadatas", "documents", "distances"]
    ) -> Dict[str, Any]:
        """
        Query the vector store for similar documents.
        
        Args:
            query_texts: List of query texts (will be embedded)
            query_embeddings: List of pre-computed query embeddings
            n_results: Number of results to return
            where: Metadata filters (e.g., {"category": "science"})
            include: What to include in results (metadatas, documents, distances, embeddings)
            
        Returns:
            Query results dictionary with ids, distances, metadatas, documents
        """
        try:
            if query_texts:
                return self.collection.query(
                    query_texts=query_texts,
                    n_results=n_results,
                    where=where,
                    include=include
                )
            elif query_embeddings:
                return self.collection.query(
                    query_embeddings=query_embeddings,
                    n_results=n_results,
                    where=where,
                    include=include
                )
            else:
                raise ValueError("Either query_texts or query_embeddings must be provided")
                
        except Exception as e:
            logger.error(f"Error querying documents: {e}")
            return {"ids": [], "distances": [], "metadatas": [], "documents": []}
    
    def get(
        self,
        ids: Optional[List[str]] = None,
        where: Optional[Dict[str, Any]] = None,
        include: List[str] = ["metadatas", "documents"]
    ) -> Dict[str, Any]:
        """
        Get documents by ID or metadata filter.
        
        Args:
            ids: List of document IDs to retrieve
            where: Metadata filters
            include: What to include in results
            
        Returns:
            Documents dictionary with ids, metadatas, documents
        """
        try:
            return self.collection.get(
                ids=ids,
                where=where,
                include=include
            )
        except Exception as e:
            logger.error(f"Error getting documents: {e}")
            return {"ids": [], "metadatas": [], "documents": []}
    
    def delete(self, ids: List[str]) -> bool:
        """
        Delete documents by ID.
        
        Args:
            ids: List of document IDs to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.collection.delete(ids=ids)
            return True
        except Exception as e:
            logger.error(f"Error deleting documents: {e}")
            return False
    
    def update(
        self,
        ids: List[str],
        documents: Optional[List[str]] = None,
        metadatas: Optional[List[Dict[str, Any]]] = None,
        embeddings: Optional[List[List[float]]] = None
    ) -> bool:
        """
        Update existing documents.
        
        Args:
            ids: List of document IDs to update
            documents: Optional updated document texts
            metadatas: Optional updated metadata
            embeddings: Optional updated embeddings
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Clean metadata
            if metadatas:
                cleaned_metadatas = []
                for metadata in metadatas:
                    cleaned = {}
                    for k, v in metadata.items():
                        if v is None:
                            cleaned[k] = ""
                        elif isinstance(v, (str, int, float, bool)):
                            cleaned[k] = v
                        else:
                            cleaned[k] = str(v)
                    cleaned_metadatas.append(cleaned)
                metadatas = cleaned_metadatas
            
            self.collection.update(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings
            )
            return True
        except Exception as e:
            logger.error(f"Error updating documents: {e}")
            return False
    
    def count(self) -> int:
        """Get the total number of documents in the collection."""
        try:
            return self.collection.count()
        except Exception as e:
            logger.error(f"Error getting count: {e}")
            return 0
    
    def clear(self) -> bool:
        """Clear all documents from the collection."""
        try:
            self.client.delete_collection(name=self.collection_name)
            self._initialize()
            return True
        except Exception as e:
            logger.error(f"Error clearing collection: {e}")
            return False
    
    def export_to_pickle(self, pickle_path: str) -> bool:
        """
        Export all embeddings and metadata to a pickle file.
        
        Args:
            pickle_path: Path to save the pickle file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get all data from ChromaDB
            all_data = self.collection.get(include=["embeddings", "metadatas", "documents"])
            
            if not all_data["ids"]:
                logger.warning("No data to export")
                return False
            
            # Prepare data structure
            export_data = {
                "embeddings": {},
                "metadata": {},
                "documents": {}
            }
            
            # Convert embeddings to numpy arrays
            for i, doc_id in enumerate(all_data["ids"]):
                if all_data.get("embeddings") is not None and i < len(all_data["embeddings"]) and all_data["embeddings"][i] is not None:
                    embedding = np.array(all_data["embeddings"][i])
                    export_data["embeddings"][doc_id] = embedding
                
                if all_data.get("metadatas") is not None and i < len(all_data["metadatas"]):
                    export_data["metadata"][doc_id] = all_data["metadatas"][i]
                
                if all_data.get("documents") is not None and i < len(all_data["documents"]):
                    export_data["documents"][doc_id] = all_data["documents"][i]
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(pickle_path) if os.path.dirname(pickle_path) else '.', exist_ok=True)
            
            # Save to pickle file
            with open(pickle_path, 'wb') as f:
                pickle.dump(export_data, f)
            
            logger.info(f"Exported {len(export_data['embeddings'])} documents to {pickle_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting to pickle: {e}")
            return False
    
    def import_from_pickle(self, pickle_path: str) -> bool:
        """
        Import embeddings and metadata from a pickle file.
        
        Args:
            pickle_path: Path to the pickle file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Load pickle file
            with open(pickle_path, 'rb') as f:
                import_data = pickle.load(f)
            
            if not import_data.get("embeddings"):
                logger.error("Invalid pickle file format")
                return False
            
            # Clear existing collection
            try:
                self.client.delete_collection(name=self.collection_name)
            except:
                pass
            
            # Recreate collection
            self._initialize()
            
            # Import data
            ids = list(import_data["embeddings"].keys())
            embeddings_list = [import_data["embeddings"][id].tolist() for id in ids]
            metadatas_list = [import_data["metadata"].get(id, {}) for id in ids]
            
            # Add to ChromaDB (use None for documents since we have embeddings)
            self.collection.add(
                ids=ids,
                embeddings=embeddings_list,
                metadatas=metadatas_list
            )
            
            logger.info(f"Imported {len(ids)} documents from {pickle_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error importing from pickle: {e}")
            return False
