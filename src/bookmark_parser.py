"""
Bookmark parsing for different browser formats.
"""
import json
import sqlite3
import os
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


def parse_chromium_bookmarks(file_path: str, browser_name: str) -> List[Dict[str, Any]]:
    """
    Parse Chromium-based browser bookmarks (Chrome, Edge, Opera, Atlas, Comet).
    
    Args:
        file_path: Path to the Bookmarks JSON file
        browser_name: Name of the browser
        
    Returns:
        List of bookmark dictionaries with url, name, folder, browser fields
    """
    logger.info(f"Reading Chromium bookmarks from: {file_path} (browser: {browser_name})")
    bookmarks = []
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        def extract_bookmarks(node: Dict[str, Any], folder_path: str = ""):
            """Recursively extract bookmarks from bookmark tree."""
            if not isinstance(node, dict):
                return
            
            node_type = node.get("type")
            name = node.get("name", "")
            
            if node_type == "url":
                url = node.get("url", "")
                if url:
                    bookmarks.append({
                        "url": url,
                        "name": name,
                        "folder": folder_path.strip("/"),
                        "browser": browser_name
                    })
            elif node_type == "folder":
                current_folder = f"{folder_path}/{name}" if folder_path else name
                for child in node.get("children", []):
                    extract_bookmarks(child, current_folder)
        
        # Process all root nodes
        roots = data.get("roots", {})
        for root_name, root_node in roots.items():
            extract_bookmarks(root_node, root_name)
            
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error parsing Chromium bookmarks from {file_path}: {e}")
    except Exception as e:
        logger.error(f"Error parsing Chromium bookmarks from {file_path}: {e}")
    
    return bookmarks


def parse_firefox_bookmarks(file_path: str, browser_name: str) -> List[Dict[str, Any]]:
    """
    Parse Firefox bookmarks from SQLite database.
    
    Args:
        file_path: Path to the places.sqlite file
        browser_name: Name of the browser
        
    Returns:
        List of bookmark dictionaries with url, name, folder, browser fields
    """
    logger.info(f"Reading Firefox bookmarks from: {file_path} (browser: {browser_name})")
    bookmarks = []
    
    try:
        conn = sqlite3.connect(file_path)
        cursor = conn.cursor()
        
        # Get bookmarks with their folder structure
        # Firefox stores bookmarks in moz_bookmarks and URLs in moz_places
        query = """
        SELECT 
            p.url,
            b.title,
            f.title as folder_title,
            f.parent as folder_id
        FROM moz_bookmarks b
        JOIN moz_places p ON b.fk = p.id
        LEFT JOIN moz_bookmarks f ON b.parent = f.id
        WHERE b.type = 1  -- Type 1 is URL bookmark
        AND p.url IS NOT NULL
        AND p.url != ''
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        # Build folder paths
        folder_map = {}
        folder_query = """
        SELECT id, title, parent
        FROM moz_bookmarks
        WHERE type = 2  -- Type 2 is folder
        """
        cursor.execute(folder_query)
        for folder_id, title, parent_id in cursor.fetchall():
            folder_map[folder_id] = {"title": title, "parent": parent_id}
        
        def get_folder_path(folder_id: Optional[int]) -> str:
            """Build folder path from folder ID."""
            if folder_id is None or folder_id not in folder_map:
                return ""
            folder_info = folder_map[folder_id]
            parent_path = get_folder_path(folder_info["parent"])
            if parent_path:
                return f"{parent_path}/{folder_info['title']}"
            return folder_info["title"]
        
        for url, title, folder_title, folder_id in rows:
            folder_path = get_folder_path(folder_id) if folder_id else ""
            if folder_title and folder_path:
                folder_path = f"{folder_path}/{folder_title}"
            elif folder_title:
                folder_path = folder_title
            
            bookmarks.append({
                "url": url,
                "name": title or "",
                "folder": folder_path,
                "browser": browser_name
            })
        
        conn.close()
        
    except sqlite3.Error as e:
        logger.error(f"SQLite error parsing Firefox bookmarks from {file_path}: {e}")
    except Exception as e:
        logger.error(f"Error parsing Firefox bookmarks from {file_path}: {e}")
    
    return bookmarks


def parse_safari_bookmarks(file_path: str, browser_name: str) -> List[Dict[str, Any]]:
    """
    Parse Safari bookmarks from plist file (macOS only).
    
    Args:
        file_path: Path to the Bookmarks.plist file
        browser_name: Name of the browser
        
    Returns:
        List of bookmark dictionaries with url, name, folder, browser fields
    """
    logger.info(f"Reading Safari bookmarks from: {file_path} (browser: {browser_name})")
    bookmarks = []
    
    try:
        # Import plistlib for macOS
        try:
            import plistlib
        except ImportError:
            # Try using Foundation framework on macOS
            try:
                from Foundation import NSDictionary
                import subprocess
                # Use plutil to convert plist to JSON
                result = subprocess.run(
                    ["plutil", "-convert", "json", "-o", "-", file_path],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                else:
                    print(f"Error converting Safari plist: {result.stderr}")
                    return []
            except Exception as e:
                logger.error(f"Error importing plist parser: {e}")
                return []
        else:
            with open(file_path, "rb") as f:
                data = plistlib.load(f)
        
        def extract_bookmarks(node: Any, folder_path: str = ""):
            """Recursively extract bookmarks from Safari bookmark tree."""
            if isinstance(node, dict):
                # Check if it's a bookmark item
                if "URLString" in node:
                    url = node.get("URLString", "")
                    name = node.get("URIDictionary", {}).get("title", "") or node.get("WebBookmarkTitle", "")
                    if url:
                        bookmarks.append({
                            "url": url,
                            "name": name,
                            "folder": folder_path.strip("/"),
                            "browser": browser_name
                        })
                # Check if it's a folder
                elif "Children" in node or "WebBookmarkType" in node:
                    folder_name = node.get("Title", "") or node.get("WebBookmarkTitle", "")
                    current_folder = f"{folder_path}/{folder_name}" if folder_path and folder_name else (folder_path or folder_name)
                    children = node.get("Children", [])
                    for child in children:
                        extract_bookmarks(child, current_folder)
            elif isinstance(node, list):
                for item in node:
                    extract_bookmarks(item, folder_path)
        
        # Safari stores bookmarks in a nested structure
        if "Children" in data:
            for child in data["Children"]:
                extract_bookmarks(child)
        else:
            extract_bookmarks(data)
            
    except Exception as e:
        logger.error(f"Error parsing Safari bookmarks from {file_path}: {e}")
    
    return bookmarks


def parse_bookmarks(file_path: str, browser_name: str) -> List[Dict[str, Any]]:
    """
    Parse bookmarks from a file based on file extension and browser type.
    
    Args:
        file_path: Path to the bookmark file
        browser_name: Name of the browser
        
    Returns:
        List of bookmark dictionaries
    """
    logger.info(f"Parsing bookmarks from: {file_path} (browser: {browser_name})")
    
    if not os.path.exists(file_path):
        logger.warning(f"Bookmark file does not exist: {file_path}")
        return []
    
    # Determine parser based on file extension
    if file_path.endswith(".sqlite") or file_path.endswith(".sqlite3"):
        logger.debug(f"Detected Firefox SQLite format for: {file_path}")
        return parse_firefox_bookmarks(file_path, browser_name)
    elif file_path.endswith(".plist"):
        logger.debug(f"Detected Safari plist format for: {file_path}")
        return parse_safari_bookmarks(file_path, browser_name)
    else:
        # Assume Chromium JSON format
        logger.debug(f"Detected Chromium JSON format for: {file_path}")
        return parse_chromium_bookmarks(file_path, browser_name)

