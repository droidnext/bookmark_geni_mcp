import os
import shutil
import unittest
import tempfile
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from search import SemanticSearch, SearchConfig


class TestSemanticSearch(unittest.TestCase):
    """Test the generic semantic search module."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_db")
        
        config = SearchConfig(
            db_path=self.db_path,
            collection_name="test_collection",
            embedding_model="all-MiniLM-L6-v2"
        )
        
        self.search = SemanticSearch(config=config)
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)
    
    def test_store_and_search(self):
        """Test storing and searching documents."""
        print("\n✅ Testing store and search...")
        
        # Store documents
        self.search.store(
            doc_id="doc1",
            text="Machine learning is a subset of artificial intelligence",
            metadata={"category": "AI", "source": "wiki"}
        )
        
        self.search.store(
            doc_id="doc2",
            text="Python is a popular programming language",
            metadata={"category": "programming", "source": "docs"}
        )
        
        # Search
        results = self.search.search("what is AI?", limit=5)
        
        # Verify results
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]["id"], "doc1")
        self.assertIn("distance", results[0])
        
        print(f"   Found {len(results)} results")
        print(f"   Top result: {results[0]['id']}")
    
    def test_store_batch(self):
        """Test batch storage."""
        print("\n✅ Testing batch storage...")
        
        documents = [
            {
                "id": "doc1",
                "text": "Python programming tutorial",
                "category": "programming",
                "tags": "python,tutorial"
            },
            {
                "id": "doc2",
                "text": "Machine learning basics",
                "category": "AI",
                "tags": "ml,ai"
            },
            {
                "id": "doc3",
                "text": "Web development with JavaScript",
                "category": "programming",
                "tags": "js,web"
            }
        ]
        
        count = self.search.store_batch(
            documents,
            id_field="id",
            text_field="text",
            metadata_fields=["category", "tags"]
        )
        
        self.assertEqual(count, 3)
        print(f"   Stored {count} documents")
    
    def test_search_with_filters(self):
        """Test search with metadata filtering."""
        print("\n✅ Testing search with filters...")
        
        # Store documents
        self.search.store("doc1", "Python tutorial", {"category": "programming"})
        self.search.store("doc2", "Python for ML", {"category": "AI"})
        
        # Search with filter
        results = self.search.search(
            query="Python",
            limit=10,
            filters={"category": "programming"}
        )
        
        self.assertGreater(len(results), 0)
        # All results should be programming category
        for result in results:
            self.assertEqual(result["metadata"]["category"], "programming")
        
        print(f"   Found {len(results)} filtered results")
    
    def test_get_and_delete(self):
        """Test get and delete operations."""
        print("\n✅ Testing get and delete...")
        
        # Store document
        self.search.store("doc1", "Test document", {"key": "value"})
        
        # Get document
        doc = self.search.get("doc1")
        self.assertIsNotNone(doc)
        self.assertEqual(doc["id"], "doc1")
        self.assertEqual(doc["text"], "Test document")
        
        # Delete document
        success = self.search.delete("doc1")
        self.assertTrue(success)
        
        # Verify deleted
        doc = self.search.get("doc1")
        self.assertIsNone(doc)
        
        print("   Get and delete operations verified")
    
    def test_stats(self):
        """Test collection statistics."""
        print("\n✅ Testing stats...")
        
        # Store some documents
        self.search.store("doc1", "Document 1")
        self.search.store("doc2", "Document 2")
        
        # Get stats
        stats = self.search.stats()
        
        self.assertEqual(stats["total_documents"], 2)
        self.assertEqual(stats["collection_name"], "test_collection")
        self.assertIn("embedding_model", stats)
        
        print(f"   Total documents: {stats['total_documents']}")
        print(f"   Embedding dimension: {stats['embedding_dimension']}")
    
    def test_clear(self):
        """Test clearing collection."""
        print("\n✅ Testing clear...")
        
        # Store documents
        self.search.store("doc1", "Document 1")
        self.search.store("doc2", "Document 2")
        
        # Clear
        success = self.search.clear()
        self.assertTrue(success)
        
        # Verify empty
        stats = self.search.stats()
        self.assertEqual(stats["total_documents"], 0)
        
        print("   Collection cleared successfully")


if __name__ == "__main__":
    unittest.main()
