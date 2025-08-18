# tests/unit/test_api_schemas.py
"""
Unit tests for API schemas and validation.

Tests Pydantic models and validation logic without external dependencies.
"""

import pytest
from datetime import datetime
from typing import Dict, Any, List
from pydantic import ValidationError

from app.api.v1.schemas.documents import (
    DocumentCreate,
    DocumentResponse,
    SemanticSearchRequest,
    RAGRequest,
    QuerySuggestionsRequest,
    SearchType
)
from app.api.v1.schemas.chat_history import (
    AgentConversationRequest,
    AgentConversationResponse,
    MessageRole,
    ConversationCreate
)


class TestDocumentSchemas:
    """Test document-related schemas."""

    def test_document_create_valid(self):
        """Test valid document creation schema."""
        doc_data = {
            "title": "Test Document",
            "content": "This is test content for the document.",
            "content_type": "text/plain",
            "tags": ["test", "document"],
            "doc_metadata": {"author": "test_user", "version": "1.0"}
        }

        doc = DocumentCreate(**doc_data)

        assert doc.title == "Test Document"
        assert doc.content == "This is test content for the document."
        assert doc.content_type == "text/plain"
        assert "test" in doc.tags
        assert doc.doc_metadata["author"] == "test_user"

    def test_document_create_minimal(self):
        """Test document creation with minimal required fields."""
        doc_data = {
            "title": "Minimal Document",
            "content": "Minimal content",
            "content_type": "text/plain"
        }

        doc = DocumentCreate(**doc_data)

        assert doc.title == "Minimal Document"
        assert doc.content == "Minimal content"
        assert doc.tags is None  # Optional field
        assert doc.doc_metadata is None  # Optional field

    def test_document_create_validation_errors(self):
        """Test document creation validation errors."""
        # Empty title
        with pytest.raises(ValidationError) as exc_info:
            DocumentCreate(title="", content="content", content_type="text/plain")
        
        errors = exc_info.value.errors()
        assert any(error["type"] == "value_error" for error in errors)
        
        # Empty content
        with pytest.raises(ValidationError):
            DocumentCreate(title="title", content="", content_type="text/plain")
        
        # Invalid content type
        with pytest.raises(ValidationError):
            DocumentCreate(title="title", content="content", content_type="invalid/type")

    def test_document_response_schema(self):
        """Test document response schema."""
        response_data = {
            "id": "doc-123",
            "title": "Response Document",
            "content": "Response content",
            "content_type": "text/markdown",
            "tags": ["response", "test"],
            "metadata": {"created_by": "system"},
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "chunk_count": 5,
            "word_count": 150
        }
        
        doc_response = DocumentResponse(**response_data)
        
        assert doc_response.id == "doc-123"
        assert doc_response.title == "Response Document"
        assert doc_response.chunk_count == 5
        assert doc_response.word_count == 150
        assert isinstance(doc_response.created_at, datetime)

    def test_semantic_search_request(self):
        """Test semantic search request schema."""
        search_data = {
            "query": "What is artificial intelligence?",
            "limit": 10,
            "score_threshold": 0.8,
            "search_type": SearchType.CHUNKS,
            "filter_conditions": {"content_type": "text/markdown"}
        }

        search_request = SemanticSearchRequest(**search_data)

        assert search_request.query == "What is artificial intelligence?"
        assert search_request.limit == 10
        assert search_request.score_threshold == 0.8
        assert search_request.search_type == SearchType.CHUNKS
        assert search_request.filter_conditions["content_type"] == "text/markdown"

    def test_semantic_search_defaults(self):
        """Test semantic search request with default values."""
        search_data = {"query": "test query"}

        search_request = SemanticSearchRequest(**search_data)

        assert search_request.query == "test query"
        assert search_request.limit == 5  # Default
        assert search_request.score_threshold == 0.7  # Default
        assert search_request.search_type == SearchType.CHUNKS  # Default
        assert search_request.filter_conditions is None  # Default

    def test_rag_request_schema(self):
        """Test RAG request schema."""
        rag_data = {
            "query": "Explain machine learning concepts",
            "search_limit": 5,
            "score_threshold": 0.75,
            "use_multi_agent": True,
            "search_type": SearchType.CHUNKS,
            "save_conversation": False
        }

        rag_request = RAGRequest(**rag_data)

        assert rag_request.query == "Explain machine learning concepts"
        assert rag_request.search_limit == 5
        assert rag_request.score_threshold == 0.75
        assert rag_request.use_multi_agent is True
        assert rag_request.search_type == SearchType.CHUNKS
        assert rag_request.save_conversation is False

    def test_query_suggestions_request(self):
        """Test query suggestions request schema."""
        suggestions_data = {
            "partial_query": "What is",
            "limit": 5,
            "context_filters": {"tags": ["documentation"]}
        }
        
        suggestions_request = QuerySuggestionsRequest(**suggestions_data)
        
        assert suggestions_request.partial_query == "What is"
        assert suggestions_request.limit == 5
        assert suggestions_request.context_filters["tags"] == ["documentation"]


class TestChatHistorySchemas:
    """Test chat history and conversation schemas."""

    def test_conversation_create_schema(self):
        """Test conversation creation schema."""
        conv_data = {
            "title": "AI Discussion",
            "initial_message": "Let's talk about AI"
        }

        conversation = ConversationCreate(**conv_data)

        assert conversation.title == "AI Discussion"
        assert conversation.initial_message == "Let's talk about AI"

    def test_agent_conversation_request(self):
        """Test agent conversation request schema."""
        request_data = {
            "input": "Hello, can you help me with AI concepts?",
            "conversation_id": "conv-456",
            "save_conversation": True
        }

        conv_request = AgentConversationRequest(**request_data)

        assert conv_request.input == "Hello, can you help me with AI concepts?"
        assert conv_request.conversation_id == "conv-456"
        assert conv_request.save_conversation is True

    def test_agent_conversation_request_minimal(self):
        """Test agent conversation request with minimal fields."""
        request_data = {
            "input": "Simple question"
        }

        conv_request = AgentConversationRequest(**request_data)

        assert conv_request.input == "Simple question"
        assert conv_request.conversation_id is None  # Optional
        assert conv_request.save_conversation is True  # Default

    def test_agent_conversation_response(self):
        """Test agent conversation response schema."""
        response_data = {
            "output": "I'd be happy to help you with AI concepts!",
            "conversation_id": "conv-456",
            "message_id": "msg-789",
            "context_used": True
        }

        conv_response = AgentConversationResponse(**response_data)

        assert conv_response.output == "I'd be happy to help you with AI concepts!"
        assert conv_response.conversation_id == "conv-456"
        assert conv_response.message_id == "msg-789"
        assert conv_response.context_used is True

    def test_message_role_enum(self):
        """Test message role enumeration."""
        roles = list(MessageRole)

        assert MessageRole.USER in roles
        assert MessageRole.ASSISTANT in roles
        assert MessageRole.SYSTEM in roles

    def test_conversation_validation_errors(self):
        """Test conversation schema validation errors."""
        # Empty input
        with pytest.raises(ValidationError):
            AgentConversationRequest(input="")





class TestSchemaIntegration:
    """Test schema integration and edge cases."""

    def test_optional_fields_handling(self):
        """Test handling of optional fields in schemas."""
        # Document with minimal fields
        doc_data = {
            "title": "Test",
            "content": "Content",
            "content_type": "text/plain"
        }

        doc = DocumentCreate(**doc_data)
        assert doc.tags is None
        assert doc.doc_metadata is None

        # Conversation with minimal fields
        conv_data = {
            "input": "Hello"
        }

        conv = AgentConversationRequest(**conv_data)
        assert conv.conversation_id is None
        assert conv.save_conversation is True  # Default

    def test_schema_serialization(self):
        """Test schema serialization to dict/JSON."""
        doc_data = {
            "title": "Serialization Test",
            "content": "Test content",
            "content_type": "text/plain",
            "tags": ["test"],
            "doc_metadata": {"key": "value"}
        }

        doc = DocumentCreate(**doc_data)
        serialized = doc.model_dump()

        assert serialized["title"] == "Serialization Test"
        assert serialized["tags"] == ["test"]
        assert serialized["doc_metadata"]["key"] == "value"

        # Test JSON serialization
        json_str = doc.model_dump_json()
        assert isinstance(json_str, str)
        assert "Serialization Test" in json_str

    def test_enum_validation(self):
        """Test enum field validation."""
        # Test valid search type
        search_data = {
            "query": "test",
            "search_type": SearchType.DOCUMENTS
        }

        search_request = SemanticSearchRequest(**search_data)
        assert search_request.search_type == SearchType.DOCUMENTS

        # Test invalid search type should raise validation error
        with pytest.raises(ValidationError):
            SemanticSearchRequest(query="test", search_type="invalid_type")


if __name__ == "__main__":
    pytest.main([__file__])
