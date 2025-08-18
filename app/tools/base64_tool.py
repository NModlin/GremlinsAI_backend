# app/tools/base64_tool.py
"""
Base64 encoding and decoding tool.
"""

import base64
import logging
from .base_tool import tool_wrapper, ToolResult, validate_input, sanitize_string

logger = logging.getLogger(__name__)


@tool_wrapper("base64_tool")
def base64_operation(operation: str, data: str) -> ToolResult:
    """
    Perform Base64 encoding or decoding operations.
    
    Args:
        operation: Operation to perform ('encode' or 'decode')
        data: Data to encode/decode
        
    Returns:
        ToolResult with encoded/decoded data
        
    Examples:
        base64_operation("encode", "Hello World")
        base64_operation("decode", "SGVsbG8gV29ybGQ=")
    """
    try:
        operation = validate_input(operation, str, "operation")
        data = validate_input(data, str, "data")
        
        operation = operation.lower().strip()
        data = sanitize_string(data, max_length=100000)
        
        if operation == 'encode':
            # Encode string to base64
            data_bytes = data.encode('utf-8')
            encoded_bytes = base64.b64encode(data_bytes)
            result = encoded_bytes.decode('ascii')
            
            return ToolResult(
                success=True,
                result=result,
                metadata={
                    "operation": "encode",
                    "input_length": len(data),
                    "output_length": len(result),
                    "encoding": "utf-8"
                }
            )
        
        elif operation == 'decode':
            # Decode base64 to string
            try:
                decoded_bytes = base64.b64decode(data)
                result = decoded_bytes.decode('utf-8')
                
                return ToolResult(
                    success=True,
                    result=result,
                    metadata={
                        "operation": "decode",
                        "input_length": len(data),
                        "output_length": len(result),
                        "encoding": "utf-8"
                    }
                )
            except Exception as e:
                return ToolResult(
                    success=False,
                    result=None,
                    error_message=f"Invalid base64 data: {str(e)}"
                )
        
        else:
            return ToolResult(
                success=False,
                result=None,
                error_message=f"Unknown operation '{operation}'. Available operations: encode, decode"
            )
        
    except Exception as e:
        error_msg = f"Base64 operation '{operation}' failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        return ToolResult(
            success=False,
            result=None,
            error_message=error_msg
        )


def get_base64_help() -> str:
    """Get help text for the base64 tool."""
    return """
Base64 Tool Help:

Usage:
- base64_operation("encode", "text_to_encode")
- base64_operation("decode", "base64_string")

Operations:
- 'encode': Convert text to Base64 encoding
- 'decode': Convert Base64 back to text

Examples:
- base64_operation("encode", "Hello World")  # Returns: SGVsbG8gV29ybGQ=
- base64_operation("decode", "SGVsbG8gV29ybGQ=")  # Returns: Hello World

Features:
- UTF-8 text encoding/decoding
- Error handling for invalid Base64
- Input validation and sanitization
- Metadata about operation results

Use Cases:
- Encoding text for safe transmission
- Decoding Base64-encoded data
- Data obfuscation (not encryption!)
- API data formatting

Note: Base64 is encoding, not encryption. Do not use for security purposes.
"""
