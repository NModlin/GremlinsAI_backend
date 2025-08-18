# app/tools/base_tool.py
"""
Base tool functionality and common utilities for the GremlinsAI tool ecosystem.
"""

import logging
import time
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass
from datetime import datetime
from functools import wraps

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Standardized result format for all tools."""
    success: bool
    result: Any
    error_message: Optional[str] = None
    execution_time: float = 0.0
    tool_name: str = ""
    timestamp: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.timestamp == "":
            self.timestamp = datetime.utcnow().isoformat()
        if self.metadata is None:
            self.metadata = {}


def tool_wrapper(tool_name: str):
    """
    Decorator to wrap tool functions with common functionality:
    - Execution time tracking
    - Error handling
    - Logging
    - Result standardization
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                logger.info(f"Executing tool: {tool_name}")
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # If function returns ToolResult, update it
                if isinstance(result, ToolResult):
                    result.execution_time = execution_time
                    result.tool_name = tool_name
                    logger.info(f"Tool {tool_name} completed successfully in {execution_time:.3f}s")
                    return result
                
                # Otherwise, wrap result in ToolResult
                tool_result = ToolResult(
                    success=True,
                    result=result,
                    execution_time=execution_time,
                    tool_name=tool_name
                )
                logger.info(f"Tool {tool_name} completed successfully in {execution_time:.3f}s")
                return tool_result
                
            except Exception as e:
                execution_time = time.time() - start_time
                error_msg = f"Tool {tool_name} failed: {str(e)}"
                logger.error(error_msg, exc_info=True)
                
                return ToolResult(
                    success=False,
                    result=None,
                    error_message=error_msg,
                    execution_time=execution_time,
                    tool_name=tool_name
                )
        
        return wrapper
    return decorator


def validate_input(value: Any, expected_type: type, param_name: str, allow_none: bool = False) -> Any:
    """
    Validate input parameter type and value.
    
    Args:
        value: The value to validate
        expected_type: Expected type
        param_name: Parameter name for error messages
        allow_none: Whether None values are allowed
        
    Returns:
        The validated value
        
    Raises:
        ValueError: If validation fails
    """
    if value is None:
        if allow_none:
            return value
        else:
            raise ValueError(f"Parameter '{param_name}' cannot be None")
    
    if not isinstance(value, expected_type):
        raise ValueError(f"Parameter '{param_name}' must be of type {expected_type.__name__}, got {type(value).__name__}")
    
    return value


def sanitize_string(value: str, max_length: int = 10000, allow_empty: bool = False) -> str:
    """
    Sanitize string input for security and length.
    
    Args:
        value: String to sanitize
        max_length: Maximum allowed length
        allow_empty: Whether empty strings are allowed
        
    Returns:
        Sanitized string
        
    Raises:
        ValueError: If validation fails
    """
    if not isinstance(value, str):
        raise ValueError(f"Expected string, got {type(value).__name__}")
    
    if not allow_empty and len(value.strip()) == 0:
        raise ValueError("String cannot be empty")
    
    if len(value) > max_length:
        raise ValueError(f"String too long: {len(value)} > {max_length}")
    
    # Remove potentially dangerous characters
    sanitized = value.strip()
    
    # Log if sanitization changed the input
    if sanitized != value:
        logger.debug(f"String sanitized: '{value}' -> '{sanitized}'")
    
    return sanitized


def format_error_message(tool_name: str, error: Exception, context: str = "") -> str:
    """Format a standardized error message for tools."""
    base_msg = f"Tool '{tool_name}' error"
    if context:
        base_msg += f" in {context}"
    base_msg += f": {str(error)}"
    
    # Add error type for debugging
    error_type = type(error).__name__
    if error_type != "Exception":
        base_msg += f" ({error_type})"
    
    return base_msg


def safe_json_loads(json_str: str) -> Union[Dict, list, str, int, float, bool, None]:
    """
    Safely parse JSON string with error handling.
    
    Args:
        json_str: JSON string to parse
        
    Returns:
        Parsed JSON object or None if parsing fails
    """
    try:
        import json
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(f"Failed to parse JSON: {e}")
        return None


def truncate_output(output: str, max_length: int = 5000) -> str:
    """
    Truncate output to prevent excessive response sizes.
    
    Args:
        output: Output string to truncate
        max_length: Maximum allowed length
        
    Returns:
        Truncated string with indicator if truncated
    """
    if len(output) <= max_length:
        return output
    
    truncated = output[:max_length - 50]  # Leave room for truncation message
    truncated += f"\n... [Output truncated - showing first {max_length - 50} characters of {len(output)} total]"
    
    return truncated
