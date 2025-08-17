# app/tools/json_processor.py
"""
JSON processing tool for parsing, validating, and manipulating JSON data.
"""

import json
import logging
from typing import Dict, Any, Union, List
from .base_tool import tool_wrapper, ToolResult, validate_input

logger = logging.getLogger(__name__)


@tool_wrapper("json_processor")
def process_json(operation: str, data: Union[str, Dict, List] = None, **kwargs) -> ToolResult:
    """
    Process JSON data with various operations.
    
    Args:
        operation: Operation to perform
        data: JSON data (string or object)
        **kwargs: Additional parameters
        
    Available Operations:
    - 'parse': Parse JSON string to object
    - 'stringify': Convert object to JSON string
    - 'validate': Validate JSON syntax
    - 'pretty': Pretty-print JSON with indentation
    - 'minify': Minify JSON (remove whitespace)
    - 'extract': Extract value by key path (path="key.subkey")
    - 'keys': Get all keys from JSON object
    - 'values': Get all values from JSON object
    - 'size': Get size/length of JSON data
    
    Returns:
        ToolResult with processed JSON data
        
    Examples:
        process_json("parse", '{"name": "John", "age": 30}')
        process_json("stringify", {"name": "John", "age": 30})
        process_json("extract", {"user": {"name": "John"}}, path="user.name")
    """
    try:
        operation = validate_input(operation, str, "operation")
        operation = operation.lower().strip()
        
        logger.info(f"Processing JSON with operation: {operation}")
        
        if operation == 'parse':
            if not isinstance(data, str):
                raise ValueError("Data must be a JSON string for parse operation")
            
            try:
                result = json.loads(data)
                return ToolResult(
                    success=True,
                    result=result,
                    metadata={
                        "operation": operation,
                        "input_type": "string",
                        "output_type": type(result).__name__,
                        "input_length": len(data)
                    }
                )
            except json.JSONDecodeError as e:
                return ToolResult(
                    success=False,
                    result=None,
                    error_message=f"Invalid JSON: {str(e)}"
                )
        
        elif operation == 'stringify':
            if data is None:
                raise ValueError("Data parameter required for stringify operation")
            
            indent = kwargs.get('indent', None)
            ensure_ascii = kwargs.get('ensure_ascii', False)
            
            result = json.dumps(data, indent=indent, ensure_ascii=ensure_ascii)
            
        elif operation == 'validate':
            if not isinstance(data, str):
                raise ValueError("Data must be a JSON string for validate operation")
            
            try:
                json.loads(data)
                result = {"valid": True, "message": "JSON is valid"}
            except json.JSONDecodeError as e:
                result = {"valid": False, "error": str(e)}
        
        elif operation == 'pretty':
            if isinstance(data, str):
                try:
                    parsed_data = json.loads(data)
                except json.JSONDecodeError as e:
                    return ToolResult(
                        success=False,
                        result=None,
                        error_message=f"Invalid JSON for pretty printing: {str(e)}"
                    )
            else:
                parsed_data = data
            
            indent = kwargs.get('indent', 2)
            result = json.dumps(parsed_data, indent=indent, ensure_ascii=False)
        
        elif operation == 'minify':
            if isinstance(data, str):
                try:
                    parsed_data = json.loads(data)
                except json.JSONDecodeError as e:
                    return ToolResult(
                        success=False,
                        result=None,
                        error_message=f"Invalid JSON for minification: {str(e)}"
                    )
            else:
                parsed_data = data
            
            result = json.dumps(parsed_data, separators=(',', ':'))
        
        elif operation == 'extract':
            path = kwargs.get('path')
            if not path:
                raise ValueError("Path parameter required for extract operation")
            
            if isinstance(data, str):
                try:
                    parsed_data = json.loads(data)
                except json.JSONDecodeError as e:
                    return ToolResult(
                        success=False,
                        result=None,
                        error_message=f"Invalid JSON: {str(e)}"
                    )
            else:
                parsed_data = data
            
            # Navigate the path
            current = parsed_data
            path_parts = path.split('.')
            
            try:
                for part in path_parts:
                    if isinstance(current, dict):
                        current = current[part]
                    elif isinstance(current, list):
                        current = current[int(part)]
                    else:
                        raise KeyError(f"Cannot access '{part}' on {type(current).__name__}")
                
                result = current
            except (KeyError, IndexError, ValueError, TypeError) as e:
                return ToolResult(
                    success=False,
                    result=None,
                    error_message=f"Path '{path}' not found: {str(e)}"
                )
        
        elif operation == 'keys':
            if isinstance(data, str):
                try:
                    parsed_data = json.loads(data)
                except json.JSONDecodeError as e:
                    return ToolResult(
                        success=False,
                        result=None,
                        error_message=f"Invalid JSON: {str(e)}"
                    )
            else:
                parsed_data = data
            
            if isinstance(parsed_data, dict):
                result = list(parsed_data.keys())
            else:
                return ToolResult(
                    success=False,
                    result=None,
                    error_message=f"Cannot get keys from {type(parsed_data).__name__}, expected dict"
                )
        
        elif operation == 'values':
            if isinstance(data, str):
                try:
                    parsed_data = json.loads(data)
                except json.JSONDecodeError as e:
                    return ToolResult(
                        success=False,
                        result=None,
                        error_message=f"Invalid JSON: {str(e)}"
                    )
            else:
                parsed_data = data
            
            if isinstance(parsed_data, dict):
                result = list(parsed_data.values())
            elif isinstance(parsed_data, list):
                result = parsed_data
            else:
                return ToolResult(
                    success=False,
                    result=None,
                    error_message=f"Cannot get values from {type(parsed_data).__name__}"
                )
        
        elif operation == 'size':
            if isinstance(data, str):
                try:
                    parsed_data = json.loads(data)
                except json.JSONDecodeError as e:
                    return ToolResult(
                        success=False,
                        result=None,
                        error_message=f"Invalid JSON: {str(e)}"
                    )
            else:
                parsed_data = data
            
            if isinstance(parsed_data, (dict, list)):
                result = {
                    "length": len(parsed_data),
                    "type": type(parsed_data).__name__
                }
            else:
                result = {
                    "length": 1,
                    "type": type(parsed_data).__name__
                }
        
        else:
            available_ops = [
                'parse', 'stringify', 'validate', 'pretty', 'minify',
                'extract', 'keys', 'values', 'size'
            ]
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
                "input_type": type(data).__name__ if data is not None else "None",
                "kwargs": kwargs
            }
        )
        
    except Exception as e:
        error_msg = f"JSON processing failed for operation '{operation}': {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        return ToolResult(
            success=False,
            result=None,
            error_message=error_msg
        )


def get_json_processor_help() -> str:
    """Get help text for the JSON processor tool."""
    return """
JSON Processor Tool Help:

Usage:
- process_json("operation", data, param=value)

Available Operations:

Basic Operations:
- 'parse': Parse JSON string to object
- 'stringify': Convert object to JSON string (indent=None)
- 'validate': Check if JSON string is valid
- 'pretty': Pretty-print JSON (indent=2)
- 'minify': Remove whitespace from JSON

Data Access:
- 'extract': Extract value by path (path="key.subkey.0")
- 'keys': Get all keys from JSON object
- 'values': Get all values from JSON object/array
- 'size': Get length/size of JSON data

Examples:
- process_json("parse", '{"name": "John", "age": 30}')
- process_json("stringify", {"name": "John"}, indent=2)
- process_json("validate", '{"valid": "json"}')
- process_json("extract", {"user": {"name": "John"}}, path="user.name")
- process_json("keys", {"a": 1, "b": 2})  # Returns ["a", "b"]
- process_json("pretty", '{"compact":"json"}')

Path Syntax for Extract:
- "key" - Access object key
- "key.subkey" - Access nested object
- "array.0" - Access array element by index
- "data.users.0.name" - Complex nested access

Note: The tool handles both JSON strings and Python objects as input.
"""
