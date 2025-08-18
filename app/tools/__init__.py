# app/tools/__init__.py
"""
GremlinsAI Tool Ecosystem

This package provides a comprehensive set of production-ready tools for the
ProductionAgent to use during its ReAct reasoning cycles.

Tools are designed with:
- Robust error handling
- Input validation and sanitization
- Comprehensive logging
- Security considerations
- Consistent interfaces
"""

from .calculator import calculate
from .web_search import web_search
from .code_interpreter import execute_python_code
from .api_caller import make_api_call
from .text_processor import process_text
from .datetime_tool import datetime_operation
from .json_processor import process_json
from .hash_generator import generate_hash
from .url_validator import validate_url
from .base64_tool import base64_operation
from .regex_tool import regex_operation
from .tool_registry import ToolRegistry, get_tool_registry

__all__ = [
    'calculate',
    'web_search',
    'execute_python_code',
    'make_api_call',
    'process_text',
    'datetime_operation',
    'process_json',
    'generate_hash',
    'validate_url',
    'base64_operation',
    'regex_operation',
    'ToolRegistry',
    'get_tool_registry'
]
