# app/tools/calculator.py
"""
Calculator tool for basic arithmetic operations with robust error handling.

Supports:
- Basic arithmetic: +, -, *, /, **, %
- Mathematical functions: sqrt, sin, cos, tan, log, exp
- Constants: pi, e
- Safe expression evaluation
"""

import ast
import math
import operator
import logging
from typing import Union, Dict, Any
from .base_tool import tool_wrapper, ToolResult, validate_input, sanitize_string

logger = logging.getLogger(__name__)

# Safe operators for expression evaluation
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

# Safe mathematical functions
SAFE_FUNCTIONS = {
    'abs': abs,
    'round': round,
    'min': min,
    'max': max,
    'sum': sum,
    'sqrt': math.sqrt,
    'sin': math.sin,
    'cos': math.cos,
    'tan': math.tan,
    'asin': math.asin,
    'acos': math.acos,
    'atan': math.atan,
    'log': math.log,
    'log10': math.log10,
    'exp': math.exp,
    'ceil': math.ceil,
    'floor': math.floor,
    'factorial': math.factorial,
}

# Safe constants
SAFE_CONSTANTS = {
    'pi': math.pi,
    'e': math.e,
    'tau': math.tau,
}


class SafeExpressionEvaluator(ast.NodeVisitor):
    """Safe expression evaluator that only allows whitelisted operations."""
    
    def visit_BinOp(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        operator_func = SAFE_OPERATORS.get(type(node.op))
        
        if operator_func is None:
            raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
        
        # Handle division by zero
        if isinstance(node.op, ast.Div) and right == 0:
            raise ZeroDivisionError("Division by zero")
        
        # Handle modulo by zero
        if isinstance(node.op, ast.Mod) and right == 0:
            raise ZeroDivisionError("Modulo by zero")
        
        # Handle negative exponents for integer bases
        if isinstance(node.op, ast.Pow):
            if isinstance(left, int) and isinstance(right, (int, float)) and right < 0:
                return float(left) ** right
        
        return operator_func(left, right)
    
    def visit_UnaryOp(self, node):
        operand = self.visit(node.operand)
        operator_func = SAFE_OPERATORS.get(type(node.op))
        
        if operator_func is None:
            raise ValueError(f"Unsupported unary operator: {type(node.op).__name__}")
        
        return operator_func(operand)
    
    def visit_Call(self, node):
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only simple function calls are allowed")
        
        func_name = node.func.id
        if func_name not in SAFE_FUNCTIONS:
            raise ValueError(f"Unsupported function: {func_name}")
        
        args = [self.visit(arg) for arg in node.args]
        
        try:
            return SAFE_FUNCTIONS[func_name](*args)
        except Exception as e:
            raise ValueError(f"Error calling function {func_name}: {str(e)}")
    
    def visit_Name(self, node):
        if node.id in SAFE_CONSTANTS:
            return SAFE_CONSTANTS[node.id]
        else:
            raise ValueError(f"Unsupported name/variable: {node.id}")
    
    def visit_Constant(self, node):
        # Handle numbers
        if isinstance(node.value, (int, float)):
            return node.value
        else:
            raise ValueError(f"Unsupported constant type: {type(node.value)}")
    
    def visit_Num(self, node):  # For Python < 3.8 compatibility
        return node.n
    
    def generic_visit(self, node):
        raise ValueError(f"Unsupported AST node: {type(node).__name__}")


def safe_eval(expression: str) -> Union[int, float]:
    """
    Safely evaluate a mathematical expression.
    
    Args:
        expression: Mathematical expression string
        
    Returns:
        Numerical result
        
    Raises:
        ValueError: If expression is invalid or contains unsafe operations
        ZeroDivisionError: If division by zero occurs
    """
    try:
        # Parse the expression into an AST
        tree = ast.parse(expression, mode='eval')
        
        # Evaluate using our safe evaluator
        evaluator = SafeExpressionEvaluator()
        result = evaluator.visit(tree.body)
        
        # Handle special float values
        if isinstance(result, float):
            if math.isnan(result):
                raise ValueError("Result is NaN (Not a Number)")
            if math.isinf(result):
                raise ValueError("Result is infinite")
        
        return result
        
    except SyntaxError as e:
        raise ValueError(f"Invalid expression syntax: {str(e)}")
    except (TypeError, AttributeError) as e:
        raise ValueError(f"Invalid expression: {str(e)}")


@tool_wrapper("calculator")
def calculate(expression: str) -> ToolResult:
    """
    Perform mathematical calculations with safe expression evaluation.
    
    Supports:
    - Basic arithmetic: +, -, *, /, **, %
    - Mathematical functions: sqrt, sin, cos, tan, log, exp, etc.
    - Constants: pi, e, tau
    - Parentheses for grouping
    
    Args:
        expression: Mathematical expression as a string
        
    Returns:
        ToolResult with the calculated result
        
    Examples:
        calculate("2 + 3 * 4")  # Returns 14
        calculate("sqrt(16)")   # Returns 4.0
        calculate("sin(pi/2)")  # Returns 1.0
        calculate("2**3")       # Returns 8
    """
    try:
        # Validate and sanitize input
        expression = validate_input(expression, str, "expression")
        expression = sanitize_string(expression, max_length=1000)
        
        if not expression:
            raise ValueError("Expression cannot be empty")
        
        # Log the calculation attempt
        logger.info(f"Calculating expression: {expression}")
        
        # Perform safe evaluation
        result = safe_eval(expression)
        
        # Format result appropriately
        if isinstance(result, float):
            # Round to reasonable precision for display
            if result.is_integer():
                result = int(result)
            else:
                result = round(result, 10)  # Avoid floating point precision issues
        
        return ToolResult(
            success=True,
            result=result,
            metadata={
                "expression": expression,
                "result_type": type(result).__name__,
                "is_integer": isinstance(result, int),
                "is_float": isinstance(result, float)
            }
        )
        
    except ZeroDivisionError as e:
        return ToolResult(
            success=False,
            result=None,
            error_message=f"Division by zero in expression '{expression}'"
        )
    
    except ValueError as e:
        return ToolResult(
            success=False,
            result=None,
            error_message=f"Invalid expression '{expression}': {str(e)}"
        )
    
    except Exception as e:
        return ToolResult(
            success=False,
            result=None,
            error_message=f"Calculation error for '{expression}': {str(e)}"
        )


def get_calculator_help() -> str:
    """Get help text for the calculator tool."""
    return """
Calculator Tool Help:

Supported Operations:
- Basic arithmetic: +, -, *, /, **, % (modulo)
- Parentheses for grouping: (2 + 3) * 4

Supported Functions:
- abs(x): Absolute value
- round(x): Round to nearest integer
- sqrt(x): Square root
- sin(x), cos(x), tan(x): Trigonometric functions (radians)
- asin(x), acos(x), atan(x): Inverse trigonometric functions
- log(x): Natural logarithm
- log10(x): Base-10 logarithm
- exp(x): e^x
- ceil(x), floor(x): Ceiling and floor functions
- factorial(x): Factorial (integers only)
- min(a, b, ...), max(a, b, ...): Minimum and maximum

Supported Constants:
- pi: π (3.14159...)
- e: Euler's number (2.71828...)
- tau: 2π (6.28318...)

Examples:
- calculate("2 + 3 * 4")      # 14
- calculate("sqrt(16)")       # 4.0
- calculate("sin(pi/2)")      # 1.0
- calculate("log(e)")         # 1.0
- calculate("2**3")           # 8
- calculate("factorial(5)")   # 120
"""
