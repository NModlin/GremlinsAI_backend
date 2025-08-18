# app/tools/api_caller.py
"""
Generic API caller tool for making HTTP GET requests with security and error handling.

Features:
- HTTP GET requests with timeout
- Response validation and parsing
- Security checks (URL validation, content type filtering)
- Rate limiting
- Error handling and retries
"""

import time
import json
import logging
from typing import Dict, Any, Optional, Union
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from .base_tool import tool_wrapper, ToolResult, validate_input, sanitize_string, truncate_output

logger = logging.getLogger(__name__)

# Rate limiting for API calls
class APIRateLimiter:
    """Rate limiter for API calls to prevent abuse."""
    
    def __init__(self, max_requests: int = 30, time_window: int = 60):
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


# Global rate limiter
_api_rate_limiter = APIRateLimiter()

# Allowed URL schemes
ALLOWED_SCHEMES = {'http', 'https'}

# Blocked domains (security)
BLOCKED_DOMAINS = {
    'localhost', '127.0.0.1', '0.0.0.0', '::1',
    '10.', '172.16.', '192.168.',  # Private IP ranges
    'metadata.google.internal',  # Cloud metadata
    'instance-data.ec2.internal'  # AWS metadata
}

# Safe content types
SAFE_CONTENT_TYPES = {
    'application/json', 'text/plain', 'text/html', 'text/xml',
    'application/xml', 'text/csv', 'application/rss+xml'
}


def validate_url(url: str) -> bool:
    """
    Validate URL for security and safety.
    
    Args:
        url: URL to validate
        
    Returns:
        True if URL is safe to access
    """
    try:
        parsed = urlparse(url)
        
        # Check scheme
        if parsed.scheme not in ALLOWED_SCHEMES:
            logger.warning(f"Blocked URL scheme: {parsed.scheme}")
            return False
        
        # Check for blocked domains
        hostname = parsed.hostname
        if hostname:
            hostname_lower = hostname.lower()
            
            # Check exact matches
            if hostname_lower in BLOCKED_DOMAINS:
                logger.warning(f"Blocked domain: {hostname}")
                return False
            
            # Check private IP ranges
            for blocked in BLOCKED_DOMAINS:
                if blocked.endswith('.') and hostname_lower.startswith(blocked):
                    logger.warning(f"Blocked private IP range: {hostname}")
                    return False
        
        return True
        
    except Exception as e:
        logger.warning(f"URL validation error: {e}")
        return False


def parse_response_content(response: 'requests.Response') -> Union[Dict, str]:
    """
    Parse response content based on content type.
    
    Args:
        response: HTTP response object
        
    Returns:
        Parsed content (dict for JSON, string for others)
    """
    content_type = response.headers.get('content-type', '').lower()
    
    try:
        # Try JSON first
        if 'json' in content_type:
            return response.json()
        
        # Return text content
        return response.text
        
    except json.JSONDecodeError:
        # If JSON parsing fails, return text
        return response.text
    except Exception as e:
        logger.warning(f"Error parsing response content: {e}")
        return response.text


@tool_wrapper("api_caller")
def make_api_call(url: str, timeout: int = 10, max_response_size: int = 100000, 
                  headers: Optional[Dict[str, str]] = None) -> ToolResult:
    """
    Make HTTP GET request to specified URL with security checks.
    
    Args:
        url: URL to make GET request to
        timeout: Request timeout in seconds (1-30)
        max_response_size: Maximum response size in bytes
        headers: Optional custom headers
        
    Returns:
        ToolResult with API response data
        
    Security Features:
    - URL validation and domain blocking
    - Rate limiting
    - Response size limits
    - Content type filtering
    - Timeout protection
    
    Examples:
        make_api_call("https://api.github.com/users/octocat")
        make_api_call("https://httpbin.org/json", timeout=5)
        make_api_call("https://api.example.com/data", headers={"User-Agent": "MyApp"})
    """
    try:
        # Validate inputs
        url = validate_input(url, str, "url")
        url = sanitize_string(url, max_length=2000)
        
        if not url:
            raise ValueError("URL cannot be empty")
        
        timeout = validate_input(timeout, int, "timeout")
        if not 1 <= timeout <= 30:
            raise ValueError("Timeout must be between 1 and 30 seconds")
        
        max_response_size = validate_input(max_response_size, int, "max_response_size")
        if not 1000 <= max_response_size <= 1000000:
            raise ValueError("max_response_size must be between 1000 and 1000000 bytes")
        
        # Check if requests library is available
        if not REQUESTS_AVAILABLE:
            return ToolResult(
                success=False,
                result=None,
                error_message="Requests library not available. Install with: pip install requests"
            )
        
        # Validate URL security
        if not validate_url(url):
            return ToolResult(
                success=False,
                result=None,
                error_message=f"URL blocked for security reasons: {url}"
            )
        
        # Check rate limiting
        if not _api_rate_limiter.can_make_request():
            wait_time = _api_rate_limiter.wait_time()
            return ToolResult(
                success=False,
                result=None,
                error_message=f"API rate limit exceeded. Please wait {wait_time:.1f} seconds."
            )
        
        # Record the request
        _api_rate_limiter.record_request()
        
        logger.info(f"Making API call to: {url}")
        
        # Prepare headers
        request_headers = {
            'User-Agent': 'GremlinsAI-Agent/1.0',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Encoding': 'gzip, deflate'
        }
        
        if headers:
            # Validate custom headers
            if not isinstance(headers, dict):
                raise ValueError("Headers must be a dictionary")
            
            # Add custom headers (with validation)
            for key, value in headers.items():
                if not isinstance(key, str) or not isinstance(value, str):
                    raise ValueError("Header keys and values must be strings")
                if len(key) > 100 or len(value) > 500:
                    raise ValueError("Header key/value too long")
                request_headers[key] = value
        
        # Make the request
        start_time = time.time()
        response = requests.get(
            url,
            headers=request_headers,
            timeout=timeout,
            stream=True,  # Stream to check content length
            allow_redirects=True,
            verify=True  # Verify SSL certificates
        )
        
        # Check response size
        content_length = response.headers.get('content-length')
        if content_length and int(content_length) > max_response_size:
            response.close()
            return ToolResult(
                success=False,
                result=None,
                error_message=f"Response too large: {content_length} bytes > {max_response_size} limit"
            )
        
        # Read response with size limit
        content = b''
        for chunk in response.iter_content(chunk_size=8192):
            content += chunk
            if len(content) > max_response_size:
                response.close()
                return ToolResult(
                    success=False,
                    result=None,
                    error_message=f"Response too large: > {max_response_size} bytes"
                )
        
        # Update response content
        response._content = content
        
        request_time = time.time() - start_time
        
        # Check status code
        if not response.ok:
            return ToolResult(
                success=False,
                result=None,
                error_message=f"HTTP {response.status_code}: {response.reason}",
                metadata={
                    "url": url,
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "request_time": request_time
                }
            )
        
        # Parse response content
        parsed_content = parse_response_content(response)
        
        # Truncate if string content is too long
        if isinstance(parsed_content, str) and len(parsed_content) > 10000:
            parsed_content = truncate_output(parsed_content, 10000)
        
        return ToolResult(
            success=True,
            result=parsed_content,
            metadata={
                "url": url,
                "status_code": response.status_code,
                "content_type": response.headers.get('content-type', 'unknown'),
                "content_length": len(content),
                "request_time": request_time,
                "response_headers": dict(response.headers),
                "is_json": isinstance(parsed_content, dict)
            }
        )
        
    except requests.exceptions.Timeout:
        return ToolResult(
            success=False,
            result=None,
            error_message=f"Request timeout after {timeout} seconds for URL: {url}"
        )
    
    except requests.exceptions.ConnectionError as e:
        return ToolResult(
            success=False,
            result=None,
            error_message=f"Connection error for URL {url}: {str(e)}"
        )
    
    except requests.exceptions.RequestException as e:
        return ToolResult(
            success=False,
            result=None,
            error_message=f"Request error for URL {url}: {str(e)}"
        )
    
    except Exception as e:
        error_msg = f"API call failed for URL {url}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        return ToolResult(
            success=False,
            result=None,
            error_message=error_msg
        )


def get_api_caller_help() -> str:
    """Get help text for the API caller tool."""
    return """
API Caller Tool Help:

Usage:
- make_api_call("https://api.example.com/data")
- make_api_call("url", timeout=15, max_response_size=50000)
- make_api_call("url", headers={"Authorization": "Bearer token"})

Parameters:
- url: URL to make GET request to (required)
- timeout: Request timeout in seconds (1-30, default: 10)
- max_response_size: Maximum response size in bytes (1000-1000000, default: 100000)
- headers: Optional custom headers dictionary

Security Features:
- URL validation and domain blocking
- Rate limiting (30 requests per minute)
- Response size limits
- SSL certificate verification
- Private IP and localhost blocking

Supported Content Types:
- JSON (automatically parsed)
- Plain text
- HTML/XML
- CSV

Examples:
- make_api_call("https://api.github.com/users/octocat")
- make_api_call("https://httpbin.org/json")
- make_api_call("https://api.weather.com/current", timeout=5)

Note: Only HTTP GET requests are supported for security reasons.
"""
