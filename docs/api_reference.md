# gremlinsAI API Reference

Complete reference documentation for all gremlinsAI APIs including REST, GraphQL, and WebSocket interfaces.

## Table of Contents

1. [REST API Reference](#rest-api-reference)
2. [GraphQL API Reference](#graphql-api-reference)
3. [WebSocket API Reference](#websocket-api-reference)
4. [Authentication](#authentication)
5. [Error Handling](#error-handling)
6. [Rate Limits](#rate-limits)

## REST API Reference

Base URL: `http://localhost:8000/api/v1/`

### Core Agent Endpoints

#### POST /agent/invoke
Invoke the core AI agent with a query.

**Request Body:**
```json
{
  "input": "string",
  "conversation_id": "string (optional)",
  "save_conversation": "boolean (optional, default: false)"
}
```

**Response:**
```json
{
  "output": "string",
  "conversation_id": "string",
  "execution_time": "number",
  "timestamp": "string (ISO 8601)"
}
```

**Example:**
```python
import requests

response = requests.post("http://localhost:8000/api/v1/agent/invoke", json={
    "input": "What is machine learning?",
    "save_conversation": True
})

print(response.json())
```

#### POST /agent/invoke-with-tools
Invoke the agent with specific tool preferences.

**Request Body:**
```json
{
  "input": "string",
  "tools": ["string"],
  "conversation_id": "string (optional)"
}
```

### Conversation Management Endpoints

#### GET /history/conversations
List all conversations with pagination.

**Query Parameters:**
- `limit`: integer (default: 10, max: 100)
- `offset`: integer (default: 0)

**Response:**
```json
{
  "conversations": [
    {
      "id": "string",
      "title": "string",
      "created_at": "string (ISO 8601)",
      "updated_at": "string (ISO 8601)",
      "message_count": "integer"
    }
  ],
  "total": "integer",
  "limit": "integer",
  "offset": "integer"
}
```

#### POST /history/conversations
Create a new conversation.

**Request Body:**
```json
{
  "title": "string (optional)"
}
```

#### GET /history/conversations/{conversation_id}
Get a specific conversation with all messages.

**Response:**
```json
{
  "id": "string",
  "title": "string",
  "created_at": "string (ISO 8601)",
  "updated_at": "string (ISO 8601)",
  "messages": [
    {
      "id": "string",
      "role": "string",
      "content": "string",
      "created_at": "string (ISO 8601)",
      "tool_calls": "string (optional)",
      "extra_data": "string (optional)"
    }
  ]
}
```

#### POST /history/conversations/{conversation_id}/messages
Add a message to a conversation.

**Request Body:**
```json
{
  "role": "string",
  "content": "string",
  "tool_calls": "string (optional)",
  "extra_data": "object (optional)"
}
```

### Multi-Agent Endpoints

#### GET /multi-agent/capabilities
Get information about available agents and their capabilities.

**Response:**
```json
{
  "agents": {
    "researcher": {
      "role": "string",
      "capabilities": "string",
      "tools": "string",
      "available": "boolean"
    }
  },
  "workflows": {
    "simple_research": "string",
    "research_analyze_write": "string"
  },
  "total_agents": "integer"
}
```

#### POST /multi-agent/execute
Execute a multi-agent workflow.

**Request Body:**
```json
{
  "workflow_type": "string",
  "input": "string",
  "conversation_id": "string (optional)",
  "save_conversation": "boolean (optional, default: false)"
}
```

**Response:**
```json
{
  "workflow_type": "string",
  "result": "string",
  "agents_used": ["string"],
  "execution_time": "number",
  "conversation_id": "string (optional)"
}
```

### Document Management Endpoints

#### POST /documents/upload
Upload a document for processing and indexing.

**Request:**
- Content-Type: `multipart/form-data`
- Body: File upload with optional metadata

**Response:**
```json
{
  "document_id": "string",
  "title": "string",
  "content_type": "string",
  "file_size": "integer",
  "chunks_created": "integer",
  "vector_indexed": "boolean"
}
```

#### GET /documents
List all documents with pagination.

**Query Parameters:**
- `limit`: integer (default: 10)
- `offset`: integer (default: 0)
- `search`: string (optional)

#### POST /documents/search
Search documents using semantic search.

**Request Body:**
```json
{
  "query": "string",
  "limit": "integer (optional, default: 5)",
  "score_threshold": "number (optional)",
  "use_rag": "boolean (optional, default: false)"
}
```

**Response:**
```json
{
  "query": "string",
  "results": [
    {
      "document_id": "string",
      "title": "string",
      "content": "string",
      "score": "number",
      "chunk_index": "integer"
    }
  ],
  "rag_response": "string (if use_rag=true)",
  "execution_time": "number"
}
```

### Orchestrator Endpoints

#### GET /orchestrator/capabilities
Get orchestrator capabilities and supported task types.

**Response:**
```json
{
  "supported_tasks": ["string"],
  "execution_modes": ["string"],
  "features": {
    "asynchronous_execution": "boolean",
    "task_monitoring": "boolean"
  },
  "version": "string"
}
```

#### POST /orchestrator/execute
Execute a task through the orchestrator.

**Request Body:**
```json
{
  "task_type": "string",
  "payload": "object",
  "execution_mode": "string (sync|async)",
  "priority": "integer (optional, default: 1)",
  "timeout": "integer (optional)"
}
```

#### GET /orchestrator/tasks/{task_id}/status
Get the status of an asynchronous task.

**Response:**
```json
{
  "task_id": "string",
  "status": "string",
  "result": "object (optional)",
  "error": "string (optional)",
  "created_at": "string (ISO 8601)",
  "updated_at": "string (ISO 8601)",
  "execution_time": "number (optional)"
}
```

### Real-time API Endpoints

#### GET /realtime/info
Get real-time API information and capabilities.

**Response:**
```json
{
  "websocket_endpoint": "string",
  "supported_subscriptions": ["string"],
  "active_connections": "integer",
  "message_types": ["string"]
}
```

#### GET /realtime/connections
Get information about active WebSocket connections.

**Response:**
```json
{
  "total_connections": "integer",
  "connections_by_type": {
    "conversation": "integer",
    "system": "integer"
  },
  "uptime": "number"
}
```

#### GET /realtime/system/status
Get comprehensive system status with real-time metrics.

**Response:**
```json
{
  "status": "string",
  "version": "string",
  "components": [
    {
      "name": "string",
      "available": "boolean"
    }
  ],
  "uptime": "number",
  "active_tasks": "integer",
  "performance_metrics": {
    "avg_response_time": "number",
    "requests_per_minute": "number"
  }
}
```

## GraphQL API Reference

Endpoint: `http://localhost:8000/graphql`

### Schema Overview

The GraphQL schema provides a unified interface to all system data with strong typing and introspection capabilities.

### Queries

#### conversations
Get conversations with optional filtering and pagination.

```graphql
query GetConversations($limit: Int, $offset: Int) {
  conversations(limit: $limit, offset: $offset) {
    id
    title
    created_at
    updated_at
    messages {
      id
      role
      content
      created_at
    }
  }
}
```

#### conversation
Get a specific conversation by ID.

```graphql
query GetConversation($id: ID!) {
  conversation(id: $id) {
    id
    title
    messages {
      role
      content
      created_at
    }
  }
}
```

#### documents
Get documents with pagination.

```graphql
query GetDocuments($limit: Int, $offset: Int) {
  documents(limit: $limit, offset: $offset) {
    id
    title
    content_type
    file_size
    created_at
  }
}
```

#### agent_capabilities
Get available agent capabilities.

```graphql
query GetAgentCapabilities {
  agent_capabilities {
    name
    role
    goal
    backstory
    available
  }
}
```

#### system_health
Get system health status.

```graphql
query GetSystemHealth {
  system_health {
    status
    version
    components {
      name
      available
    }
    uptime
    active_tasks
  }
}
```

### Mutations

#### create_conversation
Create a new conversation.

```graphql
mutation CreateConversation($input: ConversationCreateInput!) {
  create_conversation(input: $input) {
    id
    title
    created_at
  }
}
```

#### add_message
Add a message to a conversation.

```graphql
mutation AddMessage($input: MessageCreateInput!) {
  add_message(input: $input) {
    id
    role
    content
    created_at
  }
}
```

#### execute_multi_agent_workflow
Execute a multi-agent workflow.

```graphql
mutation ExecuteWorkflow($input: MultiAgentWorkflowInput!) {
  execute_multi_agent_workflow(input: $input) {
    workflow_type
    result
    agents_used
    execution_time
  }
}
```

#### create_document
Create a new document.

```graphql
mutation CreateDocument($input: DocumentCreateInput!) {
  create_document(input: $input) {
    id
    title
    content_type
    created_at
  }
}
```

### Subscriptions

#### conversation_updates
Subscribe to real-time conversation updates.

```graphql
subscription ConversationUpdates($conversation_id: ID!) {
  conversation_updates(conversation_id: $conversation_id) {
    id
    role
    content
    created_at
  }
}
```

#### task_updates
Subscribe to real-time task progress updates.

```graphql
subscription TaskUpdates($task_id: ID!) {
  task_updates(task_id: $task_id) {
    task_id
    status
    progress
    result
  }
}
```

## WebSocket API Reference

Endpoint: `ws://localhost:8000/api/v1/ws/ws`

### Connection Protocol

The WebSocket API uses JSON messages for bidirectional communication.

### Message Types

#### Client to Server Messages

**Subscribe to Updates:**
```json
{
  "type": "subscribe",
  "subscription_type": "conversation|system|task",
  "conversation_id": "string (for conversation subscriptions)",
  "task_id": "string (for task subscriptions)"
}
```

**Unsubscribe:**
```json
{
  "type": "unsubscribe",
  "subscription_type": "conversation|system|task",
  "subscription_id": "string"
}
```

**Ping:**
```json
{
  "type": "ping"
}
```

#### Server to Client Messages

**Connection Established:**
```json
{
  "type": "connection_established",
  "connection_id": "string",
  "timestamp": "string (ISO 8601)"
}
```

**Subscription Confirmed:**
```json
{
  "type": "subscription_confirmed",
  "subscription_id": "string",
  "subscription_type": "string"
}
```

**Conversation Update:**
```json
{
  "type": "conversation_update",
  "conversation_id": "string",
  "message": {
    "id": "string",
    "role": "string",
    "content": "string",
    "created_at": "string (ISO 8601)"
  }
}
```

**Task Update:**
```json
{
  "type": "task_update",
  "task_id": "string",
  "status": "string",
  "progress": "number",
  "result": "object (optional)"
}
```

**System Update:**
```json
{
  "type": "system_update",
  "event": "string",
  "data": "object",
  "timestamp": "string (ISO 8601)"
}
```

**Error:**
```json
{
  "type": "error",
  "error_code": "string",
  "message": "string",
  "details": "object (optional)"
}
```

### WebSocket Example

```python
import asyncio
import websockets
import json

async def websocket_client():
    uri = "ws://localhost:8000/api/v1/ws/ws"
    
    async with websockets.connect(uri) as websocket:
        # Wait for connection established
        message = await websocket.recv()
        print(f"Connected: {message}")
        
        # Subscribe to conversation updates
        subscribe_msg = {
            "type": "subscribe",
            "subscription_type": "conversation",
            "conversation_id": "your-conversation-id"
        }
        await websocket.send(json.dumps(subscribe_msg))
        
        # Listen for updates
        async for message in websocket:
            data = json.loads(message)
            print(f"Received: {data}")

asyncio.run(websocket_client())
```

## Authentication

Currently in development mode without authentication. Production authentication will use:

- **API Keys**: Bearer token authentication
- **Rate Limiting**: Per-key rate limits
- **HTTPS**: Mandatory encrypted connections

```python
# Future authentication pattern
headers = {
    "Authorization": "Bearer YOUR_API_KEY",
    "Content-Type": "application/json"
}
```

## Error Handling

### HTTP Status Codes

- `200`: Success
- `201`: Created
- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `422`: Validation Error
- `429`: Rate Limited
- `500`: Internal Server Error

### Error Response Format

```json
{
  "error": {
    "code": "string",
    "message": "string",
    "details": "object (optional)",
    "timestamp": "string (ISO 8601)"
  }
}
```

## Rate Limits

Development mode has no rate limits. Production limits:

- **REST API**: 1000 requests/hour per API key
- **GraphQL**: 500 queries/hour per API key
- **WebSocket**: 100 connections per API key

Rate limit headers:
- `X-RateLimit-Limit`: Request limit
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Reset`: Reset timestamp

---

For more examples and tutorials, see the [Examples Documentation](examples.md).
