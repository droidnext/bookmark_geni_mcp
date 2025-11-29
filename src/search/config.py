"""
Configuration management for semantic search module.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SearchConfig:
    """Configuration for semantic search operations."""
    
    # Database settings
    db_path: str = "./chroma_db"
    collection_name: str = "documents"
    
    # Embedding model settings
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimension: Optional[int] = None  # Auto-detected from model
    
    # Distance metric for similarity search
    # Options: "cosine", "l2", "ip" (inner product)
    distance_metric: str = "cosine"
    
    # Performance settings
    batch_size: int = 100
    
    # Logging
    enable_telemetry: bool = False
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        valid_metrics = ["cosine", "l2", "ip"]
        if self.distance_metric not in valid_metrics:
            raise ValueError(
                f"distance_metric must be one of {valid_metrics}, "
                f"got {self.distance_metric}"
            )
