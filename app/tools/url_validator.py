# app/tools/url_validator.py
"""
URL validation and parsing tool.
"""

import re
import logging
from urllib.parse import urlparse, parse_qs, unquote
from typing import Dict, Any
from .base_tool import tool_wrapper, ToolResult, validate_input, sanitize_string

logger = logging.getLogger(__name__)


@tool_wrapper("url_validator")
def validate_url(url: str, operation: str = "validate") -> ToolResult:
    """
    Validate and parse URLs with various operations.
    
    Args:
        url: URL to validate/parse
        operation: Operation to perform (validate, parse, extract_domain, extract_params)
        
    Available Operations:
    - 'validate': Check if URL is valid
    - 'parse': Parse URL into components
    - 'extract_domain': Extract domain from URL
    - 'extract_params': Extract query parameters
    - 'normalize': Normalize URL format
    
    Returns:
        ToolResult with URL validation/parsing results
        
    Examples:
        validate_url("https://example.com/path?param=value", "validate")
        validate_url("https://example.com/path?param=value", "parse")
    """
    try:
        url = validate_input(url, str, "url")
        operation = validate_input(operation, str, "operation")
        
        url = sanitize_string(url, max_length=2000)
        operation = operation.lower().strip()
        
        logger.info(f"URL operation: {operation} on {url}")
        
        if operation == 'validate':
            # Basic URL validation
            url_pattern = re.compile(
                r'^https?://'  # http:// or https://
                r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
                r'localhost|'  # localhost...
                r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
                r'(?::\d+)?'  # optional port
                r'(?:/?|[/?]\S+)$', re.IGNORECASE)
            
            is_valid = bool(url_pattern.match(url))
            
            # Additional checks
            try:
                parsed = urlparse(url)
                has_scheme = bool(parsed.scheme)
                has_netloc = bool(parsed.netloc)
                scheme_valid = parsed.scheme in ['http', 'https']
            except Exception:
                has_scheme = has_netloc = scheme_valid = False
            
            result = {
                "is_valid": is_valid and has_scheme and has_netloc and scheme_valid,
                "has_scheme": has_scheme,
                "has_domain": has_netloc,
                "scheme_valid": scheme_valid,
                "url": url
            }
        
        elif operation == 'parse':
            try:
                parsed = urlparse(url)
                
                result = {
                    "url": url,
                    "scheme": parsed.scheme,
                    "netloc": parsed.netloc,
                    "hostname": parsed.hostname,
                    "port": parsed.port,
                    "path": parsed.path,
                    "params": parsed.params,
                    "query": parsed.query,
                    "fragment": parsed.fragment,
                    "username": parsed.username,
                    "password": "***" if parsed.password else None,
                    "query_params": dict(parse_qs(parsed.query)) if parsed.query else {}
                }
            except Exception as e:
                return ToolResult(
                    success=False,
                    result=None,
                    error_message=f"Failed to parse URL: {str(e)}"
                )
        
        elif operation == 'extract_domain':
            try:
                parsed = urlparse(url)
                domain = parsed.netloc
                
                # Remove port if present
                if ':' in domain:
                    domain = domain.split(':')[0]
                
                # Extract subdomain, domain, TLD
                parts = domain.split('.')
                if len(parts) >= 2:
                    tld = parts[-1]
                    domain_name = parts[-2]
                    subdomain = '.'.join(parts[:-2]) if len(parts) > 2 else None
                else:
                    tld = domain_name = subdomain = None
                
                result = {
                    "full_domain": parsed.netloc,
                    "domain": domain,
                    "domain_name": domain_name,
                    "tld": tld,
                    "subdomain": subdomain,
                    "port": parsed.port
                }
            except Exception as e:
                return ToolResult(
                    success=False,
                    result=None,
                    error_message=f"Failed to extract domain: {str(e)}"
                )
        
        elif operation == 'extract_params':
            try:
                parsed = urlparse(url)
                query_params = parse_qs(parsed.query, keep_blank_values=True)
                
                # Flatten single-value lists
                flattened_params = {}
                for key, values in query_params.items():
                    if len(values) == 1:
                        flattened_params[key] = values[0]
                    else:
                        flattened_params[key] = values
                
                result = {
                    "query_string": parsed.query,
                    "parameters": flattened_params,
                    "parameter_count": len(flattened_params),
                    "has_parameters": bool(flattened_params)
                }
            except Exception as e:
                return ToolResult(
                    success=False,
                    result=None,
                    error_message=f"Failed to extract parameters: {str(e)}"
                )
        
        elif operation == 'normalize':
            try:
                parsed = urlparse(url)
                
                # Normalize components
                scheme = parsed.scheme.lower()
                netloc = parsed.netloc.lower()
                path = parsed.path or '/'
                
                # Remove default ports
                if ':80' in netloc and scheme == 'http':
                    netloc = netloc.replace(':80', '')
                elif ':443' in netloc and scheme == 'https':
                    netloc = netloc.replace(':443', '')
                
                # Decode URL encoding in path
                path = unquote(path)
                
                # Reconstruct URL
                normalized_url = f"{scheme}://{netloc}{path}"
                if parsed.query:
                    normalized_url += f"?{parsed.query}"
                if parsed.fragment:
                    normalized_url += f"#{parsed.fragment}"
                
                result = {
                    "original_url": url,
                    "normalized_url": normalized_url,
                    "changes_made": url != normalized_url
                }
            except Exception as e:
                return ToolResult(
                    success=False,
                    result=None,
                    error_message=f"Failed to normalize URL: {str(e)}"
                )
        
        else:
            available_ops = ['validate', 'parse', 'extract_domain', 'extract_params', 'normalize']
            return ToolResult(
                success=False,
                result=None,
                error_message=f"Unknown operation '{operation}'. Available operations: {', '.join(available_ops)}"
            )
        
        return ToolResult(
            success=True,
            result=result,
            metadata={
                "operation": operation,
                "url_length": len(url)
            }
        )
        
    except Exception as e:
        error_msg = f"URL operation '{operation}' failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        return ToolResult(
            success=False,
            result=None,
            error_message=error_msg
        )


def get_url_validator_help() -> str:
    """Get help text for the URL validator tool."""
    return """
URL Validator Tool Help:

Usage:
- validate_url("url", "operation")

Available Operations:

Validation:
- 'validate': Check if URL is valid and well-formed

Parsing:
- 'parse': Parse URL into all components
- 'extract_domain': Extract domain information
- 'extract_params': Extract query parameters
- 'normalize': Normalize URL format

Examples:
- validate_url("https://example.com/path?param=value", "validate")
- validate_url("https://sub.example.com:8080/path", "parse")
- validate_url("https://example.com/search?q=test&page=1", "extract_params")
- validate_url("https://example.com", "extract_domain")

Validation Checks:
- Valid scheme (http/https)
- Valid domain format
- Proper URL structure
- Port validation

Parse Components:
- scheme, netloc, hostname, port
- path, params, query, fragment
- username (password hidden for security)
- query parameters as dictionary

Domain Extraction:
- Full domain with port
- Domain without port
- Subdomain, domain name, TLD
- Port information

Note: This tool focuses on HTTP/HTTPS URLs for security reasons.
"""
