"""
Weaviate Schema Implementation for GremlinsAI

This module defines the comprehensive Weaviate schema that replaces SQLite tables
with vector-enabled classes for conversations, documents, and agent interactions.
The schema supports all current SQLite data plus vector embeddings for enhanced
semantic search and retrieval capabilities.
"""

import logging
from typing import Dict, List, Any, Optional
import weaviate
from weaviate.classes.config import Configure, Property, DataType
from weaviate.classes.init import Auth
from weaviate.exceptions import WeaviateBaseError

logger = logging.getLogger(__name__)


class WeaviateSchemaManager:
    """Manages Weaviate schema creation and migration for GremlinsAI."""
    
    def __init__(self, client: weaviate.WeaviateClient):
        """Initialize schema manager with Weaviate client."""
        self.client = client
        
    def create_weaviate_schema(self) -> bool:
        """
        Create comprehensive Weaviate schema for GremlinsAI.
        
        Returns:
            bool: True if schema creation successful, False otherwise
        """
        try:
            logger.info("Creating Weaviate schema for GremlinsAI...")
            
            # Create all schema classes
            self._create_conversation_class()
            self._create_message_class()
            self._create_document_class()
            self._create_document_chunk_class()
            self._create_agent_interaction_class()
            self._create_multimodal_content_class()
            
            logger.info("Weaviate schema creation completed successfully")
            return True
            
        except WeaviateBaseError as e:
            logger.error(f"Weaviate error during schema creation: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during schema creation: {e}")
            return False
    
    def _create_conversation_class(self) -> None:
        """Create Conversation class for chat conversations with full context."""
        logger.info("Creating Conversation class...")
        
        self.client.collections.create(
            name="Conversation",
            description="Chat conversation with full context and metadata",
            properties=[
                Property(
                    name="conversationId",
                    data_type=DataType.TEXT,
                    description="Unique conversation identifier"
                ),
                Property(
                    name="title",
                    data_type=DataType.TEXT,
                    description="Conversation title"
                ),
                Property(
                    name="userId",
                    data_type=DataType.TEXT,
                    description="User identifier"
                ),
                Property(
                    name="createdAt",
                    data_type=DataType.DATE,
                    description="Creation timestamp"
                ),
                Property(
                    name="updatedAt",
                    data_type=DataType.DATE,
                    description="Last update timestamp"
                ),
                Property(
                    name="isActive",
                    data_type=DataType.BOOL,
                    description="Active status"
                ),
                Property(
                    name="contextVector",
                    data_type=DataType.NUMBER_ARRAY,
                    description="Conversation context embedding"
                ),
                Property(
                    name="metadata",
                    data_type=DataType.OBJECT,
                    description="Additional conversation metadata"
                )
            ],
            vectorizer_config=Configure.Vectorizer.text2vec_openai(
                vectorize_collection_name=False
            )
        )
    
    def _create_message_class(self) -> None:
        """Create Message class for individual messages within conversations."""
        logger.info("Creating Message class...")
        
        self.client.collections.create(
            name="Message",
            description="Individual message within a conversation",
            properties=[
                Property(
                    name="messageId",
                    data_type=DataType.TEXT,
                    description="Unique message identifier"
                ),
                Property(
                    name="conversationId",
                    data_type=DataType.TEXT,
                    description="Parent conversation ID"
                ),
                Property(
                    name="role",
                    data_type=DataType.TEXT,
                    description="Message role: user, assistant, system"
                ),
                Property(
                    name="content",
                    data_type=DataType.TEXT,
                    description="Message content"
                ),
                Property(
                    name="createdAt",
                    data_type=DataType.DATE,
                    description="Message timestamp"
                ),
                Property(
                    name="toolCalls",
                    data_type=DataType.TEXT,
                    description="JSON string of tool calls"
                ),
                Property(
                    name="extraData",
                    data_type=DataType.OBJECT,
                    description="Additional message metadata"
                ),
                Property(
                    name="embedding",
                    data_type=DataType.NUMBER_ARRAY,
                    description="Message content embedding"
                )
            ],
            vectorizer_config=Configure.Vectorizer.text2vec_transformers(
                vectorize_collection_name=False
            )
        )
    
    def _create_document_class(self) -> None:
        """Create Document class for RAG and knowledge base documents."""
        logger.info("Creating Document class...")
        
        self.client.collections.create(
            name="Document",
            description="Documents for RAG and knowledge base",
            properties=[
                Property(
                    name="documentId",
                    data_type=DataType.TEXT,
                    description="Unique document identifier"
                ),
                Property(
                    name="title",
                    data_type=DataType.TEXT,
                    description="Document title"
                ),
                Property(
                    name="content",
                    data_type=DataType.TEXT,
                    description="Full document content"
                ),
                Property(
                    name="contentType",
                    data_type=DataType.TEXT,
                    description="MIME type"
                ),
                Property(
                    name="filePath",
                    data_type=DataType.TEXT,
                    description="Original file path"
                ),
                Property(
                    name="fileSize",
                    data_type=DataType.INT,
                    description="File size in bytes"
                ),
                Property(
                    name="tags",
                    data_type=DataType.TEXT_ARRAY,
                    description="Document tags"
                ),
                Property(
                    name="createdAt",
                    data_type=DataType.DATE,
                    description="Creation timestamp"
                ),
                Property(
                    name="updatedAt",
                    data_type=DataType.DATE,
                    description="Last update timestamp"
                ),
                Property(
                    name="isActive",
                    data_type=DataType.BOOL,
                    description="Active status"
                ),
                Property(
                    name="metadata",
                    data_type=DataType.OBJECT,
                    description="Document metadata"
                ),
                Property(
                    name="embedding",
                    data_type=DataType.NUMBER_ARRAY,
                    description="Document embedding"
                )
            ],
            vectorizer_config=Configure.Vectorizer.text2vec_transformers(
                vectorize_collection_name=False
            )
        )
    
    def _create_document_chunk_class(self) -> None:
        """Create DocumentChunk class for efficient document retrieval."""
        logger.info("Creating DocumentChunk class...")
        
        self.client.collections.create(
            name="DocumentChunk",
            description="Document chunks for efficient retrieval",
            properties=[
                Property(
                    name="chunkId",
                    data_type=DataType.TEXT,
                    description="Unique chunk identifier"
                ),
                Property(
                    name="documentId",
                    data_type=DataType.TEXT,
                    description="Parent document ID"
                ),
                Property(
                    name="content",
                    data_type=DataType.TEXT,
                    description="Chunk content"
                ),
                Property(
                    name="chunkIndex",
                    data_type=DataType.INT,
                    description="Chunk position in document"
                ),
                Property(
                    name="startOffset",
                    data_type=DataType.INT,
                    description="Start character offset"
                ),
                Property(
                    name="endOffset",
                    data_type=DataType.INT,
                    description="End character offset"
                ),
                Property(
                    name="metadata",
                    data_type=DataType.OBJECT,
                    description="Chunk metadata"
                ),
                Property(
                    name="embedding",
                    data_type=DataType.NUMBER_ARRAY,
                    description="Chunk embedding"
                )
            ],
            vectorizer_config=Configure.Vectorizer.text2vec_transformers(
                vectorize_collection_name=False
            )
        )

    def _create_agent_interaction_class(self) -> None:
        """Create AgentInteraction class for agent interactions and performance tracking."""
        logger.info("Creating AgentInteraction class...")

        self.client.collections.create(
            name="AgentInteraction",
            description="Agent interactions and performance tracking",
            properties=[
                Property(
                    name="interactionId",
                    data_type=DataType.TEXT,
                    description="Unique interaction identifier"
                ),
                Property(
                    name="agentType",
                    data_type=DataType.TEXT,
                    description="Type of agent"
                ),
                Property(
                    name="query",
                    data_type=DataType.TEXT,
                    description="Input query"
                ),
                Property(
                    name="response",
                    data_type=DataType.TEXT,
                    description="Agent response"
                ),
                Property(
                    name="toolsUsed",
                    data_type=DataType.TEXT_ARRAY,
                    description="Tools utilized"
                ),
                Property(
                    name="executionTimeMs",
                    data_type=DataType.NUMBER,
                    description="Execution time"
                ),
                Property(
                    name="tokensUsed",
                    data_type=DataType.INT,
                    description="Tokens consumed"
                ),
                Property(
                    name="conversationId",
                    data_type=DataType.TEXT,
                    description="Related conversation"
                ),
                Property(
                    name="createdAt",
                    data_type=DataType.DATE,
                    description="Interaction timestamp"
                ),
                Property(
                    name="metadata",
                    data_type=DataType.OBJECT,
                    description="Additional metadata"
                ),
                Property(
                    name="embedding",
                    data_type=DataType.NUMBER_ARRAY,
                    description="Interaction embedding"
                )
            ],
            vectorizer_config=Configure.Vectorizer.text2vec_transformers(
                vectorize_collection_name=False
            )
        )

    def _create_multimodal_content_class(self) -> None:
        """Create MultiModalContent class for multimodal content with cross-modal embeddings."""
        logger.info("Creating MultiModalContent class...")

        self.client.collections.create(
            name="MultiModalContent",
            description="Multimodal content with cross-modal embeddings",
            properties=[
                Property(
                    name="contentId",
                    data_type=DataType.TEXT,
                    description="Unique content identifier"
                ),
                Property(
                    name="mediaType",
                    data_type=DataType.TEXT,
                    description="Media type: audio, video, image"
                ),
                Property(
                    name="filename",
                    data_type=DataType.TEXT,
                    description="Original filename"
                ),
                Property(
                    name="fileSize",
                    data_type=DataType.INT,
                    description="File size in bytes"
                ),
                Property(
                    name="contentHash",
                    data_type=DataType.TEXT,
                    description="SHA-256 hash"
                ),
                Property(
                    name="storagePath",
                    data_type=DataType.TEXT,
                    description="Storage location"
                ),
                Property(
                    name="processingStatus",
                    data_type=DataType.TEXT,
                    description="Processing status"
                ),
                Property(
                    name="processingResult",
                    data_type=DataType.OBJECT,
                    description="Processing results"
                ),
                Property(
                    name="conversationId",
                    data_type=DataType.TEXT,
                    description="Related conversation"
                ),
                Property(
                    name="createdAt",
                    data_type=DataType.DATE,
                    description="Creation timestamp"
                ),
                Property(
                    name="updatedAt",
                    data_type=DataType.DATE,
                    description="Update timestamp"
                ),
                Property(
                    name="textContent",
                    data_type=DataType.TEXT,
                    description="Extracted text content"
                ),
                Property(
                    name="visualEmbedding",
                    data_type=DataType.NUMBER_ARRAY,
                    description="CLIP visual embedding"
                ),
                Property(
                    name="textEmbedding",
                    data_type=DataType.NUMBER_ARRAY,
                    description="Text embedding"
                )
            ],
            vectorizer_config=Configure.Vectorizer.text2vec_transformers(
                vectorize_collection_name=False
            )
        )

    def delete_schema(self) -> bool:
        """
        Delete all schema classes (for testing/cleanup).

        Returns:
            bool: True if deletion successful, False otherwise
        """
        try:
            logger.info("Deleting Weaviate schema...")

            class_names = [
                "Conversation",
                "Message",
                "Document",
                "DocumentChunk",
                "AgentInteraction",
                "MultiModalContent"
            ]

            for class_name in class_names:
                try:
                    self.client.collections.delete(class_name)
                    logger.info(f"Deleted class: {class_name}")
                except Exception as e:
                    logger.warning(f"Could not delete class {class_name}: {e}")

            logger.info("Schema deletion completed")
            return True

        except Exception as e:
            logger.error(f"Error during schema deletion: {e}")
            return False

    def get_schema_info(self) -> Dict[str, Any]:
        """
        Get information about current schema.

        Returns:
            Dict containing schema information
        """
        try:
            schema_info = {}

            class_names = [
                "Conversation",
                "Message",
                "Document",
                "DocumentChunk",
                "AgentInteraction",
                "MultiModalContent"
            ]

            for class_name in class_names:
                try:
                    collection = self.client.collections.get(class_name)
                    config = collection.config.get()
                    schema_info[class_name] = {
                        "exists": True,
                        "properties": len(config.properties) if config.properties else 0,
                        "vectorizer": config.vectorizer_config.__class__.__name__ if config.vectorizer_config else None
                    }
                except Exception:
                    schema_info[class_name] = {"exists": False}

            return schema_info

        except Exception as e:
            logger.error(f"Error getting schema info: {e}")
            return {}


def create_weaviate_schema(client: weaviate.WeaviateClient) -> bool:
    """
    Convenience function to create Weaviate schema.

    Args:
        client: Weaviate client instance

    Returns:
        bool: True if schema creation successful, False otherwise
    """
    schema_manager = WeaviateSchemaManager(client)
    return schema_manager.create_weaviate_schema()
