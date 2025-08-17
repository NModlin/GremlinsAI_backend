# app/tools/tool_registry.py
"""
Tool registry for managing and organizing all available tools.
"""

import logging
from typing import Dict, Any, Callable, List, Optional
from dataclasses import dataclass
from .base_tool import ToolResult

logger = logging.getLogger(__name__)


@dataclass
class ToolInfo:
    """Information about a registered tool."""
    name: str
    function: Callable
    description: str
    category: str
    parameters: List[str]
    examples: List[str]


class ToolRegistry:
    """Registry for managing all available tools."""
    
    def __init__(self):
        self.tools: Dict[str, ToolInfo] = {}
        self._initialize_tools()
    
    def _initialize_tools(self):
        """Initialize all available tools."""
        try:
            # Import all tool functions
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
            
            # Register tools with metadata
            self.register_tool(
                name="calculator",
                function=calculate,
                description="Perform mathematical calculations with safe expression evaluation",
                category="Math",
                parameters=["expression"],
                examples=["calculate('2 + 3 * 4')", "calculate('sqrt(16)')"]
            )
            
            self.register_tool(
                name="web_search",
                function=web_search,
                description="Search the web using DuckDuckGo with result filtering and ranking",
                category="Web",
                parameters=["query", "max_results", "safe_search"],
                examples=["web_search('Python tutorial')", "web_search('weather NYC', max_results=5)"]
            )
            
            self.register_tool(
                name="code_interpreter",
                function=execute_python_code,
                description="Execute Python code in a sandboxed environment",
                category="Programming",
                parameters=["code", "timeout", "max_output_length"],
                examples=["execute_python_code('print(2 + 3)')", "execute_python_code('import math; print(math.pi)')"]
            )
            
            self.register_tool(
                name="api_caller",
                function=make_api_call,
                description="Make HTTP GET requests to APIs with security checks",
                category="Web",
                parameters=["url", "timeout", "max_response_size", "headers"],
                examples=["make_api_call('https://api.github.com/users/octocat')", "make_api_call('https://httpbin.org/json')"]
            )
            
            self.register_tool(
                name="text_processor",
                function=process_text,
                description="Process and analyze text with various operations",
                category="Text",
                parameters=["text", "operation"],
                examples=["process_text('Hello World', 'uppercase')", "process_text('test@example.com', 'extract_emails')"]
            )
            
            self.register_tool(
                name="datetime_tool",
                function=datetime_operation,
                description="Perform date and time operations",
                category="Utilities",
                parameters=["operation"],
                examples=["datetime_operation('now')", "datetime_operation('add', datetime_str='2023-01-01', days=7)"]
            )
            
            self.register_tool(
                name="json_processor",
                function=process_json,
                description="Parse, validate, and manipulate JSON data",
                category="Data",
                parameters=["operation", "data"],
                examples=["process_json('parse', '{\"key\": \"value\"}')", "process_json('pretty', data)"]
            )
            
            self.register_tool(
                name="hash_generator",
                function=generate_hash,
                description="Generate various types of hashes (MD5, SHA256, etc.)",
                category="Security",
                parameters=["text", "algorithm", "key"],
                examples=["generate_hash('hello world', 'sha256')", "generate_hash('message', 'sha256', key='secret')"]
            )
            
            self.register_tool(
                name="url_validator",
                function=validate_url,
                description="Validate and parse URLs",
                category="Web",
                parameters=["url", "operation"],
                examples=["validate_url('https://example.com', 'validate')", "validate_url('https://example.com/path?param=value', 'parse')"]
            )
            
            self.register_tool(
                name="base64_tool",
                function=base64_operation,
                description="Encode and decode Base64 data",
                category="Encoding",
                parameters=["operation", "data"],
                examples=["base64_operation('encode', 'Hello World')", "base64_operation('decode', 'SGVsbG8gV29ybGQ=')"]
            )
            
            self.register_tool(
                name="regex_tool",
                function=regex_operation,
                description="Perform regular expression operations",
                category="Text",
                parameters=["operation", "text", "pattern"],
                examples=["regex_operation('findall', 'test@example.com', r'[\\w.-]+@[\\w.-]+\\.[\\w]+')", "regex_operation('sub', 'hello world', 'world', replacement='universe')"]
            )
            
            logger.info(f"Initialized tool registry with {len(self.tools)} tools")
            
        except Exception as e:
            logger.error(f"Error initializing tools: {e}", exc_info=True)
    
    def register_tool(self, name: str, function: Callable, description: str, 
                     category: str, parameters: List[str], examples: List[str]):
        """Register a new tool."""
        tool_info = ToolInfo(
            name=name,
            function=function,
            description=description,
            category=category,
            parameters=parameters,
            examples=examples
        )
        self.tools[name] = tool_info
        logger.debug(f"Registered tool: {name}")
    
    def get_tool(self, name: str) -> Optional[ToolInfo]:
        """Get tool information by name."""
        return self.tools.get(name)
    
    def get_tool_function(self, name: str) -> Optional[Callable]:
        """Get tool function by name."""
        tool = self.get_tool(name)
        return tool.function if tool else None
    
    def list_tools(self) -> List[str]:
        """Get list of all tool names."""
        return list(self.tools.keys())
    
    def list_tools_by_category(self) -> Dict[str, List[str]]:
        """Get tools organized by category."""
        categories = {}
        for name, tool in self.tools.items():
            if tool.category not in categories:
                categories[tool.category] = []
            categories[tool.category].append(name)
        return categories
    
    def get_tool_help(self, name: str) -> Optional[str]:
        """Get help text for a specific tool."""
        tool = self.get_tool(name)
        if not tool:
            return None
        
        help_text = f"Tool: {tool.name}\n"
        help_text += f"Category: {tool.category}\n"
        help_text += f"Description: {tool.description}\n"
        help_text += f"Parameters: {', '.join(tool.parameters)}\n"
        help_text += "Examples:\n"
        for example in tool.examples:
            help_text += f"  - {example}\n"
        
        return help_text
    
    def get_all_tools_summary(self) -> str:
        """Get summary of all available tools."""
        summary = f"Available Tools ({len(self.tools)} total):\n\n"
        
        categories = self.list_tools_by_category()
        for category, tool_names in categories.items():
            summary += f"{category}:\n"
            for tool_name in tool_names:
                tool = self.tools[tool_name]
                summary += f"  - {tool_name}: {tool.description}\n"
            summary += "\n"
        
        return summary
    
    async def execute_tool(self, tool_name: str, *args, **kwargs) -> ToolResult:
        """Execute a tool by name."""
        tool_function = self.get_tool_function(tool_name)
        if not tool_function:
            return ToolResult(
                success=False,
                result=None,
                error_message=f"Tool '{tool_name}' not found",
                tool_name=tool_name
            )
        
        try:
            # Check if tool function is async
            import asyncio
            if asyncio.iscoroutinefunction(tool_function):
                result = await tool_function(*args, **kwargs)
            else:
                result = tool_function(*args, **kwargs)
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
            return ToolResult(
                success=False,
                result=None,
                error_message=f"Tool execution failed: {str(e)}",
                tool_name=tool_name
            )


# Global registry instance
_tool_registry = None

def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry instance."""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
    return _tool_registry
