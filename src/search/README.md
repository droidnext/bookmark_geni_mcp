# Semantic Search Module

A reusable, portable semantic search module built on ChromaDB and sentence transformers. Designed to be easily integrated into any Python project.

## Features

- **Simple API**: Clean interface with intuitive methods (`store`, `search`, `get`, `delete`)
- **Automatic Embeddings**: Uses sentence transformers (all-MiniLM-L6-v2) for high-quality embeddings
- **Flexible Storage**: Built on ChromaDB for efficient vector storage and retrieval
- **Batch Operations**: Efficient batch processing for large datasets
- **Metadata Support**: Store and filter by custom metadata
- **Export/Import**: Save and restore collections via pickle files
- **Configurable**: Customize model, distance metric, batch size, and more

## Quick Start

### Installation

```bash
pip install chromadb sentence-transformers
```

### Basic Usage

```python
from search import SemanticSearch

# Initialize
search = SemanticSearch(
    db_path="./my_database",
    collection_name="documents"
)

# Store documents
search.store(
    doc_id="doc1",
    text="Machine learning is a subset of artificial intelligence",
    metadata={"category": "AI", "author": "John"}
)

# Search
results = search.search("what is AI?", limit=5)
for result in results:
    print(f"ID: {result['id']}")
    print(f"Text: {result['text']}")
    print(f"Distance: {result['distance']}")
    print(f"Metadata: {result['metadata']}")
```

### Batch Operations

```python
# Store multiple documents
documents = [
    {
        "id": "doc1",
        "text": "Python is a programming language",
        "category": "programming",
        "tags": "python,language"
    },
    {
        "id": "doc2",
        "text": "Machine learning uses algorithms",
        "category": "AI",
        "tags": "ml,ai"
    }
]

count = search.store_batch(
    documents,
    id_field="id",
    text_field="text",
    metadata_fields=["category", "tags"]
)
print(f"Stored {count} documents")
```

### Search with Filters

```python
# Search with metadata filtering
results = search.search(
    query="programming",
    limit=10,
    filters={"category": "programming"}
)
```

### Retrieve by ID

```python
# Get specific document
doc = search.get("doc1")
if doc:
    print(doc["text"])
    print(doc["metadata"])
```

### Collection Stats

```python
# Get statistics
stats = search.stats()
print(f"Total documents: {stats['total_documents']}")
print(f"Embedding model: {stats['embedding_model']}")
print(f"Embedding dimension: {stats['embedding_dimension']}")
```

## Configuration

Use `SearchConfig` for advanced configuration:

```python
from search import SemanticSearch, SearchConfig

config = SearchConfig(
    db_path="./custom_db",
    collection_name="my_collection",
    embedding_model="all-MiniLM-L6-v2",  # or "all-mpnet-base-v2"
    distance_metric="cosine",  # or "l2", "ip"
    batch_size=100
)

search = SemanticSearch(config=config)
```

### Available Embedding Models

- `all-MiniLM-L6-v2` (default): 384 dimensions, fast, good quality
- `all-mpnet-base-v2`: 768 dimensions, slower, better quality

### Distance Metrics

- `cosine` (default): Cosine similarity (best for most use cases)
- `l2`: Euclidean distance
- `ip`: Inner product

## Advanced Usage

### Custom ID Generation

```python
def my_id_generator(text):
    return f"custom_{hash(text)}"

search = SemanticSearch(
    db_path="./db",
    id_generator=my_id_generator
)
```

### Low-Level Access

```python
from search import VectorStore, EmbeddingGenerator

# Direct vector store access
vector_store = VectorStore(
    db_path="./db",
    collection_name="vectors"
)

# Direct embedding generation
embedding_gen = EmbeddingGenerator(model_name="all-MiniLM-L6-v2")
embedding = embedding_gen.generate("sample text")
```

## Integration into Other Projects

This module is designed to be portable. To use in another project:

1. Copy the entire `search/` directory to your project
2. Install dependencies: `pip install chromadb sentence-transformers`
3. Import and use: `from search import SemanticSearch`

## Architecture

```
search/
├── __init__.py           # Public API exports
├── config.py             # Configuration dataclass
├── embeddings.py         # Embedding generation
├── vector_store.py       # ChromaDB operations
└── semantic_search.py    # High-level interface
```

### Components

- **SemanticSearch**: High-level interface combining all functionality
- **VectorStore**: Low-level ChromaDB vector operations
- **EmbeddingGenerator**: Text-to-embedding conversion
- **SearchConfig**: Configuration management

## API Reference

### SemanticSearch

#### `store(doc_id, text, metadata=None)`
Store a single document.

#### `store_batch(documents, id_field="id", text_field="text", metadata_fields=None)`
Store multiple documents in batch.

#### `search(query, limit=10, filters=None, include_distances=True)`
Search for similar documents.

#### `get(doc_id)`
Retrieve a document by ID.

#### `delete(doc_id)`
Delete a document.

#### `delete_batch(doc_ids)`
Delete multiple documents.

#### `stats()`
Get collection statistics.

#### `clear()`
Clear all documents.

## Requirements

- Python 3.8+
- chromadb
- sentence-transformers
- numpy

## License

This module is part of the Bookmark Geni project and can be freely used and modified.
