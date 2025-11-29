"""
Metadata storage in JSON Lines format.
"""
import os
import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class MetadataJSONLWriter:
    """Writes bookmark metadata to JSON Lines file."""
    
    def __init__(self, file_path: str):
        """
        Initialize JSONL writer.
        
        Args:
            file_path: Path to JSONL file
        """
        self.file_path = file_path
        self._ensure_directory()
    
    def _ensure_directory(self):
        """Ensure the directory for the JSONL file exists."""
        directory = os.path.dirname(self.file_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
    
    def write_metadata(self, metadata: Dict[str, Any]) -> bool:
        """
        Write a single metadata record to JSONL file.
        
        Args:
            metadata: Metadata dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(self.file_path, 'a', encoding='utf-8') as f:
                json_line = json.dumps(metadata, ensure_ascii=False)
                f.write(json_line + '\n')
            return True
        except Exception as e:
            logger.error(f"Error writing metadata to JSONL: {e}")
            return False
    
    def write_batch(self, metadata_list: List[Dict[str, Any]]) -> int:
        """
        Write multiple metadata records to JSONL file.
        
        Args:
            metadata_list: List of metadata dictionaries
            
        Returns:
            Number of successfully written records
        """
        written = 0
        for metadata in metadata_list:
            if self.write_metadata(metadata):
                written += 1
        return written
    
    def read_all(self) -> List[Dict[str, Any]]:
        """
        Read all metadata records from JSONL file.
        
        Returns:
            List of metadata dictionaries
        """
        records = []
        if not os.path.exists(self.file_path):
            return records
        
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            record = json.loads(line)
                            records.append(record)
                        except json.JSONDecodeError as e:
                            logger.warning(f"Error parsing JSON line: {e}")
                            continue
        except Exception as e:
            logger.error(f"Error reading JSONL file: {e}")
        
        return records
    
    def get_count(self) -> int:
        """
        Get count of records in JSONL file.
        
        Returns:
            Number of records
        """
        if not os.path.exists(self.file_path):
            return 0
        
        try:
            count = 0
            with open(self.file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        count += 1
            return count
        except Exception as e:
            logger.error(f"Error counting records in JSONL: {e}")
            return 0

