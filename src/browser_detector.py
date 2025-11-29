"""
Browser path detection for multiple browsers across different operating systems.
"""
import json
import os
import platform
import logging

logger = logging.getLogger(__name__)


def home():
    """Get user home directory."""
    return os.path.expanduser("~")


def get_os():
    """Detect operating system."""
    system = platform.system().lower()
    if "windows" in system:
        return "windows"
    if "darwin" in system:
        return "mac"
    if "linux" in system:
        return "linux"
    return "unknown"


def build_chromium_paths(base):
    """Build list of bookmark paths for Chromium-based browsers."""
    logger.debug(f"Checking Chromium base path: {base}")
    if not os.path.exists(base):
        logger.debug(f"Base path does not exist: {base}")
        return []

    profiles = ["Default", "Profile 1", "Profile 2", "Profile 3"]
    results = []
    for profile in profiles:
        path = os.path.join(base, profile, "Bookmarks")
        logger.debug(f"Checking bookmark path: {path}")
        if os.path.exists(path):
            logger.info(f"Found bookmark file: {path}")
            results.append(path)
        else:
            logger.debug(f"Bookmark file not found: {path}")
    return results


def chrome_paths():
    """Get Chrome bookmark paths."""
    osname = get_os()
    logger.debug(f"Detecting Chrome bookmark paths on {osname}")
    paths = []

    if osname == "windows":
        base = os.path.join(home(), "AppData", "Local", "Google", "Chrome", "User Data")
        logger.info(f"Chrome (Windows): Checking base path: {base}")
        paths = build_chromium_paths(base)
    elif osname == "mac":
        # macOS Chrome uses Default profile by default
        path = os.path.join(home(), "Library", "Application Support", "Google", "Chrome", "Default", "Bookmarks")
        logger.info(f"Chrome (macOS): Checking bookmark path: {path}")
        if os.path.exists(path):
            logger.info(f"Chrome (macOS): Found bookmark file: {path}")
            paths = [path]
        else:
            logger.debug(f"Chrome (macOS): Bookmark file not found: {path}")
    elif osname == "linux":
        base = os.path.join(home(), ".config", "google-chrome")
        logger.info(f"Chrome (Linux): Checking base path: {base}")
        paths = build_chromium_paths(base)

    logger.info(f"Chrome: Found {len(paths)} bookmark file(s)")
    return paths


def edge_paths():
    """Get Microsoft Edge bookmark paths."""
    osname = get_os()
    logger.debug(f"Detecting Edge bookmark paths on {osname}")
    base = None

    if osname == "windows":
        base = os.path.join(home(), "AppData", "Local", "Microsoft", "Edge", "User Data")
        logger.info(f"Edge (Windows): Checking base path: {base}")
    elif osname == "mac":
        base = os.path.join(home(), "Library", "Application Support", "Microsoft Edge")
        logger.info(f"Edge (macOS): Checking base path: {base}")
    elif osname == "linux":
        base = os.path.join(home(), ".config", "microsoft-edge")
        logger.info(f"Edge (Linux): Checking base path: {base}")
    else:
        logger.debug(f"Edge: Unsupported OS: {osname}")
        return []

    paths = build_chromium_paths(base)
    logger.info(f"Edge: Found {len(paths)} bookmark file(s)")
    return paths


def opera_paths():
    """Get Opera bookmark paths."""
    osname = get_os()
    logger.debug(f"Detecting Opera bookmark paths on {osname}")
    base = None

    if osname == "windows":
        base = os.path.join(home(), "AppData", "Roaming", "Opera Software", "Opera Stable")
        bookmark_file = os.path.join(base, "Bookmarks")
        logger.info(f"Opera (Windows): Checking bookmark path: {bookmark_file}")
        if os.path.exists(bookmark_file):
            logger.info(f"Opera (Windows): Found bookmark file: {bookmark_file}")
            return [bookmark_file]
        else:
            logger.debug(f"Opera (Windows): Bookmark file not found: {bookmark_file}")
            return []
    elif osname == "mac":
        base = os.path.join(home(), "Library", "Application Support", "com.operasoftware.Opera")
        logger.info(f"Opera (macOS): Checking base path: {base}")
    elif osname == "linux":
        base = os.path.join(home(), ".config", "opera")
        logger.info(f"Opera (Linux): Checking base path: {base}")
    else:
        logger.debug(f"Opera: Unsupported OS: {osname}")
        return []

    bookmark_file = os.path.join(base, "Bookmarks")
    logger.info(f"Opera ({osname}): Checking bookmark path: {bookmark_file}")
    if os.path.exists(bookmark_file):
        logger.info(f"Opera ({osname}): Found bookmark file: {bookmark_file}")
        return [bookmark_file]
    else:
        logger.debug(f"Opera ({osname}): Bookmark file not found: {bookmark_file}")
        return []


def firefox_paths():
    """Get Firefox bookmark paths (SQLite databases)."""
    osname = get_os()
    logger.debug(f"Detecting Firefox bookmark paths on {osname}")
    
    if osname == "windows":
        base = os.path.join(home(), "AppData", "Roaming", "Mozilla", "Firefox", "Profiles")
        logger.info(f"Firefox (Windows): Checking profiles directory: {base}")
    elif osname == "mac":
        base = os.path.join(home(), "Library", "Application Support", "Firefox", "Profiles")
        logger.info(f"Firefox (macOS): Checking profiles directory: {base}")
    elif osname == "linux":
        base = os.path.join(home(), ".mozilla", "firefox")
        logger.info(f"Firefox (Linux): Checking profiles directory: {base}")
    else:
        logger.debug(f"Firefox: Unsupported OS: {osname}")
        return []

    paths = []
    if os.path.exists(base):
        logger.debug(f"Firefox: Profiles directory exists, scanning for places.sqlite files")
        for folder in os.listdir(base):
            db = os.path.join(base, folder, "places.sqlite")
            logger.debug(f"Firefox: Checking database path: {db}")
            if os.path.exists(db):
                logger.info(f"Firefox: Found bookmark database: {db}")
                paths.append(db)
    else:
        logger.debug(f"Firefox: Profiles directory does not exist: {base}")
    
    logger.info(f"Firefox: Found {len(paths)} bookmark database(s)")
    return paths


# Safari support removed - reading Bookmarks.plist requires special macOS permissions
# def safari_paths():
#     """Get Safari bookmark paths (macOS only)."""
#     if get_os() != "mac":
#         return []
#     path = os.path.join(home(), "Library", "Safari", "Bookmarks.plist")
#     return [path] if os.path.exists(path) else []


def atlas_paths():
    """Get ChatGPT Atlas bookmark paths (macOS only, Chromium-based)."""
    osname = get_os()
    logger.debug(f"Detecting ChatGPT Atlas bookmark paths on {osname}")
    
    if osname != "mac":
        logger.debug(f"Atlas: Only supported on macOS, current OS: {osname}")
        return []

    candidates = [
        os.path.join(home(), "Library", "Application Support", "ChatGPT Atlas", "Default", "Bookmarks"),
        os.path.join(home(), "Library", "Application Support", "ChatGPT Atlas", "Profile 1", "Bookmarks"),
        os.path.join(home(), "Library", "Application Support", "Atlas", "Default", "Bookmarks"),
    ]

    paths = []
    for candidate in candidates:
        logger.info(f"Atlas (macOS): Checking bookmark path: {candidate}")
        if os.path.exists(candidate):
            logger.info(f"Atlas (macOS): Found bookmark file: {candidate}")
            paths.append(candidate)
        else:
            logger.debug(f"Atlas (macOS): Bookmark file not found: {candidate}")
    
    logger.info(f"Atlas: Found {len(paths)} bookmark file(s)")
    return paths


def comet_paths():
    """Get Perplexity Comet bookmark paths (Chromium-based)."""
    osname = get_os()
    logger.debug(f"Detecting Comet bookmark paths on {osname}")
    paths = []

    if osname == "windows":
        base = os.path.join(home(), "AppData", "Local", "Perplexity", "Comet", "User Data")
        logger.info(f"Comet (Windows): Checking base path: {base}")
        paths = build_chromium_paths(base)
    elif osname == "mac":
        # macOS Comet uses Default profile with singular "Bookmark" filename
        path = os.path.join(home(), "Library", "Application Support", "Comet", "Default", "Bookmark")
        logger.info(f"Comet (macOS): Checking bookmark path: {path}")
        if os.path.exists(path):
            logger.info(f"Comet (macOS): Found bookmark file: {path}")
            paths = [path]
        else:
            logger.debug(f"Comet (macOS): Bookmark file not found: {path}")
    elif osname == "linux":
        base = os.path.join(home(), ".config", "perplexity-comet")
        logger.info(f"Comet (Linux): Checking base path: {base}")
        paths = build_chromium_paths(base)

    logger.info(f"Comet: Found {len(paths)} bookmark file(s)")
    return paths


# Browser registry mapping browser names to their path detection functions
# Note: Safari support removed - reading Bookmarks.plist requires special macOS permissions
BROWSERS = {
    "Chrome": chrome_paths,
    "Edge": edge_paths,
    "Opera": opera_paths,
    "Firefox": firefox_paths,
    # "Safari": safari_paths,  # Removed - requires macOS permissions
    "ChatGPT Atlas": atlas_paths,
    "Perplexity Comet": comet_paths,
}


def get_available_browsers(custom_paths_config=None):
    """
    Get list of browsers with detected bookmark paths.
    
    Args:
        custom_paths_config: Optional dictionary mapping browser names to list of custom paths
                             e.g. {"Chrome": ["/path/to/bookmarks"]}
    """
    available = {}
    custom_paths_config = custom_paths_config or {}
    
    for browser_name, path_fn in BROWSERS.items():
        # Check for custom paths first
        if browser_name in custom_paths_config and custom_paths_config[browser_name]:
            paths = custom_paths_config[browser_name]
            logger.info(f"{browser_name}: Using custom paths from config: {paths}")
            available[browser_name] = paths
            continue
            
        # Fallback to auto-detection
        paths = path_fn()
        if paths:
            available[browser_name] = paths
    return available


def get_browser_paths(browser_name, custom_paths=None):
    """
    Get bookmark paths for a specific browser.
    
    Args:
        browser_name: Name of the browser
        custom_paths: Optional list of custom paths to use instead of auto-detection
    """
    if custom_paths:
        logger.info(f"{browser_name}: Using custom paths from config: {custom_paths}")
        return custom_paths
        
    if browser_name not in BROWSERS:
        return []
    return BROWSERS[browser_name]()

