# app/tools/regex_tool.py
"""
Regular expression tool for pattern matching and text manipulation.
"""

import re
import logging
from typing import List, Dict, Any, Optional
from .base_tool import tool_wrapper, ToolResult, validate_input, sanitize_string

logger = logging.getLogger(__name__)


@tool_wrapper("regex_tool")
def regex_operation(operation: str, text: str, pattern: str, **kwargs) -> ToolResult:
    """
    Perform regular expression operations on text.
    
    Args:
        operation: Operation to perform
        text: Text to search/modify
        pattern: Regular expression pattern
        **kwargs: Additional parameters (replacement, flags, etc.)
        
    Available Operations:
    - 'match': Check if pattern matches at start of text
    - 'search': Search for pattern anywhere in text
    - 'findall': Find all matches of pattern
    - 'finditer': Find all matches with positions
    - 'sub': Replace matches with replacement text
    - 'split': Split text using pattern as delimiter
    - 'validate': Validate if pattern is valid regex
    
    Returns:
        ToolResult with regex operation results
        
    Examples:
        regex_operation("findall", "test@example.com", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
        regex_operation("sub", "hello world", r"world", replacement="universe")
    """
    try:
        operation = validate_input(operation, str, "operation")
        text = validate_input(text, str, "text")
        pattern = validate_input(pattern, str, "pattern")
        
        operation = operation.lower().strip()
        text = sanitize_string(text, max_length=50000)
        pattern = sanitize_string(pattern, max_length=1000)
        
        # Parse flags
        flags = 0
        flag_names = kwargs.get('flags', [])
        if isinstance(flag_names, str):
            flag_names = [flag_names]
        
        flag_map = {
            'ignorecase': re.IGNORECASE,
            'multiline': re.MULTILINE,
            'dotall': re.DOTALL,
            'verbose': re.VERBOSE,
            'ascii': re.ASCII
        }
        
        for flag_name in flag_names:
            if flag_name.lower() in flag_map:
                flags |= flag_map[flag_name.lower()]
        
        logger.info(f"Regex operation: {operation} with pattern: {pattern}")
        
        try:
            compiled_pattern = re.compile(pattern, flags)
        except re.error as e:
            return ToolResult(
                success=False,
                result=None,
                error_message=f"Invalid regex pattern: {str(e)}"
            )
        
        if operation == 'match':
            match = compiled_pattern.match(text)
            if match:
                result = {
                    "matched": True,
                    "match": match.group(0),
                    "groups": match.groups(),
                    "groupdict": match.groupdict(),
                    "start": match.start(),
                    "end": match.end()
                }
            else:
                result = {"matched": False}
        
        elif operation == 'search':
            match = compiled_pattern.search(text)
            if match:
                result = {
                    "found": True,
                    "match": match.group(0),
                    "groups": match.groups(),
                    "groupdict": match.groupdict(),
                    "start": match.start(),
                    "end": match.end()
                }
            else:
                result = {"found": False}
        
        elif operation == 'findall':
            matches = compiled_pattern.findall(text)
            result = {
                "matches": matches,
                "count": len(matches)
            }
        
        elif operation == 'finditer':
            matches = []
            for match in compiled_pattern.finditer(text):
                matches.append({
                    "match": match.group(0),
                    "groups": match.groups(),
                    "groupdict": match.groupdict(),
                    "start": match.start(),
                    "end": match.end()
                })
            
            result = {
                "matches": matches,
                "count": len(matches)
            }
        
        elif operation == 'sub':
            replacement = kwargs.get('replacement', '')
            if not isinstance(replacement, str):
                raise ValueError("replacement parameter must be a string")
            
            count = kwargs.get('count', 0)  # 0 means replace all
            
            new_text = compiled_pattern.sub(replacement, text, count=count)
            
            result = {
                "original_text": text[:500] + "..." if len(text) > 500 else text,
                "new_text": new_text,
                "replacement": replacement,
                "changes_made": text != new_text,
                "replacements_count": len(compiled_pattern.findall(text))
            }
        
        elif operation == 'split':
            maxsplit = kwargs.get('maxsplit', 0)  # 0 means no limit
            
            parts = compiled_pattern.split(text, maxsplit=maxsplit)
            
            result = {
                "parts": parts,
                "count": len(parts),
                "original_length": len(text)
            }
        
        elif operation == 'validate':
            # Pattern is already validated above, so if we get here it's valid
            result = {
                "valid": True,
                "pattern": pattern,
                "flags": list(flag_names) if flag_names else []
            }
        
        else:
            available_ops = [
                'match', 'search', 'findall', 'finditer', 'sub', 'split', 'validate'
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
                "pattern": pattern,
                "text_length": len(text),
                "flags": list(flag_names) if flag_names else [],
                "kwargs": {k: v for k, v in kwargs.items() if k != 'flags'}
            }
        )
        
    except Exception as e:
        error_msg = f"Regex operation '{operation}' failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        return ToolResult(
            success=False,
            result=None,
            error_message=error_msg
        )


def get_regex_help() -> str:
    """Get help text for the regex tool."""
    return """
Regex Tool Help:

Usage:
- regex_operation("operation", "text", "pattern", param=value)

Available Operations:

Matching:
- 'match': Check if pattern matches at start of text
- 'search': Search for pattern anywhere in text
- 'findall': Find all matches of pattern
- 'finditer': Find all matches with positions

Modification:
- 'sub': Replace matches (replacement="new_text", count=0)
- 'split': Split text using pattern (maxsplit=0)

Validation:
- 'validate': Check if regex pattern is valid

Parameters:
- flags: List of flags ['ignorecase', 'multiline', 'dotall', 'verbose', 'ascii']
- replacement: Replacement text for 'sub' operation
- count: Max replacements for 'sub' (0 = all)
- maxsplit: Max splits for 'split' (0 = no limit)

Examples:
- regex_operation("findall", "test@example.com", r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
- regex_operation("sub", "hello world", r"world", replacement="universe")
- regex_operation("split", "a,b,c", r",")
- regex_operation("search", "Hello World", r"world", flags=["ignorecase"])

Common Patterns:
- Email: r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
- URL: r"https?://[^\s]+"
- Phone: r"\b\d{3}-\d{3}-\d{4}\b"
- IP: r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"

Note: Use raw strings (r"pattern") to avoid escaping issues.
"""
