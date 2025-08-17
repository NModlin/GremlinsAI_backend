# app/tools/code_interpreter.py
"""
Sandboxed Python code execution tool with security restrictions.

Features:
- Safe code execution with restricted imports
- Timeout handling
- Output capture (stdout, stderr)
- Memory and execution limits
- Security restrictions
"""

import sys
import io
import ast
import time
import signal
import logging
import traceback
from typing import Dict, Any, Optional, List
from contextlib import redirect_stdout, redirect_stderr
from .base_tool import tool_wrapper, ToolResult, validate_input, sanitize_string, truncate_output

logger = logging.getLogger(__name__)

# Allowed built-in functions for safe execution
SAFE_BUILTINS = {
    'abs', 'all', 'any', 'ascii', 'bin', 'bool', 'bytearray', 'bytes',
    'callable', 'chr', 'classmethod', 'complex', 'dict', 'dir', 'divmod',
    'enumerate', 'filter', 'float', 'format', 'frozenset', 'getattr',
    'hasattr', 'hash', 'hex', 'id', 'int', 'isinstance', 'issubclass',
    'iter', 'len', 'list', 'map', 'max', 'min', 'next', 'oct', 'ord',
    'pow', 'print', 'range', 'repr', 'reversed', 'round', 'set', 'slice',
    'sorted', 'staticmethod', 'str', 'sum', 'tuple', 'type', 'vars', 'zip'
}

# Allowed modules for import
SAFE_MODULES = {
    'math', 'random', 'datetime', 'json', 'base64', 'hashlib', 'uuid',
    'collections', 'itertools', 'functools', 'operator', 'string', 're',
    'decimal', 'fractions', 'statistics', 'calendar'
}

# Restricted AST node types
RESTRICTED_NODES = {
    ast.Import, ast.ImportFrom, ast.FunctionDef, ast.AsyncFunctionDef,
    ast.ClassDef, ast.Global, ast.Nonlocal, ast.Delete
}


class TimeoutError(Exception):
    """Custom timeout exception."""
    pass


class CodeSecurityChecker(ast.NodeVisitor):
    """AST visitor to check for potentially dangerous code constructs."""
    
    def __init__(self):
        self.violations = []
    
    def visit_Import(self, node):
        """Check import statements."""
        for alias in node.names:
            if alias.name not in SAFE_MODULES:
                self.violations.append(f"Unsafe import: {alias.name}")
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        """Check from-import statements."""
        if node.module and node.module not in SAFE_MODULES:
            self.violations.append(f"Unsafe import from: {node.module}")
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node):
        """Check function definitions."""
        self.violations.append(f"Function definition not allowed: {node.name}")
        self.generic_visit(node)
    
    def visit_ClassDef(self, node):
        """Check class definitions."""
        self.violations.append(f"Class definition not allowed: {node.name}")
        self.generic_visit(node)
    
    def visit_Call(self, node):
        """Check function calls for dangerous functions."""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            dangerous_funcs = {'exec', 'eval', 'compile', 'open', '__import__'}
            if func_name in dangerous_funcs:
                self.violations.append(f"Dangerous function call: {func_name}")
        self.generic_visit(node)
    
    def visit_Attribute(self, node):
        """Check attribute access for dangerous attributes."""
        if isinstance(node.attr, str):
            dangerous_attrs = {'__globals__', '__locals__', '__code__', '__dict__'}
            if node.attr in dangerous_attrs:
                self.violations.append(f"Dangerous attribute access: {node.attr}")
        self.generic_visit(node)


def timeout_handler(signum, frame):
    """Signal handler for execution timeout."""
    raise TimeoutError("Code execution timeout")


def check_code_safety(code: str) -> List[str]:
    """
    Check if code is safe to execute.
    
    Args:
        code: Python code string
        
    Returns:
        List of security violations (empty if safe)
    """
    try:
        tree = ast.parse(code)
        checker = CodeSecurityChecker()
        checker.visit(tree)
        return checker.violations
    except SyntaxError as e:
        return [f"Syntax error: {str(e)}"]


def create_safe_globals() -> Dict[str, Any]:
    """Create a restricted global namespace for code execution."""
    safe_globals = {
        '__builtins__': {name: getattr(__builtins__, name) for name in SAFE_BUILTINS if hasattr(__builtins__, name)}
    }
    
    # Add safe modules
    for module_name in SAFE_MODULES:
        try:
            module = __import__(module_name)
            safe_globals[module_name] = module
        except ImportError:
            logger.warning(f"Safe module {module_name} not available")
    
    return safe_globals


@tool_wrapper("code_interpreter")
def execute_python_code(code: str, timeout: int = 10, max_output_length: int = 5000) -> ToolResult:
    """
    Execute Python code in a sandboxed environment.
    
    Args:
        code: Python code to execute
        timeout: Maximum execution time in seconds (1-30)
        max_output_length: Maximum output length in characters
        
    Returns:
        ToolResult with execution results
        
    Security Features:
    - Restricted imports (only safe modules)
    - No file system access
    - No network access
    - Execution timeout
    - Output length limits
    - No function/class definitions
    
    Examples:
        execute_python_code("print(2 + 3)")
        execute_python_code("import math; print(math.sqrt(16))")
        execute_python_code("result = sum(range(10)); print(result)")
    """
    try:
        # Validate inputs
        code = validate_input(code, str, "code")
        code = sanitize_string(code, max_length=10000)
        
        if not code.strip():
            raise ValueError("Code cannot be empty")
        
        timeout = validate_input(timeout, int, "timeout")
        if not 1 <= timeout <= 30:
            raise ValueError("Timeout must be between 1 and 30 seconds")
        
        max_output_length = validate_input(max_output_length, int, "max_output_length")
        if not 100 <= max_output_length <= 50000:
            raise ValueError("max_output_length must be between 100 and 50000")
        
        logger.info(f"Executing Python code (timeout: {timeout}s)")
        
        # Check code safety
        violations = check_code_safety(code)
        if violations:
            return ToolResult(
                success=False,
                result=None,
                error_message=f"Code security violations: {'; '.join(violations)}"
            )
        
        # Prepare execution environment
        safe_globals = create_safe_globals()
        safe_locals = {}
        
        # Capture output
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        execution_result = None
        execution_error = None
        
        # Set up timeout (Unix-like systems only)
        if hasattr(signal, 'SIGALRM'):
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout)
        
        start_time = time.time()
        
        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                # Compile and execute the code
                compiled_code = compile(code, '<string>', 'exec')
                exec(compiled_code, safe_globals, safe_locals)
                
                # If code doesn't produce output, try to get the last expression value
                if not stdout_capture.getvalue():
                    try:
                        # Try to evaluate as expression
                        expr_result = eval(compile(code, '<string>', 'eval'), safe_globals, safe_locals)
                        if expr_result is not None:
                            execution_result = str(expr_result)
                    except:
                        pass  # Not an expression, that's fine
        
        except TimeoutError:
            execution_error = f"Code execution timeout after {timeout} seconds"
        
        except Exception as e:
            execution_error = f"Execution error: {str(e)}"
            # Capture traceback
            tb_lines = traceback.format_exc().split('\n')
            # Filter out internal traceback lines
            filtered_tb = [line for line in tb_lines if '<string>' in line or 'Error:' in line or line.strip().startswith('File')]
            if filtered_tb:
                execution_error += f"\nTraceback: {' '.join(filtered_tb[-3:])}"
        
        finally:
            # Clean up timeout
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
        
        execution_time = time.time() - start_time
        
        # Get captured output
        stdout_output = stdout_capture.getvalue()
        stderr_output = stderr_capture.getvalue()
        
        # Combine outputs
        output_parts = []
        if stdout_output:
            output_parts.append(f"Output:\n{stdout_output}")
        if execution_result:
            output_parts.append(f"Result: {execution_result}")
        if stderr_output:
            output_parts.append(f"Errors:\n{stderr_output}")
        
        combined_output = '\n'.join(output_parts)
        
        # Handle execution errors
        if execution_error:
            return ToolResult(
                success=False,
                result=None,
                error_message=execution_error,
                metadata={
                    "code": code[:500],  # Truncated code for logging
                    "execution_time": execution_time,
                    "stdout": stdout_output[:1000] if stdout_output else "",
                    "stderr": stderr_output[:1000] if stderr_output else ""
                }
            )
        
        # Truncate output if too long
        if len(combined_output) > max_output_length:
            combined_output = truncate_output(combined_output, max_output_length)
        
        # Success case
        return ToolResult(
            success=True,
            result=combined_output if combined_output else "Code executed successfully (no output)",
            metadata={
                "code": code[:500],  # Truncated code for logging
                "execution_time": execution_time,
                "output_length": len(combined_output),
                "has_stdout": bool(stdout_output),
                "has_stderr": bool(stderr_output),
                "has_result": bool(execution_result)
            }
        )
        
    except Exception as e:
        error_msg = f"Code execution setup failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        return ToolResult(
            success=False,
            result=None,
            error_message=error_msg
        )


def get_code_interpreter_help() -> str:
    """Get help text for the code interpreter tool."""
    return """
Code Interpreter Tool Help:

Usage:
- execute_python_code("your_code_here")
- execute_python_code("code", timeout=15, max_output_length=1000)

Parameters:
- code: Python code to execute (required)
- timeout: Maximum execution time in seconds (1-30, default: 10)
- max_output_length: Maximum output length (100-50000, default: 5000)

Allowed Operations:
- Basic Python operations and built-in functions
- Math calculations and string operations
- List/dict/set operations
- Control flow (if/else, loops)
- Safe module imports: math, random, datetime, json, etc.

Security Restrictions:
- No file system access
- No network access
- No function/class definitions
- No dangerous built-ins (exec, eval, open, etc.)
- Execution timeout protection
- Output length limits

Examples:
- execute_python_code("print(2 + 3)")
- execute_python_code("import math; print(math.sqrt(16))")
- execute_python_code("numbers = [1,2,3,4,5]; print(sum(numbers))")
- execute_python_code("import json; data = {'key': 'value'}; print(json.dumps(data))")

Note: This tool provides a sandboxed Python environment for safe code execution.
"""
