# app/tools/hash_generator.py
"""
Hash generation tool for creating various types of hashes.
"""

import hashlib
import hmac
import logging
from typing import Optional
from .base_tool import tool_wrapper, ToolResult, validate_input, sanitize_string

logger = logging.getLogger(__name__)


@tool_wrapper("hash_generator")
def generate_hash(text: str, algorithm: str = "sha256", key: Optional[str] = None) -> ToolResult:
    """
    Generate hash for given text using specified algorithm.
    
    Args:
        text: Text to hash
        algorithm: Hash algorithm (md5, sha1, sha256, sha512, blake2b, blake2s)
        key: Optional key for HMAC (if provided, generates HMAC instead)
        
    Returns:
        ToolResult with generated hash
        
    Examples:
        generate_hash("hello world", "sha256")
        generate_hash("message", "sha256", key="secret")
    """
    try:
        text = validate_input(text, str, "text")
        algorithm = validate_input(algorithm, str, "algorithm")
        
        text = sanitize_string(text, max_length=100000)
        algorithm = algorithm.lower().strip()
        
        # Available algorithms
        available_algorithms = {
            'md5': hashlib.md5,
            'sha1': hashlib.sha1,
            'sha256': hashlib.sha256,
            'sha512': hashlib.sha512,
            'blake2b': hashlib.blake2b,
            'blake2s': hashlib.blake2s
        }
        
        if algorithm not in available_algorithms:
            return ToolResult(
                success=False,
                result=None,
                error_message=f"Unsupported algorithm '{algorithm}'. Available: {', '.join(available_algorithms.keys())}"
            )
        
        text_bytes = text.encode('utf-8')
        
        if key:
            # Generate HMAC
            key_bytes = key.encode('utf-8')
            hash_obj = hmac.new(key_bytes, text_bytes, available_algorithms[algorithm])
            hash_hex = hash_obj.hexdigest()
            hash_type = f"HMAC-{algorithm.upper()}"
        else:
            # Generate regular hash
            hash_obj = available_algorithms[algorithm](text_bytes)
            hash_hex = hash_obj.hexdigest()
            hash_type = algorithm.upper()
        
        return ToolResult(
            success=True,
            result=hash_hex,
            metadata={
                "algorithm": algorithm,
                "hash_type": hash_type,
                "input_length": len(text),
                "output_length": len(hash_hex),
                "uses_key": bool(key)
            }
        )
        
    except Exception as e:
        error_msg = f"Hash generation failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        return ToolResult(
            success=False,
            result=None,
            error_message=error_msg
        )


def get_hash_generator_help() -> str:
    """Get help text for the hash generator tool."""
    return """
Hash Generator Tool Help:

Usage:
- generate_hash("text", "algorithm")
- generate_hash("text", "algorithm", key="secret")

Available Algorithms:
- 'md5': MD5 hash (128-bit)
- 'sha1': SHA-1 hash (160-bit)
- 'sha256': SHA-256 hash (256-bit) - Recommended
- 'sha512': SHA-512 hash (512-bit)
- 'blake2b': BLAKE2b hash (512-bit)
- 'blake2s': BLAKE2s hash (256-bit)

Features:
- Regular hash generation
- HMAC generation (with key parameter)
- Hexadecimal output format

Examples:
- generate_hash("hello world", "sha256")
- generate_hash("secret message", "sha256", key="my_secret_key")
- generate_hash("data", "md5")

Security Notes:
- SHA-256 is recommended for most use cases
- MD5 and SHA-1 are deprecated for security purposes
- Use HMAC for message authentication
- BLAKE2 algorithms are modern and fast

Note: All hashes are returned in lowercase hexadecimal format.
"""
