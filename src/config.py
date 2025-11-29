"""
Configuration management for the MCP server.
"""
import yaml
import os
from typing import Dict, Any, List, Optional


def load_config(mcp_server_root: str) -> Dict[str, Any]:
    """
    Load configuration from config.yaml in MCP server root.
    
    Args:
        mcp_server_root: Path to the MCP server root directory
        
    Returns:
        Configuration dictionary
    """
    config_path = os.path.join(mcp_server_root, "config.yaml")
    
    default_config = {
        "debug": False,
        "browsers": {
            "Chrome": {"enabled": True},
            "Safari": {"enabled": True},
            "Edge": {"enabled": True},
            "Firefox": {"enabled": True},
            "Opera": {"enabled": True},
            "ChatGPT Atlas": {"enabled": True},
            "Perplexity Comet": {"enabled": True}
        },
        "chromaDbPath": ".chromadb",
        "metadataJsonlPath": "data/bookmarks_metadata.jsonl",
        "urlJsonPath": "data/urls.json",
        "urlLimit": -1
    }
    
    if not os.path.exists(config_path):
        return default_config
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
        
        # Merge with defaults
        merged_config = default_config.copy()
        merged_config.update(config)
        
        # Resolve relative paths to absolute paths relative to MCP server root
        if "chromaDbPath" in merged_config:
            chroma_path = merged_config["chromaDbPath"]
            if not os.path.isabs(chroma_path):
                merged_config["chromaDbPath"] = os.path.join(mcp_server_root, chroma_path)
            else:
                merged_config["chromaDbPath"] = chroma_path
        
        if "metadataJsonlPath" in merged_config:
            jsonl_path = merged_config["metadataJsonlPath"]
            if not os.path.isabs(jsonl_path):
                merged_config["metadataJsonlPath"] = os.path.join(mcp_server_root, jsonl_path)
            else:
                merged_config["metadataJsonlPath"] = jsonl_path
        
        if "urlJsonPath" in merged_config:
            url_json_path = merged_config["urlJsonPath"]
            if not os.path.isabs(url_json_path):
                merged_config["urlJsonPath"] = os.path.join(mcp_server_root, url_json_path)
            else:
                merged_config["urlJsonPath"] = url_json_path
        else:
            # Default to data/urls.json if not specified
            merged_config["urlJsonPath"] = os.path.join(mcp_server_root, "data", "urls.json")
            
        if "errorUrlsPath" in merged_config:
            error_path = merged_config["errorUrlsPath"]
            if not os.path.isabs(error_path):
                merged_config["errorUrlsPath"] = os.path.join(mcp_server_root, error_path)
            else:
                merged_config["errorUrlsPath"] = error_path
        else:
            # Default to data/error_urls.jsonl if not specified
            merged_config["errorUrlsPath"] = os.path.join(mcp_server_root, "data", "error_urls.jsonl")
        
        return merged_config
        
    except Exception as e:
        print(f"Error loading config: {e}")
        return default_config


def get_enabled_browsers(config: Dict[str, Any]) -> List[str]:
    """
    Get list of enabled browser names from configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        List of enabled browser names
    """
    enabled = []
    browsers_config = config.get("browsers", {})
    
    for browser_name, browser_config in browsers_config.items():
        if isinstance(browser_config, dict):
            if browser_config.get("enabled", True):
                enabled.append(browser_name)
        elif browser_config:  # If it's just a boolean
            enabled.append(browser_name)
    
    return enabled


def get_browser_custom_paths(config: Dict[str, Any], browser_name: str) -> List[str]:
    """
    Get custom bookmark paths for a specific browser from configuration.
    
    Args:
        config: Configuration dictionary
        browser_name: Name of the browser
        
    Returns:
        List of custom paths if specified, empty list otherwise
    """
    browsers_config = config.get("browsers", {})
    browser_config = browsers_config.get(browser_name, {})
    
    if isinstance(browser_config, dict):
        return browser_config.get("paths", [])
    
    return []


def get_chromadb_path(config: Dict[str, Any]) -> str:
    """
    Get ChromaDB storage path from configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        ChromaDB path string
    """
    return config.get("chromaDbPath", ".chromadb")


def get_metadata_jsonl_path(config: Dict[str, Any]) -> str:
    """
    Get JSONL metadata file path from configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        JSONL file path string
    """
    return config.get("metadataJsonlPath", "data/bookmarks_metadata.jsonl")


def get_url_limit(config: Dict[str, Any]) -> int:
    """
    Get URL processing limit from configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        URL limit (-1 means process all, positive number limits processing)
    """
    return config.get("urlLimit", -1)


def get_debug_mode(config: Dict[str, Any]) -> bool:
    """
    Get debug mode flag from configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        True if debug mode is enabled, False otherwise
    """
    return config.get("debug", False)


def get_url_json_path(config: Dict[str, Any]) -> str:
    """
    Get URL JSON file path from configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        URL JSON file path string
    """
    return config.get("urlJsonPath", "data/urls.json")


def get_error_urls_path(config: Dict[str, Any]) -> str:
    """
    Get error URLs JSONL file path from configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Error URLs JSONL file path string
    """
    return config.get("errorUrlsPath", "data/error_urls.jsonl")

