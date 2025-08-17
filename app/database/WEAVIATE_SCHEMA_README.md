# Weaviate Schema Implementation

## Overview

This module implements a comprehensive Weaviate schema that replaces SQLite tables with vector-enabled classes for conversations, documents, and agent interactions. The schema supports all current SQLite data plus vector embeddings for enhanced semantic search and retrieval capabilities.

## Schema Classes

### 1. Conversation
**Purpose**: Chat conversations with full context and metadata
- **Properties**: 8 total
  - `conversationId` (TEXT): Unique conversation identifier
  - `title` (TEXT): Conversation title
  - `userId` (TEXT): User identifier
  - `createdAt` (DATE): Creation timestamp
  - `updatedAt` (DATE): Last update timestamp
  - `isActive` (BOOL): Active status
  - `contextVector` (NUMBER_ARRAY): Conversation context embedding
  - `metadata` (OBJECT): Additional conversation metadata
- **Vectorizer**: text2vec-openai

### 2. Message
**Purpose**: Individual messages within conversations
- **Properties**: 8 total
  - `messageId` (TEXT): Unique message identifier
  - `conversationId` (TEXT): Parent conversation ID
  - `role` (TEXT): Message role (user, assistant, system)
  - `content` (TEXT): Message content
  - `createdAt` (DATE): Message timestamp
  - `toolCalls` (TEXT): JSON string of tool calls
  - `extraData` (OBJECT): Additional message metadata
  - `embedding` (NUMBER_ARRAY): Message content embedding
- **Vectorizer**: text2vec-transformers

### 3. Document
**Purpose**: Documents for RAG and knowledge base
- **Properties**: 12 total
  - `documentId` (TEXT): Unique document identifier
  - `title` (TEXT): Document title
  - `content` (TEXT): Full document content
  - `contentType` (TEXT): MIME type
  - `filePath` (TEXT): Original file path
  - `fileSize` (INT): File size in bytes
  - `tags` (TEXT_ARRAY): Document tags
  - `createdAt` (DATE): Creation timestamp
  - `updatedAt` (DATE): Last update timestamp
  - `isActive` (BOOL): Active status
  - `metadata` (OBJECT): Document metadata
  - `embedding` (NUMBER_ARRAY): Document embedding
- **Vectorizer**: text2vec-transformers

### 4. DocumentChunk
**Purpose**: Document chunks for efficient retrieval
- **Properties**: 8 total
  - `chunkId` (TEXT): Unique chunk identifier
  - `documentId` (TEXT): Parent document ID
  - `content` (TEXT): Chunk content
  - `chunkIndex` (INT): Chunk position in document
  - `startOffset` (INT): Start character offset
  - `endOffset` (INT): End character offset
  - `metadata` (OBJECT): Chunk metadata
  - `embedding` (NUMBER_ARRAY): Chunk embedding
- **Vectorizer**: text2vec-transformers

### 5. AgentInteraction
**Purpose**: Agent interactions and performance tracking
- **Properties**: 11 total
  - `interactionId` (TEXT): Unique interaction identifier
  - `agentType` (TEXT): Type of agent
  - `query` (TEXT): Input query
  - `response` (TEXT): Agent response
  - `toolsUsed` (TEXT_ARRAY): Tools utilized
  - `executionTimeMs` (NUMBER): Execution time
  - `tokensUsed` (INT): Tokens consumed
  - `conversationId` (TEXT): Related conversation
  - `createdAt` (DATE): Interaction timestamp
  - `metadata` (OBJECT): Additional metadata
  - `embedding` (NUMBER_ARRAY): Interaction embedding
- **Vectorizer**: text2vec-transformers

### 6. MultiModalContent
**Purpose**: Multimodal content with cross-modal embeddings
- **Properties**: 14 total
  - `contentId` (TEXT): Unique content identifier
  - `mediaType` (TEXT): Media type (audio, video, image)
  - `filename` (TEXT): Original filename
  - `fileSize` (INT): File size in bytes
  - `contentHash` (TEXT): SHA-256 hash
  - `storagePath` (TEXT): Storage location
  - `processingStatus` (TEXT): Processing status
  - `processingResult` (OBJECT): Processing results
  - `conversationId` (TEXT): Related conversation
  - `createdAt` (DATE): Creation timestamp
  - `updatedAt` (DATE): Update timestamp
  - `textContent` (TEXT): Extracted text content
  - `visualEmbedding` (NUMBER_ARRAY): CLIP visual embedding
  - `textEmbedding` (NUMBER_ARRAY): Text embedding
- **Vectorizer**: text2vec-transformers

## Usage

### Basic Schema Creation

```python
import weaviate
from app.database.weaviate_schema import create_weaviate_schema

# Connect to Weaviate
client = weaviate.connect_to_local()

# Create schema
success = create_weaviate_schema(client)
if success:
    print("Schema created successfully!")
else:
    print("Schema creation failed!")
```

### Advanced Schema Management

```python
from app.database.weaviate_schema import WeaviateSchemaManager

# Create schema manager
schema_manager = WeaviateSchemaManager(client)

# Create schema
schema_manager.create_weaviate_schema()

# Get schema information
info = schema_manager.get_schema_info()
print(f"Schema info: {info}")

# Delete schema (for cleanup)
schema_manager.delete_schema()
```

## Migration from SQLite

The schema is designed to be fully compatible with existing SQLite data:

### Conversation Migration
- `id` → `conversationId`
- `title` → `title`
- `user_id` → `userId`
- `created_at` → `createdAt`
- `updated_at` → `updatedAt`
- **New**: `contextVector`, `isActive`, `metadata`

### Message Migration
- `id` → `messageId`
- `conversation_id` → `conversationId`
- `role` → `role`
- `content` → `content`
- `created_at` → `createdAt`
- `tool_calls` → `toolCalls`
- `extra_data` → `extraData`
- **New**: `embedding`

### Migration Utilities

```python
from app.database.migration_utils import migrate_sqlite_to_weaviate

# Migrate all data
results = migrate_sqlite_to_weaviate(sqlite_session, weaviate_client)
print(f"Migration results: {results}")
```

## Vector Capabilities

### Semantic Search
All text content is automatically vectorized for semantic search:

```python
# Search conversations by semantic similarity
collection = client.collections.get("Conversation")
results = collection.query.near_text(
    query="AI assistance",
    limit=10
)
```

### Cross-Modal Search
MultiModalContent supports cross-modal embeddings:

```python
# Search multimodal content
collection = client.collections.get("MultiModalContent")
results = collection.query.near_text(
    query="image of a cat",
    limit=5
)
```

## Performance Characteristics

- **Total Classes**: 6
- **Total Properties**: 61
- **Average Properties per Class**: 10.2
- **Vector Dimensions**: Configurable per vectorizer
- **Indexing**: Real-time with Weaviate
- **Scalability**: Distributed architecture support

## Testing

Comprehensive unit tests are provided in `tests/unit/test_weaviate_schema.py`:

```bash
# Run schema tests
python -m pytest tests/unit/test_weaviate_schema.py -v

# Run with coverage
python -m pytest tests/unit/test_weaviate_schema.py --cov=app.database.weaviate_schema
```

## Dependencies

- `weaviate-client>=4.4.0`: Weaviate Python client
- `pydantic>=2.0.0`: Data validation
- `sqlalchemy>=2.0.0`: For migration utilities

## Error Handling

The implementation includes comprehensive error handling:

- **WeaviateBaseError**: Weaviate-specific errors
- **Connection Errors**: Network and authentication issues
- **Schema Conflicts**: Existing schema validation
- **Migration Errors**: Data conversion and validation

## Production Considerations

1. **Authentication**: Configure API keys for production Weaviate
2. **Vectorizers**: Choose appropriate vectorizers for your use case
3. **Indexing**: Configure HNSW parameters for performance
4. **Backup**: Implement regular schema and data backups
5. **Monitoring**: Set up monitoring for schema health and performance

## Future Enhancements

- **Custom Vectorizers**: Support for domain-specific embeddings
- **Schema Versioning**: Automated schema migration support
- **Performance Optimization**: Query optimization and caching
- **Multi-Tenancy**: Support for tenant-specific schemas
