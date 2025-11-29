import os
import shutil
import unittest
import tempfile
import numpy as np
import sys
import logging
import chromadb
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.bookmark_vector_store import BookmarkVectorStore

# Configure logging
logging.basicConfig(level=logging.DEBUG)
print(f"ChromaDB Version: {chromadb.__version__}")

class TestVectorStore(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_db")
        self.store = BookmarkVectorStore(self.db_path, collection_name="test_collection")
        
    def tearDown(self):
        shutil.rmtree(self.test_dir)
        
    def test_upsert_and_query(self):
        print("\nTesting Upsert and Query...")
        # 1. Add a bookmark
        bookmark = {
            "url": "http://example.com",
            "name": "Example",
            "description": "An example website",
            "folder": "Work",
            "browser": "Chrome"
        }
        success = self.store.store_bookmark(bookmark)
        self.assertTrue(success)
        
        # Verify it exists
        results = self.store.query_bookmarks("example")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Example")
        
        # 2. Update the bookmark (Upsert)
        bookmark["name"] = "Updated Example"
        bookmark["description"] = "An updated example website"
        success = self.store.store_bookmark(bookmark)
        self.assertTrue(success)
        
        # Verify update
        results = self.store.query_bookmarks("example")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Updated Example")
        print("✅ Upsert verified")
        
    def test_metadata_filtering(self):
        print("\nTesting Metadata Filtering...")
        # Add two bookmarks
        b1 = {"url": "http://a.com", "name": "A", "folder": "Work", "browser": "Chrome"}
        b2 = {"url": "http://b.com", "name": "B", "folder": "Personal", "browser": "Safari"}
        self.store.store_bookmark(b1)
        self.store.store_bookmark(b2)
        
        # Query with filter
        results_work = self.store.query_bookmarks("A", where={"folder": "Work"})
        self.assertEqual(len(results_work), 1)
        self.assertEqual(results_work[0]["name"], "A")
        
        results_safari = self.store.query_bookmarks("B", where={"browser": "Safari"})
        self.assertEqual(len(results_safari), 1)
        self.assertEqual(results_safari[0]["name"], "B")
        
        results_none = self.store.query_bookmarks("A", where={"folder": "Personal"})
        # Ensure "A" is not in results (it should be filtered out)
        # "B" might be returned because it matches the filter and has some similarity
        names = [r["name"] for r in results_none]
        self.assertNotIn("A", names)
        print("✅ Metadata filtering verified")

    def test_export_import(self):
        print("\nTesting Export/Import...")
        # Add a bookmark
        bookmark = {"url": "http://export.com", "name": "Export Me", "browser": "Chrome"}
        self.store.store_bookmark(bookmark)
        
        # Export
        pickle_path = os.path.join(self.test_dir, "export.pkl")
        success = self.store.export_to_pickle(pickle_path)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(pickle_path))
        
        # Clear collection
        self.store.clear_collection()
        results = self.store.query_bookmarks("Export")
        self.assertEqual(len(results), 0)
        
        # Import
        success = self.store.import_from_pickle(pickle_path)
        self.assertTrue(success)
        
        # Verify data is back
        results = self.store.query_bookmarks("Export")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Export Me")
        print("✅ Export/Import verified")

if __name__ == "__main__":
    unittest.main()
