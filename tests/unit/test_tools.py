# tests/unit/test_tools.py
"""
Unit tests for the comprehensive tool ecosystem

Tests cover:
- All 11+ production-ready tools
- Error handling and edge cases
- Input validation and sanitization
- Tool registry functionality
- Integration with ProductionAgent
"""

import pytest
import json
import base64
from unittest.mock import Mock, patch, MagicMock

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from app.tools.calculator import calculate
from app.tools.web_search import web_search
from app.tools.code_interpreter import execute_python_code
from app.tools.api_caller import make_api_call
from app.tools.text_processor import process_text
from app.tools.datetime_tool import datetime_operation
from app.tools.json_processor import process_json
from app.tools.hash_generator import generate_hash
from app.tools.url_validator import validate_url
from app.tools.base64_tool import base64_operation
from app.tools.regex_tool import regex_operation
from app.tools.tool_registry import ToolRegistry, get_tool_registry
from app.tools.base_tool import ToolResult


class TestCalculatorTool:
    """Test calculator tool functionality."""
    
    def test_basic_arithmetic(self):
        """Test basic arithmetic operations."""
        result = calculate("2 + 3")
        assert result.success is True
        assert result.result == 5
        
        result = calculate("10 - 4")
        assert result.success is True
        assert result.result == 6
        
        result = calculate("3 * 4")
        assert result.success is True
        assert result.result == 12
        
        result = calculate("15 / 3")
        assert result.success is True
        assert result.result == 5.0
    
    def test_advanced_operations(self):
        """Test advanced mathematical operations."""
        result = calculate("2**3")
        assert result.success is True
        assert result.result == 8
        
        result = calculate("sqrt(16)")
        assert result.success is True
        assert result.result == 4.0
        
        result = calculate("sin(pi/2)")
        assert result.success is True
        assert abs(result.result - 1.0) < 0.0001
    
    def test_division_by_zero(self):
        """Test division by zero handling."""
        result = calculate("5 / 0")
        assert result.success is False
        assert "Division by zero" in result.error_message
    
    def test_invalid_expression(self):
        """Test invalid expression handling."""
        result = calculate("2 +")
        assert result.success is False
        assert "Invalid expression" in result.error_message
        
        result = calculate("invalid_function(5)")
        assert result.success is False
        assert "Unsupported function" in result.error_message
    
    def test_empty_expression(self):
        """Test empty expression handling."""
        result = calculate("")
        assert result.success is False
        assert "cannot be empty" in result.error_message


class TestWebSearchTool:
    """Test web search tool functionality."""
    
    @patch('app.tools.web_search.DDGS')
    def test_successful_search(self, mock_ddgs):
        """Test successful web search."""
        # Mock search results
        mock_results = [
            {
                'title': 'Python Tutorial',
                'href': 'https://example.com/python',
                'body': 'Learn Python programming'
            }
        ]
        
        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.text.return_value = mock_results
        mock_ddgs.return_value.__enter__.return_value = mock_ddgs_instance
        
        result = web_search("Python tutorial")
        
        assert result.success is True
        assert len(result.result) == 1
        assert result.result[0]['title'] == 'Python Tutorial'
    
    def test_empty_query(self):
        """Test empty query handling."""
        result = web_search("")
        assert result.success is False
        assert "cannot be empty" in result.error_message
    
    def test_invalid_max_results(self):
        """Test invalid max_results parameter."""
        result = web_search("test", max_results=0)
        assert result.success is False
        assert "must be between 1 and 20" in result.error_message


class TestCodeInterpreterTool:
    """Test code interpreter tool functionality."""
    
    def test_simple_code_execution(self):
        """Test simple code execution."""
        result = execute_python_code("print('Hello World')")
        assert result.success is True
        assert "Hello World" in result.result
    
    def test_mathematical_calculation(self):
        """Test mathematical calculations."""
        result = execute_python_code("result = 2 + 3; print(result)")
        assert result.success is True
        assert "5" in result.result
    
    def test_import_safe_module(self):
        """Test importing safe modules."""
        result = execute_python_code("import math; print(math.pi)")
        assert result.success is True
        assert "3.14" in result.result
    
    def test_security_restrictions(self):
        """Test security restrictions."""
        # Test dangerous function
        result = execute_python_code("exec('print(1)')")
        assert result.success is False
        assert "security violations" in result.error_message
        
        # Test unsafe import
        result = execute_python_code("import os")
        assert result.success is False
        assert "security violations" in result.error_message
    
    def test_empty_code(self):
        """Test empty code handling."""
        result = execute_python_code("")
        assert result.success is False
        assert "cannot be empty" in result.error_message


class TestAPICallerTool:
    """Test API caller tool functionality."""
    
    @patch('app.tools.api_caller.requests.get')
    def test_successful_api_call(self, mock_get):
        """Test successful API call."""
        # Mock response
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.headers = {'content-type': 'application/json'}
        mock_response.json.return_value = {'key': 'value'}
        mock_response.text = '{"key": "value"}'
        mock_response.iter_content.return_value = [b'{"key": "value"}']
        mock_get.return_value = mock_response
        
        result = make_api_call("https://api.example.com/data")
        
        assert result.success is True
        assert result.result == {'key': 'value'}
    
    def test_invalid_url(self):
        """Test invalid URL handling."""
        result = make_api_call("not-a-url")
        assert result.success is False
        assert "blocked for security reasons" in result.error_message
    
    def test_blocked_domain(self):
        """Test blocked domain handling."""
        result = make_api_call("http://localhost:8080/api")
        assert result.success is False
        assert "blocked for security reasons" in result.error_message


class TestTextProcessorTool:
    """Test text processor tool functionality."""
    
    def test_text_analysis(self):
        """Test text analysis operation."""
        result = process_text("Hello world! This is a test.", "analyze")
        assert result.success is True
        assert result.result['word_count'] == 6
        assert result.result['character_count'] == 28
    
    def test_case_conversion(self):
        """Test case conversion operations."""
        result = process_text("Hello World", "uppercase")
        assert result.success is True
        assert result.result == "HELLO WORLD"
        
        result = process_text("Hello World", "lowercase")
        assert result.success is True
        assert result.result == "hello world"
    
    def test_email_extraction(self):
        """Test email extraction."""
        result = process_text("Contact us at test@example.com", "extract_emails")
        assert result.success is True
        assert "test@example.com" in result.result
    
    def test_invalid_operation(self):
        """Test invalid operation handling."""
        result = process_text("test", "invalid_operation")
        assert result.success is False
        assert "Unknown operation" in result.error_message


class TestDateTimeTool:
    """Test datetime tool functionality."""
    
    def test_current_datetime(self):
        """Test getting current datetime."""
        result = datetime_operation("now")
        assert result.success is True
        assert isinstance(result.result, str)
        assert "T" in result.result  # ISO format
    
    def test_date_parsing(self):
        """Test date parsing."""
        result = datetime_operation("parse", datetime_str="2023-01-01 12:00:00")
        assert result.success is True
        assert result.result['year'] == 2023
        assert result.result['month'] == 1
        assert result.result['day'] == 1
    
    def test_date_arithmetic(self):
        """Test date arithmetic."""
        result = datetime_operation("add", datetime_str="2023-01-01", days=7)
        assert result.success is True
        assert "2023-01-08" in result.result['new_datetime']
    
    def test_invalid_datetime(self):
        """Test invalid datetime handling."""
        result = datetime_operation("parse", datetime_str="invalid-date")
        assert result.success is False
        assert "Unable to parse" in result.error_message


class TestJSONProcessorTool:
    """Test JSON processor tool functionality."""
    
    def test_json_parsing(self):
        """Test JSON parsing."""
        result = process_json("parse", '{"name": "John", "age": 30}')
        assert result.success is True
        assert result.result['name'] == "John"
        assert result.result['age'] == 30
    
    def test_json_stringify(self):
        """Test JSON stringification."""
        data = {"name": "John", "age": 30}
        result = process_json("stringify", data)
        assert result.success is True
        assert '"name"' in result.result
        assert '"John"' in result.result
    
    def test_json_validation(self):
        """Test JSON validation."""
        result = process_json("validate", '{"valid": "json"}')
        assert result.success is True
        assert result.result['valid'] is True
        
        result = process_json("validate", '{"invalid": json}')
        assert result.success is True
        assert result.result['valid'] is False
    
    def test_json_extraction(self):
        """Test JSON path extraction."""
        data = {"user": {"name": "John", "age": 30}}
        result = process_json("extract", data, path="user.name")
        assert result.success is True
        assert result.result == "John"


class TestHashGeneratorTool:
    """Test hash generator tool functionality."""
    
    def test_sha256_hash(self):
        """Test SHA256 hash generation."""
        result = generate_hash("hello world", "sha256")
        assert result.success is True
        assert len(result.result) == 64  # SHA256 hex length
        assert result.result == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
    
    def test_md5_hash(self):
        """Test MD5 hash generation."""
        result = generate_hash("hello world", "md5")
        assert result.success is True
        assert len(result.result) == 32  # MD5 hex length
    
    def test_hmac_generation(self):
        """Test HMAC generation."""
        result = generate_hash("message", "sha256", key="secret")
        assert result.success is True
        assert len(result.result) == 64  # SHA256 hex length
        assert result.metadata['uses_key'] is True
    
    def test_invalid_algorithm(self):
        """Test invalid algorithm handling."""
        result = generate_hash("test", "invalid_algorithm")
        assert result.success is False
        assert "Unsupported algorithm" in result.error_message


class TestURLValidatorTool:
    """Test URL validator tool functionality."""
    
    def test_valid_url(self):
        """Test valid URL validation."""
        result = validate_url("https://example.com/path", "validate")
        assert result.success is True
        assert result.result['is_valid'] is True
    
    def test_url_parsing(self):
        """Test URL parsing."""
        result = validate_url("https://example.com:8080/path?param=value", "parse")
        assert result.success is True
        assert result.result['scheme'] == 'https'
        assert result.result['hostname'] == 'example.com'
        assert result.result['port'] == 8080
        assert result.result['path'] == '/path'
    
    def test_domain_extraction(self):
        """Test domain extraction."""
        result = validate_url("https://sub.example.com/path", "extract_domain")
        assert result.success is True
        assert result.result['domain_name'] == 'example'
        assert result.result['tld'] == 'com'
        assert result.result['subdomain'] == 'sub'
    
    def test_invalid_url(self):
        """Test invalid URL handling."""
        result = validate_url("not-a-url", "validate")
        assert result.success is True
        assert result.result['is_valid'] is False


class TestBase64Tool:
    """Test Base64 tool functionality."""
    
    def test_base64_encoding(self):
        """Test Base64 encoding."""
        result = base64_operation("encode", "Hello World")
        assert result.success is True
        assert result.result == "SGVsbG8gV29ybGQ="
    
    def test_base64_decoding(self):
        """Test Base64 decoding."""
        result = base64_operation("decode", "SGVsbG8gV29ybGQ=")
        assert result.success is True
        assert result.result == "Hello World"
    
    def test_invalid_base64(self):
        """Test invalid Base64 handling."""
        result = base64_operation("decode", "invalid-base64!")
        assert result.success is False
        assert "Invalid base64" in result.error_message
    
    def test_invalid_operation(self):
        """Test invalid operation handling."""
        result = base64_operation("invalid", "test")
        assert result.success is False
        assert "Unknown operation" in result.error_message


class TestRegexTool:
    """Test regex tool functionality."""
    
    def test_regex_findall(self):
        """Test regex findall operation."""
        result = regex_operation("findall", "test@example.com and user@test.org", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
        assert result.success is True
        assert len(result.result['matches']) == 2
        assert "test@example.com" in result.result['matches']
        assert "user@test.org" in result.result['matches']
    
    def test_regex_substitution(self):
        """Test regex substitution."""
        result = regex_operation("sub", "hello world", r"world", replacement="universe")
        assert result.success is True
        assert result.result['new_text'] == "hello universe"
        assert result.result['changes_made'] is True
    
    def test_regex_split(self):
        """Test regex split operation."""
        result = regex_operation("split", "a,b,c,d", r",")
        assert result.success is True
        assert result.result['parts'] == ['a', 'b', 'c', 'd']
        assert result.result['count'] == 4
    
    def test_invalid_regex(self):
        """Test invalid regex pattern handling."""
        result = regex_operation("findall", "test", r"[invalid")
        assert result.success is False
        assert "Invalid regex pattern" in result.error_message


class TestToolRegistry:
    """Test tool registry functionality."""
    
    def test_tool_registration(self):
        """Test tool registration and retrieval."""
        registry = ToolRegistry()
        
        # Check that tools are registered
        tools = registry.list_tools()
        assert len(tools) >= 11  # At least 11 tools
        
        # Check specific tools
        assert "calculator" in tools
        assert "web_search" in tools
        assert "code_interpreter" in tools
        assert "api_caller" in tools
    
    def test_tool_categories(self):
        """Test tool categorization."""
        registry = ToolRegistry()
        categories = registry.list_tools_by_category()
        
        assert "Math" in categories
        assert "Web" in categories
        assert "Programming" in categories
        assert "Text" in categories
    
    def test_tool_help(self):
        """Test tool help generation."""
        registry = ToolRegistry()
        help_text = registry.get_tool_help("calculator")
        
        assert help_text is not None
        assert "calculator" in help_text
        assert "Math" in help_text
        assert "Examples:" in help_text
    
    @pytest.mark.asyncio
    async def test_tool_execution(self):
        """Test tool execution through registry."""
        registry = ToolRegistry()
        
        # Test calculator execution
        result = await registry.execute_tool("calculator", "2 + 3")
        assert result.success is True
        assert result.result == 5
        
        # Test non-existent tool
        result = await registry.execute_tool("non_existent_tool", "test")
        assert result.success is False
        assert "not found" in result.error_message


if __name__ == "__main__":
    pytest.main([__file__])
