#!/usr/bin/env python3
"""
MCP server for bookmark metadata generation and querying.
"""
import os
import sys
import json
import logging
import asyncio
import time
from typing import Any, List, Optional

# CRITICAL: Set stdout to unbuffered for MCP stdio protocol
# This ensures MCP protocol messages are sent immediately without buffering
sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None
sys.stderr.reconfigure(line_buffering=True) if hasattr(sys.stderr, 'reconfigure') else None

# CRITICAL: Log immediately to stderr to verify server is being invoked
# This must happen before any other imports or operations
sys.stderr.write("[MCP SERVER] Script started\n")
sys.stderr.write(f"[MCP SERVER] Python: {sys.executable}\n")
sys.stderr.write(f"[MCP SERVER] Script: {__file__}\n")
sys.stderr.write(f"[MCP SERVER] Working directory: {os.getcwd()}\n")
sys.stderr.write(f"[MCP SERVER] Python path: {sys.path[:3]}\n")
sys.stderr.flush()

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stderr.write(f"[MCP SERVER] Added to path: {os.path.join(os.path.dirname(__file__), '..')}\n")
sys.stderr.flush()

try:
    sys.stderr.write("[MCP SERVER] Importing FastMCP...\n")
    sys.stderr.flush()
    from fastmcp import FastMCP
    sys.stderr.write("[MCP SERVER] FastMCP imported successfully\n")
    sys.stderr.flush()
except Exception as e:
    sys.stderr.write(f"[MCP SERVER] ERROR importing FastMCP: {e}\n")
    sys.stderr.flush()
    raise

try:
    sys.stderr.write("[MCP SERVER] Importing local modules...\n")
    sys.stderr.flush()
    from src.browser_detector import get_available_browsers, get_browser_paths, BROWSERS
    from src.bookmark_parser import parse_bookmarks
    from src.metadata_generator import generate_metadata_batch
    from src.bookmark_vector_store import BookmarkVectorStore
    from src.config import (
    load_config, 
    get_enabled_browsers, 
    get_chromadb_path, 
    get_metadata_jsonl_path,
    get_url_limit,
    get_debug_mode,
    get_url_json_path,
    get_error_urls_path,
    get_browser_custom_paths
)
    from src.metadata_storage import MetadataJSONLWriter
    from src.url_tracker import URLTracker
    sys.stderr.write("[MCP SERVER] Local modules imported successfully\n")
    sys.stderr.flush()
except Exception as e:
    sys.stderr.write(f"[MCP SERVER] ERROR importing local modules: {e}\n")
    sys.stderr.write(f"[MCP SERVER] Traceback:\n")
    import traceback
    traceback.print_exc(file=sys.stderr)
    sys.stderr.flush()
    raise

# Global state - load config first to check debug mode
sys.stderr.write("[MCP SERVER] Loading configuration...\n")
sys.stderr.flush()
# Get MCP server root (parent of servers folder)
mcp_server_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.stderr.write(f"[MCP SERVER] MCP server root: {mcp_server_root}\n")
sys.stderr.flush()

try:
    config = load_config(mcp_server_root)
    sys.stderr.write(f"[MCP SERVER] Config loaded: {bool(config)}\n")
    sys.stderr.flush()
except Exception as e:
    sys.stderr.write(f"[MCP SERVER] ERROR loading config: {e}\n")
    sys.stderr.flush()
    raise

try:
    debug_mode = get_debug_mode(config)
    sys.stderr.write(f"[MCP SERVER] Debug mode: {debug_mode}\n")
    sys.stderr.flush()
except Exception as e:
    sys.stderr.write(f"[MCP SERVER] ERROR getting debug mode: {e}\n")
    sys.stderr.flush()
    debug_mode = False

# Configure logging based on debug mode
# In debug mode, log everything to stderr; otherwise use WARNING level
log_level = logging.DEBUG if debug_mode else logging.WARNING
logging.basicConfig(
    level=log_level,
    format='[%(asctime)s] %(name)s:%(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stderr  # Always log to stderr to avoid interfering with MCP stdio
)
logger = logging.getLogger(__name__)

# Create a debug logger that writes to stderr
debug_logger = logging.getLogger("debug")
debug_handler = logging.StreamHandler(sys.stderr)
debug_handler.setLevel(logging.DEBUG if debug_mode else logging.WARNING)
debug_handler.setFormatter(logging.Formatter('[DEBUG] %(message)s'))
debug_logger.addHandler(debug_handler)
debug_logger.setLevel(logging.DEBUG if debug_mode else logging.WARNING)
debug_logger.propagate = False

# Create a progress logger that writes to stderr
progress_logger = logging.getLogger("progress")
progress_handler = logging.StreamHandler(sys.stderr)
progress_handler.setLevel(logging.INFO)
progress_handler.setFormatter(logging.Formatter('%(message)s'))
progress_logger.addHandler(progress_handler)
progress_logger.setLevel(logging.INFO)
progress_logger.propagate = False

# Debug logging for startup
if debug_mode:
    debug_logger.debug("="*60)
    debug_logger.debug("MCP SERVER STARTUP")
    debug_logger.debug("="*60)
    debug_logger.debug(f"MCP server root: {mcp_server_root}")
    debug_logger.debug(f"Python version: {sys.version}")
    debug_logger.debug(f"Python executable: {sys.executable}")
    debug_logger.debug(f"Debug mode: {debug_mode}")
    debug_logger.debug(f"Config loaded: {bool(config)}")
    debug_logger.debug(f"Environment variables:")

# Initialize MCP server
sys.stderr.write("[MCP SERVER] Initializing FastMCP server...\n")
sys.stderr.flush()

if debug_mode:
    debug_logger.debug("Initializing FastMCP server...")

try:
    mcp = FastMCP(
        "Bookmark Geni",
        instructions="This server provides tools for processing browser bookmarks, extracting HTML content, and querying them using semantic search. Available tools: generate_bookmarks_metadata, query_bookmarks, list_browsers, get_stats, export_embeddings, import_embeddings."
    )
    sys.stderr.write(f"[MCP SERVER] FastMCP server initialized: {mcp.name}\n")
    sys.stderr.flush()
except Exception as e:
    sys.stderr.write(f"[MCP SERVER] ERROR initializing FastMCP: {e}\n")
    import traceback
    traceback.print_exc(file=sys.stderr)
    sys.stderr.flush()
    raise

if debug_mode:
    debug_logger.debug(f"MCP server initialized: {mcp.name}")
    debug_logger.debug(f"MCP instructions: {mcp.instructions[:100]}...")

sys.stderr.write("[MCP SERVER] Server initialization complete, registering tools...\n")
sys.stderr.flush()

vector_store = None
jsonl_writer = None
url_tracker = None


def get_vector_store():
    """Get or initialize vector store."""
    global vector_store
    if vector_store is None:
        db_path = get_chromadb_path(config)
        vector_store = BookmarkVectorStore(db_path)
    return vector_store


def get_jsonl_writer():
    """Get or initialize JSONL writer."""
    global jsonl_writer
    if jsonl_writer is None:
        jsonl_path = get_metadata_jsonl_path(config)
        jsonl_writer = MetadataJSONLWriter(jsonl_path)
    return jsonl_writer


def get_url_tracker():
    """Get or create URL tracker instance."""
    global url_tracker
    if url_tracker is None:
        url_json_path = get_url_json_path(config)
        url_tracker = URLTracker(url_json_path)
    return url_tracker


# Register tools with logging
sys.stderr.write("[MCP SERVER] Registering tool: list_browsers\n")
sys.stderr.flush()

@mcp.tool()
def list_browsers() -> str:
    """
    List available browsers and their detected bookmark file paths.
    Returns a JSON string with browser names and paths.
    """
    try:
        if debug_mode:
            debug_logger.debug("Tool called: list_browsers()")
        
        # Extract custom paths from config
        custom_paths_config = {}
        for browser in ["Chrome", "Edge", "Firefox", "Opera", "ChatGPT Atlas", "Perplexity Comet"]:
            paths = get_browser_custom_paths(config, browser)
            if paths:
                custom_paths_config[browser] = paths
                
        available = get_available_browsers(custom_paths_config)
        
        if debug_mode:
            debug_logger.debug(f"Found {len(available)} available browsers (including custom paths)")
        
        result = {
            "available_browsers": list(available.keys()),
            "browser_details": {}
        }
        
        for browser_name, paths in available.items():
            result["browser_details"][browser_name] = {
                "paths": paths,
                "bookmark_count": "unknown"  # Could be calculated if needed
            }
            if debug_mode:
                debug_logger.debug(f"  Browser: {browser_name}, paths: {len(paths)}")
        
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error listing browsers: {e}")
        if debug_mode:
            debug_logger.debug(f"Exception in list_browsers: {e}", exc_info=True)
        return json.dumps({"error": str(e)})


sys.stderr.write("[MCP SERVER] Registering tool: generate_bookmarks_metadata\n")
sys.stderr.flush()

@mcp.tool()
async def generate_bookmarks_metadata(
    browsers: Optional[str] = None,
    interactive: bool = False
) -> str:
    """
    Generate metadata for bookmarks from selected browsers.
    
    Args:
        browsers: Comma-separated list of browser names, or "All" for all browsers. 
                  Defaults to "Chrome" if not provided.
        interactive: Whether to prompt for browser selection (not implemented in MCP, handled by CLI)
    
    Returns:
        JSON string with generation results
    """
    try:
        if debug_mode:
            debug_logger.debug("="*60)
            debug_logger.debug("Tool called: generate_bookmarks_metadata()")
            debug_logger.debug(f"  Parameters: browsers={browsers}, interactive={interactive}")
            debug_logger.debug("="*60)
        
        progress_logger.info("🚀 Starting bookmark metadata generation...")
        
        # Get enabled browsers from config
        # config = load_config(mcp_server_root) # Config is already loaded globally
        enabled_browsers = get_enabled_browsers(config)
        
        # Extract custom paths from config
        custom_paths_config = {}
        for browser in ["Chrome", "Edge", "Firefox", "Opera", "ChatGPT Atlas", "Perplexity Comet"]:
            paths = get_browser_custom_paths(config, browser)
            if paths:
                custom_paths_config[browser] = paths

        # Determine which browsers to process - default to "Chrome" if not provided
        if browsers:
            if browsers.lower() == "all":
                browser_list = list(get_available_browsers(custom_paths_config).keys())
            else:
                browser_list = [b.strip() for b in browsers.split(",")]
        else:
            # Default to Chrome if not specified
            browser_list = ["Chrome"]
        
        if not browser_list:
            progress_logger.error("❌ No browsers specified or available")
            return json.dumps({"error": "No browsers specified or available"})
        
        progress_logger.info(f"📋 Browsers to process: {', '.join(browser_list)}")
        
        # Get vector store
        progress_logger.info("🔧 Initializing vector store...")
        store = get_vector_store()
        progress_logger.info("✅ Vector store initialized")
        
        all_bookmarks = []
        all_skipped = []
        all_existing = []  # Track URLs that were skipped because they already exist
        processed_count = 0
        error_count = 0
        
        # Get available browsers map
        available_browsers_map = get_available_browsers(custom_paths_config)
        
        # Process each browser
        for browser_name in browser_list:
            if browser_name not in available_browsers_map:
                logger.warning(f"Browser {browser_name} not found or no bookmarks detected")
                continue
            
            try:
                # Get paths for this browser from the available browsers map
                paths = available_browsers_map[browser_name]
                progress_logger.info(f"   Detected {len(paths)} bookmark file path(s) for {browser_name}")
                
                if not paths:
                    progress_logger.warning(f"   ⚠️  No bookmark paths found for {browser_name}")
                    logger.info(f"No bookmark paths found for {browser_name}")
                    continue
                
                # Log all detected paths
                for i, path in enumerate(paths, 1):
                    progress_logger.info(f"   📁 Path {i}/{len(paths)}: {path}")
                    logger.info(f"Bookmark path {i} for {browser_name}: {path}")
                
                # Parse bookmarks from all paths
                browser_bookmarks = []
                progress_logger.info(f"\n🔍 Reading bookmarks from {browser_name}...")
                for path_idx, path in enumerate(paths, 1):
                    try:
                        progress_logger.info(f"   📖 [{path_idx}/{len(paths)}] Reading bookmark file: {path}")
                        logger.info(f"Parsing bookmarks from {path} (browser: {browser_name})")
                        bookmarks = parse_bookmarks(path, browser_name)
                        browser_bookmarks.extend(bookmarks)
                        progress_logger.info(f"      ✅ Found {len(bookmarks)} bookmarks in this file")
                        logger.info(f"Found {len(bookmarks)} bookmarks in {path}")
                    except Exception as e:
                        progress_logger.error(f"      ❌ Error parsing {path}: {e}")
                        logger.error(f"Error parsing {path}: {e}", exc_info=True)
                        error_count += 1
                
                progress_logger.info(f"   📊 Total bookmarks found from {browser_name}: {len(browser_bookmarks)}")
                logger.info(f"Total bookmarks found from {browser_name}: {len(browser_bookmarks)}")
                
                if browser_bookmarks:
                    # Get URL tracker
                    tracker = get_url_tracker()
                    
                    # First, filter out URLs that have already been processed (unique URL check)
                    progress_logger.info(f"\n🔍 Checking URL tracker for previously processed URLs...")
                    unprocessed_bookmarks = []
                    url_tracker_skipped = []
                    
                    for bm in browser_bookmarks:
                        url = bm.get("url", "")
                        if url and tracker.is_processed(url):
                            url_tracker_skipped.append({
                                "url": url,
                                "browser": bm.get("browser", ""),
                                "reason": "URL already processed (unique URL check)"
                            })
                        else:
                            unprocessed_bookmarks.append(bm)
                    
                    if url_tracker_skipped:
                        progress_logger.info(f"   ⏭️  Found {len(url_tracker_skipped)} URLs already processed (skipping duplicates)...")
                        all_existing.extend(url_tracker_skipped)
                    
                    # Then check ChromaDB for existing URLs with valid descriptions
                    progress_logger.info(f"🔍 Checking ChromaDB for existing bookmarks with valid descriptions...")
                    existing_urls = store.get_existing_urls(unprocessed_bookmarks)
                    existing_count = len(existing_urls)
                    
                    # Track existing URLs for reporting
                    if existing_count > 0:
                        progress_logger.info(f"   ⏭️  Found {existing_count} bookmarks already in ChromaDB with valid descriptions, skipping...")
                        all_existing.extend([
                            {"url": url, "browser": browser, "reason": "Already in ChromaDB with valid description"}
                            for url, browser in existing_urls
                        ])
                        # Filter out existing bookmarks
                        new_bookmarks = [
                            bm for bm in unprocessed_bookmarks
                            if (bm.get("url", ""), bm.get("browser", "")) not in existing_urls
                        ]
                        progress_logger.info(f"   ✨ {len(new_bookmarks)} bookmarks to process (new or need reprocessing)")
                    else:
                        new_bookmarks = unprocessed_bookmarks
                        progress_logger.info(f"   ✨ All {len(unprocessed_bookmarks)} bookmarks are new or need processing")
                    
                    # Apply URL limit if configured
                    url_limit = get_url_limit(config)
                    if url_limit > 0 and len(new_bookmarks) > url_limit:
                        progress_logger.info(f"   ⚠️  Limiting processing to {url_limit} URLs (found {len(new_bookmarks)} total)")
                        new_bookmarks = new_bookmarks[:url_limit]
                    
                    # Only process new bookmarks
                    if new_bookmarks:
                        # Generate metadata with summaries (async)
                        progress_logger.info(f"\n📚 Processing {len(new_bookmarks)} new bookmarks from {browser_name}...")
                        metadata_list, skipped_list = await generate_metadata_batch(new_bookmarks, include_content=True, progress_logger=progress_logger)
                    else:
                        progress_logger.info(f"\n✅ All bookmarks from {browser_name} already processed, skipping...")
                        metadata_list = []
                        skipped_list = []
                    
                    # Store skipped bookmarks for reporting (and error logging)
                    all_skipped.extend(skipped_list)
                    
                    # Write errors to error_urls.jsonl
                    if skipped_list:
                        error_path = get_error_urls_path(config)
                        try:
                            # Append to error file
                            with open(error_path, 'a', encoding='utf-8') as f:
                                for error_item in skipped_list:
                                    # Add timestamp
                                    error_item['timestamp'] = time.time()
                                    f.write(json.dumps(error_item) + '\n')
                            progress_logger.info(f"   ⚠️  Logged {len(skipped_list)} errors to {error_path}")
                        except Exception as e:
                            logger.error(f"Error writing to error log: {e}")
                    
                    # Store in JSONL file
                    jsonl_writer = get_jsonl_writer()
                    progress_logger.info(f"💾 Writing {len(metadata_list)} bookmarks to JSONL file...")
                    jsonl_written = jsonl_writer.write_batch(metadata_list)
                    progress_logger.info(f"   ✅ Written {jsonl_written} records to {jsonl_writer.file_path}")
                    
                    # Store in vector database
                    progress_logger.info(f"💾 Storing {len(metadata_list)} bookmarks in vector database...")
                    stored = store.store_bookmarks(metadata_list)
                    processed_count += stored
                    all_bookmarks.extend(metadata_list)
                    
                    # Add successfully processed URLs to tracker
                    if metadata_list:
                        tracker = get_url_tracker()
                        processed_urls = [m.get("url", "") for m in metadata_list if m.get("url")]
                        tracker.add_urls(processed_urls)
                        progress_logger.info(f"   📝 Added {len(processed_urls)} URLs to URL tracker")
                    
                    progress_logger.info(f"✅ Successfully processed {stored} bookmarks from {browser_name} ({len(skipped_list)} skipped)\n")
                    
            except Exception as e:
                logger.error(f"Error processing {browser_name}: {e}")
                error_count += 1
        
        # Get JSONL file info
        jsonl_writer = get_jsonl_writer()
        jsonl_count = jsonl_writer.get_count()
        jsonl_path = jsonl_writer.file_path
        
        # Get URL tracker info
        tracker = get_url_tracker()
        url_tracker_count = tracker.get_count()
        url_tracker_path = tracker.file_path
        
        progress_logger.info("\n" + "="*60)
        progress_logger.info("📊 Generation Summary:")
        progress_logger.info(f"   Browsers processed: {len(browser_list)}")
        progress_logger.info(f"   Total bookmarks processed: {len(all_bookmarks)}")
        progress_logger.info(f"   Already processed (skipped): {len(all_existing)}")
        progress_logger.info(f"   Successfully stored: {processed_count}")
        progress_logger.info(f"   Skipped (auth/access issues): {len(all_skipped)}")
        progress_logger.info(f"   Errors: {error_count}")
        progress_logger.info(f"   JSONL file: {jsonl_path}")
        progress_logger.info(f"   Total records in JSONL: {jsonl_count}")
        progress_logger.info(f"   URL tracker file: {url_tracker_path}")
        progress_logger.info(f"   Total unique URLs tracked: {url_tracker_count}")
        
        # Report skipped URLs
        if all_skipped:
            progress_logger.info("\n⏭️  Skipped URLs (authentication/access issues):")
            for skipped in all_skipped[:20]:  # Show first 20
                progress_logger.info(f"   - {skipped['name'][:50]}: {skipped['reason']}")
                progress_logger.info(f"     URL: {skipped['url'][:80]}")
            if len(all_skipped) > 20:
                progress_logger.info(f"   ... and {len(all_skipped) - 20} more")
        
        progress_logger.info("="*60 + "\n")
        
        result = {
            "success": True,
            "browsers_processed": browser_list,
            "total_bookmarks": len(all_bookmarks),
            "already_existing": len(all_existing),
            "stored_count": processed_count,
            "skipped_count": len(all_skipped),
            "skipped_urls": all_skipped,
            "existing_urls": all_existing[:20],  # Include first 20 for reference
            "error_count": error_count,
            "message": f"Successfully processed {processed_count} bookmarks from {len(browser_list)} browser(s), skipped {len(all_existing)} URLs with valid descriptions and {len(all_skipped)} URLs with access issues"
        }
        
        if debug_mode:
            debug_logger.debug("generate_bookmarks_metadata completed successfully")
            debug_logger.debug(f"  Processed: {processed_count} bookmarks")
            debug_logger.debug(f"  Skipped: {len(all_skipped)} URLs")
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"Error in generate_bookmarks_metadata: {e}")
        if debug_mode:
            debug_logger.debug(f"Exception in generate_bookmarks_metadata: {e}", exc_info=True)
        return json.dumps({"error": str(e), "success": False})


sys.stderr.write("[MCP SERVER] Registering tool: query_bookmarks\n")
sys.stderr.flush()

@mcp.tool()
def query_bookmarks(query: str, limit: int = 10) -> str:
    """
    Query bookmarks using semantic search.
    
    Args:
        query: Search query string
        limit: Maximum number of results to return
    
    Returns:
        JSON string with matching bookmarks with content and matchin URL's 
    """
    try:
        if debug_mode:
            debug_logger.debug("Tool called: query_bookmarks()")
            debug_logger.debug(f"  Parameters: query='{query}', limit={limit}")
        
        store = get_vector_store()
        
        if not query or not query.strip():
            if debug_mode:
                debug_logger.debug("Query string is empty")
            return json.dumps({"error": "Query string is required"})
        
        # Perform semantic search
        if debug_mode:
            debug_logger.debug(f"Performing semantic search for: '{query.strip()}'")
        results = store.query_bookmarks(query.strip(), limit=limit)
        
        if debug_mode:
            debug_logger.debug(f"Found {len(results)} results")
        
        # Format results
        formatted_results = []
        for bookmark in results:
            formatted_results.append({
                "url": bookmark.get("url", ""),
                "name": bookmark.get("name", ""),
                "description": bookmark.get("description", ""),
                "content": bookmark.get("content", ""),
                "folder": bookmark.get("folder", ""),
                "browser": bookmark.get("browser", ""),
                "relevance_score": 1.0 - bookmark.get("distance", 1.0)  # Convert distance to similarity
            })
        
        result = {
            "query": query,
            "results_count": len(formatted_results),
            "results": formatted_results
        }
        
        return json.dumps(result, indent=2)
    
    except Exception as e:
        logger.error(f"Error in query_bookmarks: {e}")
        if debug_mode:
            debug_logger.debug(f"Exception in query_bookmarks: {e}", exc_info=True)
        return json.dumps({"error": str(e)})


sys.stderr.write("[MCP SERVER] Registering tool: export_embeddings\n")
sys.stderr.flush()

@mcp.tool()
def export_embeddings(pickle_path: Optional[str] = None) -> str:
    """
    Export all embeddings and metadata to a pickle file.
    This allows transferring data to a remote server.
    
    Args:
        pickle_path: Path to save the pickle file (default: data/bookmarks_embeddings.pkl)
    
    Returns:
        JSON string with export results
    """
    try:
        if debug_mode:
            debug_logger.debug("Tool called: export_embeddings()")
            debug_logger.debug(f"  Parameters: pickle_path={pickle_path}")
        
        progress_logger.info("📦 Exporting embeddings and metadata to pickle file...")
        
        # Default path
        if not pickle_path:
            pickle_path = os.path.join(mcp_server_root, "data", "bookmarks_embeddings.pkl")
        
        # Ensure absolute path
        if not os.path.isabs(pickle_path):
            pickle_path = os.path.join(mcp_server_root, pickle_path)
        
        store = get_vector_store()
        success = store.export_to_pickle(pickle_path)
        
        if success:
            # Get file size
            file_size = os.path.getsize(pickle_path) / (1024 * 1024)  # MB
            progress_logger.info(f"✅ Successfully exported embeddings to {pickle_path}")
            progress_logger.info(f"   File size: {file_size:.2f} MB")
            
            result = {
                "success": True,
                "pickle_path": pickle_path,
                "file_size_mb": round(file_size, 2),
                "message": f"Successfully exported embeddings to {pickle_path}"
            }
        else:
            result = {
                "success": False,
                "error": "Failed to export embeddings"
            }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"Error exporting embeddings: {e}")
        if debug_mode:
            debug_logger.debug(f"Exception in export_embeddings: {e}", exc_info=True)
        return json.dumps({"error": str(e), "success": False})


sys.stderr.write("[MCP SERVER] Registering tool: import_embeddings\n")
sys.stderr.flush()

@mcp.tool()
def import_embeddings(pickle_path: str) -> str:
    """
    Import embeddings and metadata from a pickle file.
    This allows loading data on a remote server.
    
    Args:
        pickle_path: Path to the pickle file to import
    
    Returns:
        JSON string with import results
    """
    try:
        if debug_mode:
            debug_logger.debug("Tool called: import_embeddings()")
            debug_logger.debug(f"  Parameters: pickle_path={pickle_path}")
        
        progress_logger.info(f"📥 Importing embeddings and metadata from pickle file...")
        progress_logger.info(f"   Source: {pickle_path}")
        
        # Ensure absolute path
        if not os.path.isabs(pickle_path):
            pickle_path = os.path.join(mcp_server_root, pickle_path)
        
        if not os.path.exists(pickle_path):
            return json.dumps({
                "success": False,
                "error": f"Pickle file not found: {pickle_path}"
            })
        
        store = get_vector_store()
        success = store.import_from_pickle(pickle_path)
        
        if success:
            # Get stats after import
            stats = store.get_collection_stats()
            progress_logger.info(f"✅ Successfully imported embeddings from {pickle_path}")
            progress_logger.info(f"   Total bookmarks: {stats.get('total_bookmarks', 0)}")
            
            result = {
                "success": True,
                "pickle_path": pickle_path,
                "total_bookmarks": stats.get("total_bookmarks", 0),
                "message": f"Successfully imported {stats.get('total_bookmarks', 0)} bookmarks from {pickle_path}"
            }
        else:
            result = {
                "success": False,
                "error": "Failed to import embeddings"
            }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"Error importing embeddings: {e}")
        if debug_mode:
            debug_logger.debug(f"Exception in import_embeddings: {e}", exc_info=True)
        return json.dumps({"error": str(e), "success": False})


sys.stderr.write("[MCP SERVER] Registering tool: get_stats\n")
sys.stderr.flush()

@mcp.tool()
def get_stats() -> str:
    """
    Get statistics about the bookmark database.
    
    Returns:
        JSON string with database statistics
    """
    try:
        if debug_mode:
            debug_logger.debug("Tool called: get_stats()")
        
        store = get_vector_store()
        stats = store.get_collection_stats()
        
        if debug_mode:
            debug_logger.debug(f"Stats retrieved: {json.dumps(stats, indent=2)}")
        
        return json.dumps(stats, indent=2)
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        if debug_mode:
            debug_logger.debug(f"Exception in get_stats: {e}", exc_info=True)
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Bookmark Geni MCP Server")
    parser.add_argument("--transport", default="stdio", choices=["stdio", "sse"], help="Transport mode (stdio or sse)")
    parser.add_argument("--host", default="localhost", help="Host for SSE server")
    parser.add_argument("--port", type=int, default=8000, help="Port for SSE server")
    
    args = parser.parse_args()
    
    sys.stderr.write("[MCP SERVER] All tools registered, entering main block\n")
    sys.stderr.flush()
    
    if debug_mode:
        debug_logger.debug("="*60)
        debug_logger.debug("REGISTERING TOOLS")
        debug_logger.debug("="*60)
        # Try to list registered tools
        try:
            # FastMCP registers tools via decorators, so we can't easily list them here
            # But we can log that they should be registered
            debug_logger.debug("Tools registered via @mcp.tool() decorators:")
            debug_logger.debug("  - generate_bookmarks_metadata")
            debug_logger.debug("  - query_bookmarks")
            debug_logger.debug("  - list_browsers")
            debug_logger.debug("  - get_stats")
        except Exception as e:
            debug_logger.debug(f"Could not list tools: {e}")
        
        debug_logger.debug("="*60)
        debug_logger.debug(f"STARTING MCP SERVER ({args.transport} transport)")
        debug_logger.debug("="*60)
        if args.transport == "stdio":
            debug_logger.debug("Waiting for MCP protocol messages on stdin...")
            debug_logger.debug("Debug logs will appear on stderr")
        else:
            debug_logger.debug(f"Listening on http://{args.host}:{args.port}")
        debug_logger.debug("="*60)
    
    if args.transport == "stdio":
        sys.stderr.write("[MCP SERVER] Starting MCP server with stdio transport...\n")
        sys.stderr.write("[MCP SERVER] Server ready, waiting for MCP protocol messages on stdin\n")
        sys.stderr.write("[MCP SERVER] Checking stdin/stdout/stderr availability...\n")
        sys.stderr.write(f"[MCP SERVER] stdin readable: {hasattr(sys.stdin, 'readable') and sys.stdin.readable()}\n")
        sys.stderr.write(f"[MCP SERVER] stdout writable: {hasattr(sys.stdout, 'writable') and sys.stdout.writable()}\n")
        sys.stderr.write(f"[MCP SERVER] stderr writable: {hasattr(sys.stderr, 'writable') and sys.stderr.writable()}\n")
        sys.stderr.write("[MCP SERVER] ============================================================\n")
        sys.stderr.flush()
        
        # Try to read a test line from stdin to see if it's available
        # But don't block - just check if there's data available
        try:
            import select
            if hasattr(select, 'select'):
                # Check if stdin has data available (non-blocking check)
                ready, _, _ = select.select([sys.stdin], [], [], 0)
                if ready:
                    sys.stderr.write("[MCP SERVER] stdin has data available\n")
                else:
                    sys.stderr.write("[MCP SERVER] stdin is empty, waiting for MCP protocol messages...\n")
            else:
                sys.stderr.write("[MCP SERVER] select module not available, cannot check stdin\n")
        except Exception as e:
            sys.stderr.write(f"[MCP SERVER] Error checking stdin: {e}\n")
        sys.stderr.flush()
        
        try:
            sys.stderr.write("[MCP SERVER] Calling mcp.run(transport='stdio')...\n")
            sys.stderr.flush()
            mcp.run(transport="stdio")
            sys.stderr.write("[MCP SERVER] mcp.run() returned (should not happen normally)\n")
            sys.stderr.flush()
        except KeyboardInterrupt:
            sys.stderr.write("[MCP SERVER] Received KeyboardInterrupt, shutting down gracefully\n")
            sys.stderr.flush()
            if debug_mode:
                debug_logger.debug("Received KeyboardInterrupt, shutting down gracefully")
            pass
        except Exception as e:
            # Log fatal errors to stderr
            error_msg = f"[MCP SERVER] Fatal error: {e}\n"
            sys.stderr.write(error_msg)
            import traceback
            traceback.print_exc(file=sys.stderr)
            sys.stderr.flush()
            if debug_mode:
                debug_logger.debug("Fatal error occurred", exc_info=True)
            sys.exit(1)
            
    elif args.transport == "sse":
        sys.stderr.write(f"[MCP SERVER] Starting MCP server with SSE transport on {args.host}:{args.port}...\n")
        sys.stderr.flush()
        
        try:
            mcp.run(transport="sse", host=args.host, port=args.port)
        except KeyboardInterrupt:
            sys.stderr.write("[MCP SERVER] Received KeyboardInterrupt, shutting down gracefully\n")
            sys.stderr.flush()
            pass
        except Exception as e:
            sys.stderr.write(f"[MCP SERVER] Fatal error: {e}\n")
            sys.stderr.flush()
            sys.exit(1)

