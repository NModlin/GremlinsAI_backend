"""
gremlinsAI Python SDK

A comprehensive Python SDK for interacting with the gremlinsAI platform.
Provides easy-to-use interfaces for REST, GraphQL, and WebSocket APIs.
"""

from .client import GremlinsAIClient
from .exceptions import (
    GremlinsAIError,
    APIError,
    ValidationError,
    RateLimitError,
    AuthenticationError
)
from .models import (
    Conversation,
    Message,
    Document,
    Agent,
    Task,
    SystemHealth
)

__version__ = "1.0.0"
__author__ = "gremlinsAI Team"
__email__ = "support@gremlinsai.com"

__all__ = [
    "GremlinsAIClient",
    "GremlinsAIError",
    "APIError", 
    "ValidationError",
    "RateLimitError",
    "AuthenticationError",
    "Conversation",
    "Message",
    "Document",
    "Agent",
    "Task",
    "SystemHealth"
]
