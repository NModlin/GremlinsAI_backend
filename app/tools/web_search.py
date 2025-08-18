# app/tools/web_search.py
"""
Production-ready web search tool using DuckDuckGo with enhanced features.

Features:
- Rate limiting and request throttling
- Result filtering and ranking
- Error handling and retries
- Structured output format
- Content summarization
"""

import time
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

try:
    from duckduckgo_search import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False

from .base_tool import tool_wrapper, ToolResult, validate_input, sanitize_string, truncate_output

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Individual search result structure."""
    title: str
    url: str
    snippet: str
    relevance_score: float = 0.0
    source_domain: str = ""


class SearchRateLimiter:
    """Simple rate limiter for search requests."""
    
    def __init__(self, max_requests: int = 10, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
    
    def can_make_request(self) -> bool:
        """Check if a request can be made within rate limits."""
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self.time_window)
        
        # Remove old requests
        self.requests = [req_time for req_time in self.requests if req_time > cutoff]
        
        return len(self.requests) < self.max_requests
    
    def record_request(self):
        """Record a new request."""
        self.requests.append(datetime.utcnow())
    
    def wait_time(self) -> float:
        """Get time to wait before next request is allowed."""
        if self.can_make_request():
            return 0.0
        
        oldest_request = min(self.requests)
        wait_until = oldest_request + timedelta(seconds=self.time_window)
        wait_seconds = (wait_until - datetime.utcnow()).total_seconds()
        
        return max(0.0, wait_seconds)


# Global rate limiter instance
_rate_limiter = SearchRateLimiter()


def extract_domain(url: str) -> str:
    """Extract domain from URL for source identification."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc.lower()
    except Exception:
        return "unknown"


def calculate_relevance_score(result: Dict[str, str], query: str) -> float:
    """
    Calculate relevance score for a search result.
    
    Args:
        result: Search result dictionary
        query: Original search query
        
    Returns:
        Relevance score between 0.0 and 1.0
    """
    try:
        query_lower = query.lower()
        title_lower = result.get('title', '').lower()
        snippet_lower = result.get('body', '').lower()
        
        score = 0.0
        
        # Title relevance (weighted higher)
        title_matches = sum(1 for word in query_lower.split() if word in title_lower)
        score += (title_matches / len(query_lower.split())) * 0.6
        
        # Snippet relevance
        snippet_matches = sum(1 for word in query_lower.split() if word in snippet_lower)
        score += (snippet_matches / len(query_lower.split())) * 0.4
        
        # Bonus for exact phrase matches
        if query_lower in title_lower:
            score += 0.2
        elif query_lower in snippet_lower:
            score += 0.1
        
        return min(1.0, score)
        
    except Exception as e:
        logger.warning(f"Error calculating relevance score: {e}")
        return 0.5  # Default score


def filter_and_rank_results(results: List[Dict], query: str, max_results: int = 10) -> List[SearchResult]:
    """
    Filter and rank search results by relevance.
    
    Args:
        results: Raw search results from DuckDuckGo
        query: Original search query
        max_results: Maximum number of results to return
        
    Returns:
        List of filtered and ranked SearchResult objects
    """
    processed_results = []
    seen_urls = set()
    
    for result in results:
        try:
            url = result.get('href', '')
            title = result.get('title', 'No title')
            snippet = result.get('body', 'No description')
            
            # Skip duplicates
            if url in seen_urls:
                continue
            seen_urls.add(url)
            
            # Skip invalid results
            if not url or not title:
                continue
            
            # Calculate relevance
            relevance = calculate_relevance_score(result, query)
            
            # Create structured result
            search_result = SearchResult(
                title=title[:200],  # Truncate long titles
                url=url,
                snippet=snippet[:500],  # Truncate long snippets
                relevance_score=relevance,
                source_domain=extract_domain(url)
            )
            
            processed_results.append(search_result)
            
        except Exception as e:
            logger.warning(f"Error processing search result: {e}")
            continue
    
    # Sort by relevance score (descending)
    processed_results.sort(key=lambda x: x.relevance_score, reverse=True)
    
    return processed_results[:max_results]


@tool_wrapper("web_search")
def web_search(query: str, max_results: int = 10, safe_search: bool = True) -> ToolResult:
    """
    Perform web search using DuckDuckGo with enhanced features.
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return (1-20)
        safe_search: Enable safe search filtering
        
    Returns:
        ToolResult with structured search results
        
    Examples:
        web_search("Python programming tutorial")
        web_search("weather in New York", max_results=5)
    """
    try:
        # Validate inputs
        query = validate_input(query, str, "query")
        query = sanitize_string(query, max_length=500)
        
        if not query:
            raise ValueError("Search query cannot be empty")
        
        max_results = validate_input(max_results, int, "max_results")
        if not 1 <= max_results <= 20:
            raise ValueError("max_results must be between 1 and 20")
        
        # Check if DuckDuckGo search is available
        if not DDGS_AVAILABLE:
            return ToolResult(
                success=False,
                result=None,
                error_message="DuckDuckGo search library not available. Install with: pip install duckduckgo-search"
            )
        
        # Check rate limiting
        if not _rate_limiter.can_make_request():
            wait_time = _rate_limiter.wait_time()
            return ToolResult(
                success=False,
                result=None,
                error_message=f"Rate limit exceeded. Please wait {wait_time:.1f} seconds before next search."
            )
        
        # Record the request
        _rate_limiter.record_request()
        
        logger.info(f"Performing web search for: {query}")
        
        # Perform the search
        with DDGS() as ddgs:
            # Get more results than needed for better filtering
            raw_results = list(ddgs.text(
                keywords=query,
                max_results=min(max_results * 2, 20),
                safesearch='moderate' if safe_search else 'off'
            ))
        
        if not raw_results:
            return ToolResult(
                success=True,
                result=[],
                metadata={
                    "query": query,
                    "total_results": 0,
                    "message": "No search results found"
                }
            )
        
        # Filter and rank results
        processed_results = filter_and_rank_results(raw_results, query, max_results)
        
        # Format results for output
        formatted_results = []
        for i, result in enumerate(processed_results, 1):
            formatted_results.append({
                "rank": i,
                "title": result.title,
                "url": result.url,
                "snippet": result.snippet,
                "relevance_score": round(result.relevance_score, 3),
                "source_domain": result.source_domain
            })
        
        # Create summary
        summary = f"Found {len(formatted_results)} relevant results for '{query}'"
        if processed_results:
            avg_relevance = sum(r.relevance_score for r in processed_results) / len(processed_results)
            summary += f" (average relevance: {avg_relevance:.2f})"
        
        return ToolResult(
            success=True,
            result=formatted_results,
            metadata={
                "query": query,
                "total_results": len(formatted_results),
                "summary": summary,
                "safe_search": safe_search,
                "max_results_requested": max_results,
                "search_timestamp": datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        error_msg = f"Web search failed for query '{query}': {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        return ToolResult(
            success=False,
            result=None,
            error_message=error_msg
        )


def get_search_help() -> str:
    """Get help text for the web search tool."""
    return """
Web Search Tool Help:

Usage:
- web_search("your search query")
- web_search("query", max_results=5, safe_search=True)

Parameters:
- query: Search terms (required)
- max_results: Number of results to return (1-20, default: 10)
- safe_search: Enable safe search filtering (default: True)

Features:
- Rate limiting to prevent abuse
- Result ranking by relevance
- Duplicate filtering
- Source domain identification
- Safe search filtering

Examples:
- web_search("Python programming tutorial")
- web_search("weather forecast London", max_results=5)
- web_search("machine learning algorithms", safe_search=False)

Note: This tool uses DuckDuckGo search and respects rate limits.
"""
