"""
Text embedding generation using sentence transformers.
"""
import logging
from typing import List, Union
from chromadb.utils import embedding_functions

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generate text embeddings using sentence transformer models."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the embedding generator.
        
        Args:
            model_name: Name of the sentence transformer model to use.
                       Default is "all-MiniLM-L6-v2" (384 dimensions, fast, good quality)
                       Other options: "all-mpnet-base-v2" (768 dim, slower, better quality)
        """
        self.model_name = model_name
        self._embedding_function = None
        self._initialize()
    
    def _initialize(self):
        """Initialize the sentence transformer embedding function."""
        try:
            self._embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=self.model_name
            )
            logger.info(f"Initialized sentence transformer model: {self.model_name}")
        except Exception as e:
            logger.error(f"Error initializing embedding model: {e}")
            raise
    
    def generate(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """
        Generate embeddings for one or more text strings.
        
        Args:
            text: Single text string or list of text strings
            
        Returns:
            If input is a string: List of floats (embedding vector)
            If input is a list: List of embedding vectors
        """
        try:
            if isinstance(text, str):
                return self._embedding_function([text])[0]
            else:
                return self._embedding_function(text)
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise
    
    def generate_batch(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """
        Generate embeddings for a large list of texts in batches.
        
        Args:
            texts: List of text strings
            batch_size: Number of texts to process per batch
            
        Returns:
            List of embedding vectors
        """
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            try:
                embeddings = self._embedding_function(batch)
                all_embeddings.extend(embeddings)
            except Exception as e:
                logger.error(f"Error generating embeddings for batch {i//batch_size}: {e}")
                # Add None for failed embeddings
                all_embeddings.extend([None] * len(batch))
        
        return all_embeddings
    
    @property
    def embedding_function(self):
        """Get the underlying ChromaDB embedding function."""
        return self._embedding_function
    
    @property
    def dimension(self) -> int:
        """Get the embedding dimension for this model."""
        # Generate a sample embedding to determine dimension
        sample = self.generate("sample text")
        return len(sample)
