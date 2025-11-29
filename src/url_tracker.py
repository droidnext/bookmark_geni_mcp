"""
URL tracking for ensuring unique URLs are processed only once.
Stores processed URLs in a JSON file for quick reference.
"""
import json
import os
import logging
from typing import Set, List

logger = logging.getLogger(__name__)


class URLTracker:
    """Tracks processed URLs in a JSON file."""
    
    def __init__(self, file_path: str):
        """
        Initialize URL tracker.
        
        Args:
            file_path: Path to JSON file storing URLs
        """
        self.file_path = file_path
        self._ensure_directory()
        self._urls: Set[str] = self._load_urls()
    
    def _ensure_directory(self):
        """Ensure the directory for the URL file exists."""
        directory = os.path.dirname(self.file_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
    
    def _load_urls(self) -> Set[str]:
        """
        Load URLs from JSON file.
        
        Returns:
            Set of URLs
        """
        if not os.path.exists(self.file_path):
            return set()
        
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return set(data)
                elif isinstance(data, dict) and 'urls' in data:
                    return set(data['urls'])
                else:
                    logger.warning(f"Unexpected format in {self.file_path}, starting fresh")
                    return set()
        except json.JSONDecodeError as e:
            logger.warning(f"Error parsing {self.file_path}: {e}, starting fresh")
            return set()
        except Exception as e:
            logger.error(f"Error loading URLs from {self.file_path}: {e}")
            return set()
    
    def _save_urls(self):
        """Save URLs to JSON file."""
        try:
            # Save as a sorted list for readability
            urls_list = sorted(list(self._urls))
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(urls_list, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving URLs to {self.file_path}: {e}")
    
    def is_processed(self, url: str) -> bool:
        """
        Check if a URL has been processed.
        
        Args:
            url: URL to check
            
        Returns:
            True if URL has been processed, False otherwise
        """
        return url in self._urls
    
    def add_url(self, url: str):
        """
        Add a URL to the tracker.
        
        Args:
            url: URL to add
        """
        if url and url not in self._urls:
            self._urls.add(url)
            self._save_urls()
    
    def add_urls(self, urls: List[str]):
        """
        Add multiple URLs to the tracker.
        
        Args:
            urls: List of URLs to add
        """
        new_urls = [url for url in urls if url and url not in self._urls]
        if new_urls:
            self._urls.update(new_urls)
            self._save_urls()
    
    def get_all_urls(self) -> List[str]:
        """
        Get all tracked URLs.
        
        Returns:
            List of URLs (sorted)
        """
        return sorted(list(self._urls))
    
    def get_count(self) -> int:
        """
        Get count of tracked URLs.
        
        Returns:
            Number of URLs
        """
        return len(self._urls)
    
    def filter_unprocessed(self, urls: List[str]) -> List[str]:
        """
        Filter out URLs that have already been processed.
        
        Args:
            urls: List of URLs to filter
            
        Returns:
            List of URLs that haven't been processed yet
        """
        return [url for url in urls if url and not self.is_processed(url)]

