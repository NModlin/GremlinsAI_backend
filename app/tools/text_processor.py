# app/tools/text_processor.py
"""
Text processing tool with various text manipulation and analysis functions.

Features:
- Text analysis (word count, character count, etc.)
- Text transformation (case conversion, cleaning)
- Text extraction (emails, URLs, numbers)
- Text formatting and manipulation
"""

import re
import logging
from typing import Dict, Any, List, Optional, Union
from collections import Counter
from .base_tool import tool_wrapper, ToolResult, validate_input, sanitize_string

logger = logging.getLogger(__name__)


def extract_emails(text: str) -> List[str]:
    """Extract email addresses from text."""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    return re.findall(email_pattern, text)


def extract_urls(text: str) -> List[str]:
    """Extract URLs from text."""
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    return re.findall(url_pattern, text)


def extract_numbers(text: str) -> List[float]:
    """Extract numbers from text."""
    number_pattern = r'-?\d+\.?\d*'
    matches = re.findall(number_pattern, text)
    numbers = []
    for match in matches:
        try:
            if '.' in match:
                numbers.append(float(match))
            else:
                numbers.append(float(int(match)))
        except ValueError:
            continue
    return numbers


def analyze_text(text: str) -> Dict[str, Any]:
    """Analyze text and return statistics."""
    words = text.split()
    sentences = re.split(r'[.!?]+', text)
    paragraphs = text.split('\n\n')
    
    # Word frequency
    word_freq = Counter(word.lower().strip('.,!?;:"()[]{}') for word in words if word.strip())
    
    return {
        'character_count': len(text),
        'character_count_no_spaces': len(text.replace(' ', '')),
        'word_count': len(words),
        'sentence_count': len([s for s in sentences if s.strip()]),
        'paragraph_count': len([p for p in paragraphs if p.strip()]),
        'average_word_length': sum(len(word) for word in words) / len(words) if words else 0,
        'most_common_words': word_freq.most_common(10),
        'unique_words': len(word_freq),
        'emails_found': extract_emails(text),
        'urls_found': extract_urls(text),
        'numbers_found': extract_numbers(text)
    }


@tool_wrapper("text_processor")
def process_text(text: str, operation: str, **kwargs) -> ToolResult:
    """
    Process text with various operations.
    
    Args:
        text: Input text to process
        operation: Operation to perform
        **kwargs: Additional parameters for specific operations
        
    Available Operations:
    - 'analyze': Analyze text statistics
    - 'uppercase': Convert to uppercase
    - 'lowercase': Convert to lowercase
    - 'title': Convert to title case
    - 'reverse': Reverse the text
    - 'clean': Clean and normalize text
    - 'extract_emails': Extract email addresses
    - 'extract_urls': Extract URLs
    - 'extract_numbers': Extract numbers
    - 'word_count': Count words
    - 'char_count': Count characters
    - 'remove_duplicates': Remove duplicate words
    - 'sort_words': Sort words alphabetically
    
    Returns:
        ToolResult with processed text or analysis
        
    Examples:
        process_text("Hello World", "uppercase")
        process_text("This is a test.", "analyze")
        process_text("Contact us at test@example.com", "extract_emails")
    """
    try:
        # Validate inputs
        text = validate_input(text, str, "text")
        operation = validate_input(operation, str, "operation")
        
        if not text:
            raise ValueError("Text cannot be empty")
        
        operation = operation.lower().strip()
        
        logger.info(f"Processing text with operation: {operation}")
        
        # Perform the requested operation
        if operation == 'analyze':
            result = analyze_text(text)
            
        elif operation == 'uppercase':
            result = text.upper()
            
        elif operation == 'lowercase':
            result = text.lower()
            
        elif operation == 'title':
            result = text.title()
            
        elif operation == 'reverse':
            result = text[::-1]
            
        elif operation == 'clean':
            # Remove extra whitespace, normalize line endings
            result = re.sub(r'\s+', ' ', text.strip())
            result = result.replace('\r\n', '\n').replace('\r', '\n')
            
        elif operation == 'extract_emails':
            result = extract_emails(text)
            
        elif operation == 'extract_urls':
            result = extract_urls(text)
            
        elif operation == 'extract_numbers':
            result = extract_numbers(text)
            
        elif operation == 'word_count':
            result = len(text.split())
            
        elif operation == 'char_count':
            include_spaces = kwargs.get('include_spaces', True)
            if include_spaces:
                result = len(text)
            else:
                result = len(text.replace(' ', ''))
                
        elif operation == 'remove_duplicates':
            words = text.split()
            unique_words = []
            seen = set()
            for word in words:
                if word.lower() not in seen:
                    unique_words.append(word)
                    seen.add(word.lower())
            result = ' '.join(unique_words)
            
        elif operation == 'sort_words':
            words = text.split()
            reverse_order = kwargs.get('reverse', False)
            sorted_words = sorted(words, key=str.lower, reverse=reverse_order)
            result = ' '.join(sorted_words)
            
        else:
            available_ops = [
                'analyze', 'uppercase', 'lowercase', 'title', 'reverse', 'clean',
                'extract_emails', 'extract_urls', 'extract_numbers', 'word_count',
                'char_count', 'remove_duplicates', 'sort_words'
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
                "input_length": len(text),
                "result_type": type(result).__name__,
                "kwargs": kwargs
            }
        )
        
    except Exception as e:
        error_msg = f"Text processing failed for operation '{operation}': {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        return ToolResult(
            success=False,
            result=None,
            error_message=error_msg
        )


def get_text_processor_help() -> str:
    """Get help text for the text processor tool."""
    return """
Text Processor Tool Help:

Usage:
- process_text("your text", "operation")
- process_text("text", "operation", param=value)

Available Operations:

Analysis:
- 'analyze': Complete text analysis (word count, sentences, etc.)
- 'word_count': Count words in text
- 'char_count': Count characters (include_spaces=True/False)

Transformation:
- 'uppercase': Convert to UPPERCASE
- 'lowercase': Convert to lowercase
- 'title': Convert To Title Case
- 'reverse': Reverse the text
- 'clean': Clean and normalize whitespace

Extraction:
- 'extract_emails': Find email addresses
- 'extract_urls': Find URLs
- 'extract_numbers': Find numbers

Manipulation:
- 'remove_duplicates': Remove duplicate words
- 'sort_words': Sort words alphabetically (reverse=True/False)

Examples:
- process_text("Hello World", "uppercase")  # "HELLO WORLD"
- process_text("This is a test.", "analyze")  # Full analysis
- process_text("Contact test@example.com", "extract_emails")  # ["test@example.com"]
- process_text("apple banana apple", "remove_duplicates")  # "apple banana"
- process_text("zebra apple banana", "sort_words")  # "apple banana zebra"

Note: All operations preserve the original text structure where applicable.
"""
