"""
Metadata generation for bookmarks via HTML content extraction.
"""
import os
import time
import logging
import asyncio
from typing import Dict, Any, Optional, Tuple
import aiohttp
from bs4 import BeautifulSoup
import html2text
import trafilatura

logger = logging.getLogger(__name__)


def extract_metadata_from_html(html_content: str) -> str:
    """
    Extract summary/description from HTML metadata tags.
    Tries multiple sources in order of preference:
    1. Open Graph description (og:description)
    2. Meta description tag
    3. Twitter Card description
    4. First paragraph from main content
    5. Title tag as fallback
    
    Args:
        html_content: Raw HTML string
        
    Returns:
        Summary string extracted from HTML metadata
    """
    try:
        # Use lxml parser if available for speed, otherwise fallback to html.parser
        try:
            soup = BeautifulSoup(html_content, 'lxml')
        except Exception:
            soup = BeautifulSoup(html_content, 'html.parser')
        
        # Try Open Graph description first (most reliable)
        og_desc = soup.find('meta', property='og:description')
        if og_desc and og_desc.get('content'):
            desc = og_desc['content'].strip()
            if desc:
                return desc[:500]  # Limit length
        
        # Try meta description tag
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            desc = meta_desc['content'].strip()
            if desc:
                return desc[:500]
        
        # Try Twitter Card description
        twitter_desc = soup.find('meta', attrs={'name': 'twitter:description'})
        if twitter_desc and twitter_desc.get('content'):
            desc = twitter_desc['content'].strip()
            if desc:
                return desc[:500]
        
        # Try structured data (JSON-LD)
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_ld_scripts:
            try:
                import json
                data = json.loads(script.string)
                if isinstance(data, dict):
                    # Try common description fields
                    for key in ['description', 'about', 'abstract']:
                        if key in data and data[key]:
                            desc = str(data[key]).strip()
                            if desc:
                                return desc[:500]
                    # Try nested structures
                    if '@graph' in data:
                        for item in data['@graph']:
                            if isinstance(item, dict) and 'description' in item:
                                desc = str(item['description']).strip()
                                if desc:
                                    return desc[:500]
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
        
        # Extract first meaningful paragraph from main content
        # Try common content containers
        content_selectors = ['main', 'article', '[role="main"]', '.content', '#content', 'body']
        for selector in content_selectors:
            content = soup.select_one(selector)
            if content:
                # Get first paragraph
                paragraphs = content.find_all('p')
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    if len(text) > 50:  # Meaningful length
                        return text[:500]
        
        # Fallback to title tag
        title = soup.find('title')
        if title:
            title_text = title.get_text(strip=True)
            if title_text:
                return title_text[:200]
        
        return ""
    except Exception as e:
        logger.error(f"Error extracting metadata from HTML: {e}")
        return ""


def extract_text_from_html(html_content: str) -> str:
    """
    Extract clean text from HTML content.
    Uses trafilatura for main content extraction, falling back to html2text.
    
    Args:
        html_content: Raw HTML string
        
    Returns:
        Clean text extracted from HTML
    """
    try:
        # Try trafilatura first (better for main content extraction)
        text = trafilatura.extract(html_content, include_comments=False, include_tables=True)
        
        if text:
            # Limit text length to avoid token limits (keep first 5000 chars)
            if len(text) > 5000:
                text = text[:5000] + "..."
            return text
            
        # Fallback to html2text if trafilatura fails to extract content
        logger.debug("Trafilatura returned no content, falling back to html2text")
        
        # Parse HTML with BeautifulSoup
        try:
            soup = BeautifulSoup(html_content, 'lxml')
        except Exception:
            soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "meta", "link"]):
            script.decompose()
        
        # Use html2text for clean text extraction
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = True
        h.body_width = 0  # Don't wrap text
        h.unicode_snob = True
        
        text = h.handle(str(soup))
        
        # Clean up excessive whitespace
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        text = '\n'.join(lines)
        
        # Limit text length to avoid token limits (keep first 5000 chars)
        if len(text) > 5000:
            text = text[:5000] + "..."
        
        return text
    except Exception as e:
        logger.error(f"Error extracting text from HTML: {e}")
        return ""


async def fetch_html_content(url: str, max_retries: int = 3) -> Tuple[Optional[str], Optional[str]]:
    """
    Fetch HTML content from a URL using aiohttp.
    
    Args:
        url: URL to fetch
        max_retries: Maximum number of retry attempts
        
    Returns:
        Tuple of (html_content, error_reason)
        - html_content: HTML string or None on failure
        - error_reason: Empty string if successful, otherwise reason for failure
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    timeout = aiohttp.ClientTimeout(total=10)
    
    for attempt in range(max_retries):
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers, allow_redirects=True) as response:
                    # Check for authentication/access errors
                    if response.status == 401 or response.status == 403:
                        reason = "Authentication required or access denied"
                        return None, reason
                    
                    # Check for not found errors
                    if response.status == 404:
                        reason = "URL not found"
                        return None, reason
                    
                    if response.status >= 400:
                        reason = f"HTTP {response.status} error"
                        if attempt < max_retries - 1:
                            await asyncio.sleep(1)
                            continue
                        return None, reason
                    
                    # Check content type
                    content_type = response.headers.get('content-type', '').lower()
                    if 'text/html' not in content_type:
                        reason = f"Not HTML content: {content_type}"
                        return None, reason
                    
                    html_content = await response.text()
                    return html_content, ""
            
        except asyncio.TimeoutError:
            if attempt < max_retries - 1:
                logger.warning(f"Timeout fetching {url}, retrying...")
                await asyncio.sleep(1)
                continue
            return None, "Request timeout"
            
        except aiohttp.ClientSSLError:
            reason = "SSL certificate error"
            return None, reason
            
        except aiohttp.ClientConnectionError:
            if attempt < max_retries - 1:
                logger.warning(f"Connection error for {url}, retrying...")
                await asyncio.sleep(1)
                continue
            return None, "Connection error"
            
        except Exception as e:
            error_msg = str(e).lower()
            if attempt < max_retries - 1:
                logger.warning(f"Error fetching {url} (attempt {attempt + 1}/{max_retries}): {e}")
                await asyncio.sleep(1)
                continue
            return None, f"Error: {str(e)[:100]}"
    
    return None, "Failed to fetch HTML content"


async def fetch_url_content(url: str, max_retries: int = 2, retry_delay: float = 1.0) -> tuple[str, str, str]:
    """
    Fetch HTML content from a URL and extract text.
    
    Args:
        url: URL to fetch
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
        
    Returns:
        Tuple of (html_text, description, error_reason)
        - html_text: Extracted text from HTML content
        - description: Description extracted from HTML metadata (og:description, meta description, etc.)
        - error_reason: Empty string if successful, otherwise reason for failure
    """
    for attempt in range(max_retries):
        try:
            # Fetch HTML content
            html_content, fetch_error = await fetch_html_content(url, max_retries=2)
            
            if html_content is None:
                # Return the fetch error reason
                return "", "", fetch_error
            
            # Extract text from HTML
            html_text = extract_text_from_html(html_content)
            
            # Extract description from HTML metadata
            description = extract_metadata_from_html(html_content)
            
            if html_text or description:
                logger.debug(f"Successfully fetched content for {url}")
                return html_text, description, ""
            else:
                # No content extracted
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))
                    continue
                else:
                    return "", "", "No content extracted from HTML"
            
        except Exception as e:
            error_msg = str(e).lower()
            
            if attempt < max_retries - 1:
                wait_time = retry_delay * (attempt + 1)
                logger.warning(f"Error fetching content for {url} (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
                continue
            else:
                reason = f"Failed after {max_retries} attempts: {str(e)[:100]}"
                logger.error(f"Error fetching content for {url} after {max_retries} attempts: {e}")
                return "", "", reason
    
    return "", "", "Failed to fetch content"


async def generate_metadata(bookmark: Dict[str, Any], include_content: bool = True) -> tuple[Dict[str, Any], str]:
    """
    Generate complete metadata for a bookmark including HTML content.
    
    Args:
        bookmark: Bookmark dictionary with url, name, folder, browser
        include_content: Whether to fetch HTML content (may be slow)
        
    Returns:
        Tuple of (metadata_dict, error_reason)
        - metadata_dict: Complete metadata dictionary with content and description fields
        - error_reason: Empty string if successful, otherwise reason for skipping
    """
    metadata = {
        "url": bookmark.get("url", ""),
        "name": bookmark.get("name", ""),
        "folder": bookmark.get("folder", ""),
        "browser": bookmark.get("browser", ""),
        "description": bookmark.get("description", ""),  # May be empty
        "content": bookmark.get("content", ""),  # HTML text content
        "timestamp": bookmark.get("timestamp", time.time())
    }
    
    error_reason = ""
    
    # Fetch content if requested and URL is available
    if include_content and metadata["url"]:
        try:
            html_text, description, error_reason = await fetch_url_content(metadata["url"],max_retries=2, retry_delay=1.0)
            if html_text:
                metadata["content"] = html_text
            if description:
                metadata["description"] = description
            if error_reason:
                logger.warning(f"Could not fetch content for {metadata['url']}: {error_reason}")
        except Exception as e:
            error_reason = f"Exception: {str(e)[:100]}"
            logger.error(f"Error fetching content for {metadata['url']}: {e}")
            metadata["content"] = ""
            metadata["description"] = ""
    
    return metadata, error_reason


async def generate_metadata_batch(bookmarks: list[Dict[str, Any]], include_content: bool = True, progress_logger=None, concurrency: int = 10) -> tuple[list[Dict[str, Any]], list[Dict[str, str]]]:
    """
    Generate metadata for multiple bookmarks concurrently.
    
    Args:
        bookmarks: List of bookmark dictionaries
        include_content: Whether to fetch HTML content
        progress_logger: Optional logger for progress updates
        concurrency: Maximum number of concurrent requests
        
    Returns:
        Tuple of (results_list, skipped_list)
        - results_list: List of successfully processed metadata dictionaries
        - skipped_list: List of skipped bookmarks with reasons [{"url": str, "name": str, "reason": str}]
    """
    results = []
    skipped = []
    total = len(bookmarks)
    
    if progress_logger:
        progress_logger.info(f"   Generating metadata for {total} bookmarks (content: {include_content}, concurrency: {concurrency})")
    
    semaphore = asyncio.Semaphore(concurrency)
    processed_count = 0
    
    async def process_bookmark(idx: int, bookmark: Dict[str, Any]):
        nonlocal processed_count
        url = bookmark.get("url", "")
        name = bookmark.get("name", "")[:50]
        
        async with semaphore:
            try:
                if progress_logger:
                    # Only log start for every 10th to avoid spamming
                    if idx % 10 == 0:
                        progress_logger.info(f"   [{idx}/{total}] Processing batch...")
                
                metadata, error_reason = await generate_metadata(bookmark, include_content=include_content)
                
                # Check if this bookmark should be skipped (or logged as error but stored)
                if error_reason and ("authentication" in error_reason.lower() or "access denied" in error_reason.lower() or "not found" in error_reason.lower()):
                    # Return BOTH metadata (for storage) AND skip_info (for error logging)
                    return metadata, {
                        "url": url,
                        "name": bookmark.get("name", ""),
                        "reason": error_reason
                    }
                else:
                    return metadata, None
                    
            except Exception as e:
                error_msg = str(e)[:100]
                logger.error(f"Error processing bookmark {idx}/{total}: {e}")
                return None, {
                    "url": url,
                    "name": bookmark.get("name", ""),
                    "reason": f"Exception: {error_msg}"
                }
            finally:
                processed_count += 1
                if progress_logger and processed_count % 10 == 0:
                    progress_logger.info(f"   Progress: {processed_count}/{total} bookmarks processed")

    # Create tasks
    tasks = [process_bookmark(i, bm) for i, bm in enumerate(bookmarks, 1)]
    
    # Run tasks concurrently
    batch_results = await asyncio.gather(*tasks)
    
    # Process results
    for metadata, skip_info in batch_results:
        if metadata:
            results.append(metadata)
        if skip_info:
            skipped.append(skip_info)
    
    if progress_logger:
        progress_logger.info(f"   ✅ Completed metadata generation: {len(results)}/{total} bookmarks processed, {len(skipped)} skipped")
    
    return results, skipped

