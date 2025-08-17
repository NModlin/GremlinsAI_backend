"""
Unit tests for Weaviate schema implementation.

Tests verify that the create_weaviate_schema function correctly defines
all six classes (Conversation, Message, Document, DocumentChunk, 
AgentInteraction, MultiModalContent) with proper properties, data types,
vectorizers, and module configurations.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from weaviate.classes.config import Configure, Property, DataType, Tokenization
from weaviate.exceptions import WeaviateBaseError

from app.database.weaviate_schema import WeaviateSchemaManager, create_weaviate_schema


class TestWeaviateSchemaManager:
    """Test cases for WeaviateSchemaManager class."""
    
    @pytest.fixture
    def mock_client(self):
        """Create a mock Weaviate client."""
        client = Mock()
        client.collections = Mock()
        client.collections.create = Mock()
        client.collections.delete = Mock()
        client.collections.get = Mock()
        return client
    
    @pytest.fixture
    def schema_manager(self, mock_client):
        """Create WeaviateSchemaManager instance with mock client."""
        return WeaviateSchemaManager(mock_client)
    
    def test_create_weaviate_schema_success(self, schema_manager, mock_client):
        """Test successful schema creation."""
        # Act
        result = schema_manager.create_weaviate_schema()
        
        # Assert
        assert result is True
        assert mock_client.collections.create.call_count == 6
        
        # Verify all expected classes were created
        created_classes = [call.kwargs['name'] for call in mock_client.collections.create.call_args_list]
        expected_classes = ["Conversation", "Message", "Document", "DocumentChunk", "AgentInteraction", "MultiModalContent"]
        
        for expected_class in expected_classes:
            assert expected_class in created_classes
    
    def test_create_weaviate_schema_weaviate_error(self, schema_manager, mock_client):
        """Test schema creation with Weaviate error."""
        # Arrange
        mock_client.collections.create.side_effect = WeaviateBaseError("Connection failed")
        
        # Act
        result = schema_manager.create_weaviate_schema()
        
        # Assert
        assert result is False
    
    def test_create_weaviate_schema_unexpected_error(self, schema_manager, mock_client):
        """Test schema creation with unexpected error."""
        # Arrange
        mock_client.collections.create.side_effect = Exception("Unexpected error")
        
        # Act
        result = schema_manager.create_weaviate_schema()
        
        # Assert
        assert result is False
    
    def test_conversation_class_creation(self, schema_manager, mock_client):
        """Test Conversation class creation with correct properties."""
        # Act
        schema_manager._create_conversation_class()
        
        # Assert
        mock_client.collections.create.assert_called_once()
        call_args = mock_client.collections.create.call_args
        
        assert call_args.kwargs['name'] == "Conversation"
        assert call_args.kwargs['description'] == "Chat conversation with full context and metadata"
        
        # Verify properties
        properties = call_args.kwargs['properties']
        property_names = [prop.name for prop in properties]
        
        expected_properties = [
            "conversationId", "title", "userId", "createdAt", 
            "updatedAt", "isActive", "contextVector", "metadata"
        ]
        
        for expected_prop in expected_properties:
            assert expected_prop in property_names
        
        # Verify vectorizer configuration
        vectorizer_config = call_args.kwargs['vectorizer_config']
        assert vectorizer_config is not None
    
    def test_message_class_creation(self, schema_manager, mock_client):
        """Test Message class creation with correct properties."""
        # Act
        schema_manager._create_message_class()
        
        # Assert
        mock_client.collections.create.assert_called_once()
        call_args = mock_client.collections.create.call_args
        
        assert call_args.kwargs['name'] == "Message"
        assert call_args.kwargs['description'] == "Individual message within a conversation"
        
        # Verify properties
        properties = call_args.kwargs['properties']
        property_names = [prop.name for prop in properties]
        
        expected_properties = [
            "messageId", "conversationId", "role", "content",
            "createdAt", "toolCalls", "extraData", "embedding"
        ]
        
        for expected_prop in expected_properties:
            assert expected_prop in property_names
    
    def test_document_class_creation(self, schema_manager, mock_client):
        """Test Document class creation with correct properties."""
        # Act
        schema_manager._create_document_class()
        
        # Assert
        mock_client.collections.create.assert_called_once()
        call_args = mock_client.collections.create.call_args
        
        assert call_args.kwargs['name'] == "Document"
        assert call_args.kwargs['description'] == "Documents for RAG and knowledge base"
        
        # Verify properties
        properties = call_args.kwargs['properties']
        property_names = [prop.name for prop in properties]
        
        expected_properties = [
            "documentId", "title", "content", "contentType", "filePath",
            "fileSize", "tags", "createdAt", "updatedAt", "isActive",
            "metadata", "embedding"
        ]
        
        for expected_prop in expected_properties:
            assert expected_prop in property_names
    
    def test_document_chunk_class_creation(self, schema_manager, mock_client):
        """Test DocumentChunk class creation with correct properties."""
        # Act
        schema_manager._create_document_chunk_class()
        
        # Assert
        mock_client.collections.create.assert_called_once()
        call_args = mock_client.collections.create.call_args
        
        assert call_args.kwargs['name'] == "DocumentChunk"
        assert call_args.kwargs['description'] == "Document chunks for efficient retrieval"
        
        # Verify properties
        properties = call_args.kwargs['properties']
        property_names = [prop.name for prop in properties]
        
        expected_properties = [
            "chunkId", "documentId", "content", "chunkIndex",
            "startOffset", "endOffset", "metadata", "embedding"
        ]
        
        for expected_prop in expected_properties:
            assert expected_prop in property_names
    
    def test_agent_interaction_class_creation(self, schema_manager, mock_client):
        """Test AgentInteraction class creation with correct properties."""
        # Act
        schema_manager._create_agent_interaction_class()
        
        # Assert
        mock_client.collections.create.assert_called_once()
        call_args = mock_client.collections.create.call_args
        
        assert call_args.kwargs['name'] == "AgentInteraction"
        assert call_args.kwargs['description'] == "Agent interactions and performance tracking"
        
        # Verify properties
        properties = call_args.kwargs['properties']
        property_names = [prop.name for prop in properties]
        
        expected_properties = [
            "interactionId", "agentType", "query", "response", "toolsUsed",
            "executionTimeMs", "tokensUsed", "conversationId", "createdAt",
            "metadata", "embedding"
        ]
        
        for expected_prop in expected_properties:
            assert expected_prop in property_names
    
    def test_multimodal_content_class_creation(self, schema_manager, mock_client):
        """Test MultiModalContent class creation with correct properties."""
        # Act
        schema_manager._create_multimodal_content_class()
        
        # Assert
        mock_client.collections.create.assert_called_once()
        call_args = mock_client.collections.create.call_args
        
        assert call_args.kwargs['name'] == "MultiModalContent"
        assert call_args.kwargs['description'] == "Multimodal content with cross-modal embeddings"
        
        # Verify properties
        properties = call_args.kwargs['properties']
        property_names = [prop.name for prop in properties]
        
        expected_properties = [
            "contentId", "mediaType", "filename", "fileSize", "contentHash",
            "storagePath", "processingStatus", "processingResult", "conversationId",
            "createdAt", "updatedAt", "textContent", "visualEmbedding", "textEmbedding"
        ]
        
        for expected_prop in expected_properties:
            assert expected_prop in property_names
    
    def test_delete_schema_success(self, schema_manager, mock_client):
        """Test successful schema deletion."""
        # Act
        result = schema_manager.delete_schema()
        
        # Assert
        assert result is True
        assert mock_client.collections.delete.call_count == 6
        
        # Verify all classes were deleted
        deleted_classes = [call.args[0] for call in mock_client.collections.delete.call_args_list]
        expected_classes = ["Conversation", "Message", "Document", "DocumentChunk", "AgentInteraction", "MultiModalContent"]
        
        for expected_class in expected_classes:
            assert expected_class in deleted_classes
    
    def test_delete_schema_with_errors(self, schema_manager, mock_client):
        """Test schema deletion with some errors (should continue and return True)."""
        # Arrange
        mock_client.collections.delete.side_effect = [None, Exception("Error"), None, None, None, None]
        
        # Act
        result = schema_manager.delete_schema()
        
        # Assert
        assert result is True  # Should still return True even with some errors
        assert mock_client.collections.delete.call_count == 6
    
    def test_get_schema_info_success(self, schema_manager, mock_client):
        """Test getting schema information successfully."""
        # Arrange
        mock_collection = Mock()
        mock_config = Mock()
        mock_config.properties = [Mock(), Mock(), Mock()]  # 3 properties
        mock_config.vectorizer_config = Mock()
        mock_config.vectorizer_config.__class__.__name__ = "Text2VecTransformers"
        mock_collection.config.get.return_value = mock_config
        mock_client.collections.get.return_value = mock_collection
        
        # Act
        result = schema_manager.get_schema_info()
        
        # Assert
        assert isinstance(result, dict)
        assert len(result) == 6
        
        for class_name in ["Conversation", "Message", "Document", "DocumentChunk", "AgentInteraction", "MultiModalContent"]:
            assert class_name in result
            assert result[class_name]["exists"] is True
            assert result[class_name]["properties"] == 3
            assert result[class_name]["vectorizer"] == "Text2VecTransformers"
    
    def test_get_schema_info_missing_classes(self, schema_manager, mock_client):
        """Test getting schema information when classes don't exist."""
        # Arrange
        mock_client.collections.get.side_effect = Exception("Class not found")
        
        # Act
        result = schema_manager.get_schema_info()
        
        # Assert
        assert isinstance(result, dict)
        assert len(result) == 6
        
        for class_name in ["Conversation", "Message", "Document", "DocumentChunk", "AgentInteraction", "MultiModalContent"]:
            assert class_name in result
            assert result[class_name]["exists"] is False


class TestCreateWeaviateSchemaFunction:
    """Test cases for the create_weaviate_schema convenience function."""
    
    def test_create_weaviate_schema_function(self):
        """Test the convenience function creates schema manager and calls create_weaviate_schema."""
        # Arrange
        mock_client = Mock()
        
        with patch('app.database.weaviate_schema.WeaviateSchemaManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager.create_weaviate_schema.return_value = True
            mock_manager_class.return_value = mock_manager
            
            # Act
            result = create_weaviate_schema(mock_client)
            
            # Assert
            assert result is True
            mock_manager_class.assert_called_once_with(mock_client)
            mock_manager.create_weaviate_schema.assert_called_once()
