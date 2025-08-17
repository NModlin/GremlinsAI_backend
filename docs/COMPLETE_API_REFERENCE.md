# GremlinsAI Complete API Reference v10.0.0

## Overview

GremlinsAI provides a comprehensive suite of APIs for building advanced AI applications with multi-modal processing, real-time collaboration, analytics, and local LLM optimization.

**Base URL:** `http://localhost:8000`  
**API Version:** v10.0.0  
**Total Endpoints:** 120+  
**Supported Protocols:** REST, GraphQL, WebSocket

## Table of Contents

1. [Authentication](#authentication)
2. [Core Agent APIs](#core-agent-apis)
3. [Multi-Agent Workflows](#multi-agent-workflows)
4. [Document Management & RAG](#document-management--rag)
5. [Multi-Modal Processing](#multi-modal-processing)
6. [Real-time Collaboration](#real-time-collaboration)
7. [Analytics Dashboard](#analytics-dashboard)
8. [Local LLM Optimization](#local-llm-optimization)
9. [WebSocket APIs](#websocket-apis)
10. [GraphQL APIs](#graphql-apis)
11. [Error Handling](#error-handling)
12. [Rate Limiting](#rate-limiting)

## Authentication

### API Key Authentication
```http
Authorization: Bearer YOUR_API_KEY
```

### OAuth 2.0 (Google)
```http
Authorization: Bearer OAUTH_ACCESS_TOKEN
```

### Generate API Key
```bash
curl -X POST "http://localhost:8000/api/v1/auth/api-keys" \
  -H "Content-Type: application/json" \
  -d '{"name": "My App", "permissions": ["read", "write"]}'
```

## Core Agent APIs

### Simple Agent Invocation
```http
POST /api/v1/agent/invoke
```

**Request:**
```json
{
  "input": "What is artificial intelligence?",
  "conversation_id": "optional-uuid",
  "save_conversation": true
}
```

**Response:**
```json
{
  "output": "AI is a branch of computer science...",
  "conversation_id": "uuid",
  "message_id": "uuid",
  "execution_time": 1.23,
  "tokens_used": 150,
  "tools_used": ["web_search"]
}
```

### Context-Aware Chat
```http
POST /api/v1/agent/chat
```

**Request:**
```json
{
  "input": "Can you explain that in simpler terms?",
  "conversation_id": "existing-uuid",
  "use_multi_agent": true,
  "use_rag": true,
  "save_conversation": true
}
```

**Response:**
```json
{
  "output": "In simple terms, AI is...",
  "conversation_id": "uuid",
  "message_id": "uuid",
  "context_used": true,
  "agents_involved": ["researcher", "writer"],
  "documents_referenced": 3,
  "execution_time": 2.45
}
```

## Multi-Agent Workflows

### Execute Multi-Agent Workflow
```http
POST /api/v1/multi-agent/workflow
```

**Request:**
```json
{
  "input": "Analyze the impact of renewable energy on the economy",
  "workflow_type": "research_analyze_write",
  "agents": ["researcher", "analyst", "writer"],
  "save_conversation": true,
  "async_mode": false
}
```

**Response:**
```json
{
  "workflow_id": "uuid",
  "status": "completed",
  "result": {
    "research_findings": "...",
    "analysis": "...",
    "final_report": "..."
  },
  "agents_used": ["researcher", "analyst", "writer"],
  "execution_time": 15.67,
  "conversation_id": "uuid"
}
```

### Get Agent Capabilities
```http
GET /api/v1/multi-agent/capabilities
```

**Response:**
```json
{
  "available_agents": [
    {
      "name": "researcher",
      "description": "Specialized in information gathering and research",
      "tools": ["web_search", "document_search"],
      "capabilities": ["research", "fact_checking"]
    },
    {
      "name": "analyst",
      "description": "Expert in data analysis and insights",
      "tools": ["calculator", "data_processor"],
      "capabilities": ["analysis", "pattern_recognition"]
    }
  ],
  "workflow_types": ["research_analyze_write", "creative_workflow", "technical_analysis"]
}
```

## Document Management & RAG

### Create Document
```http
POST /api/v1/documents/
```

**Request:**
```json
{
  "title": "AI Research Paper",
  "content": "Artificial intelligence research shows...",
  "tags": ["ai", "research", "machine-learning"],
  "chunk_size": 1000,
  "metadata": {
    "author": "Dr. Smith",
    "publication_date": "2024-01-15"
  }
}
```

**Response:**
```json
{
  "id": "uuid",
  "title": "AI Research Paper",
  "chunks_created": 15,
  "vector_embeddings": 15,
  "created_at": "2024-01-15T10:00:00Z",
  "status": "processed"
}
```

### Semantic Search
```http
POST /api/v1/documents/search
```

**Request:**
```json
{
  "query": "machine learning algorithms",
  "limit": 5,
  "search_type": "chunks",
  "filters": {
    "tags": ["ai", "research"],
    "date_range": {
      "start": "2024-01-01",
      "end": "2024-12-31"
    }
  },
  "similarity_threshold": 0.7
}
```

**Response:**
```json
{
  "results": [
    {
      "chunk_id": "uuid",
      "document_id": "uuid",
      "content": "Machine learning algorithms are...",
      "similarity_score": 0.95,
      "metadata": {
        "document_title": "AI Research Paper",
        "chunk_index": 3
      }
    }
  ],
  "total_results": 12,
  "search_time": 0.045
}
```

### RAG Query
```http
POST /api/v1/documents/rag
```

**Request:**
```json
{
  "query": "Explain neural networks based on available documents",
  "use_multi_agent": true,
  "search_limit": 5,
  "context_window": 4000,
  "include_sources": true
}
```

**Response:**
```json
{
  "answer": "Based on the available research documents, neural networks are...",
  "sources": [
    {
      "document_title": "Deep Learning Fundamentals",
      "chunk_content": "Neural networks consist of...",
      "relevance_score": 0.92
    }
  ],
  "documents_used": 3,
  "agents_involved": ["researcher", "analyst"],
  "confidence_score": 0.88
}
```

## Multi-Modal Processing

### Process Audio File
```http
POST /api/v1/multimodal/process/audio
```

**Request (multipart/form-data):**
```
file: audio.wav
transcribe: true
analyze: true
language: en
```

**Response:**
```json
{
  "content_id": "uuid",
  "transcription": {
    "text": "Hello, this is a test audio file...",
    "confidence": 0.95,
    "language": "en",
    "duration": 30.5
  },
  "analysis": {
    "sentiment": "neutral",
    "key_topics": ["technology", "AI"],
    "speaker_count": 1
  },
  "processing_time": 2.3
}
```

### Process Video File
```http
POST /api/v1/multimodal/process/video
```

**Request (multipart/form-data):**
```
file: video.mp4
extract_frames: true
transcribe_audio: true
frame_count: 10
```

**Response:**
```json
{
  "content_id": "uuid",
  "video_analysis": {
    "duration": 120.5,
    "resolution": "1920x1080",
    "fps": 30
  },
  "frames": [
    {
      "timestamp": 0.0,
      "objects_detected": ["person", "computer"],
      "description": "A person working at a computer"
    }
  ],
  "audio_transcription": {
    "text": "In this video, we'll explore...",
    "confidence": 0.92
  }
}
```

### Multi-Modal Fusion
```http
POST /api/v1/multimodal/process/multimodal
```

**Request (multipart/form-data):**
```
files: audio.wav
files: video.mp4
files: document.pdf
fusion_strategy: concatenate
```

**Response:**
```json
{
  "fusion_id": "uuid",
  "combined_content": {
    "text": "Combined transcription and document text...",
    "media_elements": 3,
    "total_duration": 150.5
  },
  "cross_modal_insights": {
    "consistency_score": 0.87,
    "key_themes": ["AI", "technology", "innovation"],
    "sentiment_alignment": "positive"
  }
}
```

## Real-time Collaboration

### Create Collaboration Session
```http
POST /api/v1/collaboration/sessions
```

**Request:**
```json
{
  "document_id": "uuid",
  "initial_content": "# Collaborative Document\n\nStart editing here...",
  "creator_id": "user123"
}
```

**Response:**
```json
{
  "session_id": "uuid",
  "document_id": "uuid",
  "websocket_url": "/api/v1/collaborate/uuid",
  "created_at": "2024-01-15T10:00:00Z",
  "max_participants": 50
}
```

### WebSocket Collaboration
```javascript
// Connect to collaboration session
const ws = new WebSocket('ws://localhost:8000/api/v1/collaborate/session-uuid?participant_id=user123&display_name=Alice');

// Join session
ws.send(JSON.stringify({
  type: 'join_session',
  participant_type: 'human_user'
}));

// Send document operation
ws.send(JSON.stringify({
  type: 'document_update',
  operation: {
    type: 'insert',
    position: 10,
    content: 'Hello world'
  }
}));

// Receive real-time updates
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Received:', message);
};
```

### Get Collaboration Metrics
```http
GET /api/v1/collaboration/metrics
```

**Response:**
```json
{
  "active_sessions": 15,
  "total_participants": 45,
  "avg_latency_ms": 85,
  "operations_per_second": 120,
  "uptime_hours": 168.5
}
```

## Analytics Dashboard

### Get Tool Usage Analytics
```http
GET /api/analytics/tool_usage?time_window=24h&limit=20
```

**Response:**
```json
[
  {
    "tool_name": "web_search",
    "usage_count": 145,
    "success_rate": 0.92,
    "avg_execution_time": 2.3,
    "unique_users": 23,
    "efficiency_score": 4.2
  },
  {
    "tool_name": "text_processor",
    "usage_count": 98,
    "success_rate": 0.96,
    "avg_execution_time": 1.1,
    "unique_users": 18,
    "efficiency_score": 8.7
  }
]
```

### Get Query Trends
```http
GET /api/analytics/query_trends?time_window=7d&category=business_keyword
```

**Response:**
```json
[
  {
    "keyword": "analysis",
    "category": "business_keyword",
    "frequency": 89,
    "trend_score": 0.34,
    "percentage": 0.18
  },
  {
    "keyword": "data",
    "category": "business_keyword",
    "frequency": 76,
    "trend_score": 0.29,
    "percentage": 0.15
  }
]
```

### Get Performance Metrics
```http
GET /api/analytics/performance_metrics?time_window=24h
```

**Response:**
```json
[
  {
    "agent_type": "production_agent",
    "avg_response_time": 3.2,
    "success_rate": 0.94,
    "total_interactions": 156,
    "avg_reasoning_steps": 2.8,
    "avg_token_usage": 1245,
    "performance_grade": "A"
  }
]
```

### Get Dashboard Summary
```http
GET /api/analytics/dashboard?time_window=24h
```

**Response:**
```json
{
  "summary": {
    "total_interactions": 1250,
    "active_users": 45,
    "top_performing_agent": "production_agent",
    "most_used_tool": "web_search",
    "avg_response_time": 2.8,
    "overall_success_rate": 0.93
  },
  "tool_usage": [...],
  "query_trends": [...],
  "performance_metrics": [...],
  "processing_status": {
    "status": "active",
    "last_processing_time": "2024-01-15T10:00:00Z",
    "latency_target": "< 5 minutes"
  }
}
```

### Trigger Analytics Processing
```http
POST /api/analytics/process?time_window=1h
```

**Response:**
```json
{
  "status": "success",
  "message": "Analytics processing completed",
  "result": {
    "processed": 150,
    "metrics_generated": 25,
    "processing_time_seconds": 2.3
  },
  "timestamp": "2024-01-15T10:00:00Z"
}
```

## Local LLM Optimization

### Get LLM Router Status
```http
GET /api/v1/llm/router/status
```

**Response:**
```json
{
  "active_tiers": ["fast", "balanced", "powerful"],
  "model_configs": {
    "fast": {
      "model_name": "llama3.2:3b",
      "gpu_memory_mb": 3000,
      "avg_tokens_per_second": 50.0,
      "concurrent_capacity": 8
    },
    "powerful": {
      "model_name": "llama3.2:70b",
      "gpu_memory_mb": 40000,
      "avg_tokens_per_second": 8.0,
      "concurrent_capacity": 1
    }
  },
  "current_load": {
    "fast": 3,
    "balanced": 1,
    "powerful": 0
  },
  "throughput_improvement": 28.5,
  "memory_efficiency": 72.3
}
```

### Optimize GPU Memory
```http
POST /api/v1/llm/optimize-memory
```

**Response:**
```json
{
  "models_unloaded": ["llama3.2:70b"],
  "memory_freed_mb": 40000,
  "models_kept_loaded": ["llama3.2:3b", "llama3.2:8b"],
  "optimization_time_seconds": 2.5,
  "memory_reduction_percent": 35.2
}
```

### Get Performance Metrics
```http
GET /api/v1/llm/performance-metrics
```

**Response:**
```json
{
  "routing_stats": {
    "total_requests": 1000,
    "tier_usage": {
      "fast": 600,
      "balanced": 300,
      "powerful": 100
    }
  },
  "tier_performance": {
    "fast": {
      "avg_response_time": 0.8,
      "usage_percentage": 60.0,
      "success_rate": 0.98
    }
  },
  "throughput_analysis": {
    "improvement_percentage": 25.3,
    "baseline_throughput": 20.0,
    "optimized_throughput": 25.1
  }
}
```

## WebSocket APIs

### Connection Endpoint
```
ws://localhost:8000/api/v1/ws/ws
```

### Message Types

#### Subscribe to Updates
```json
{
  "type": "subscribe",
  "subscription_type": "conversation",
  "conversation_id": "uuid"
}
```

#### Real-time Message
```json
{
  "type": "message",
  "conversation_id": "uuid",
  "message": {
    "id": "uuid",
    "role": "assistant",
    "content": "Hello! How can I help you?",
    "timestamp": "2024-01-15T10:00:00Z"
  }
}
```

#### Task Status Update
```json
{
  "type": "task_update",
  "task_id": "uuid",
  "status": "completed",
  "result": {...},
  "timestamp": "2024-01-15T10:00:00Z"
}
```

#### System Event
```json
{
  "type": "system_event",
  "event": "agent_started",
  "data": {
    "agent_type": "researcher",
    "task_id": "uuid"
  },
  "timestamp": "2024-01-15T10:00:00Z"
}
```

## GraphQL APIs

### Endpoint
```
POST http://localhost:8000/graphql
```

### Query Examples

#### Get Conversations
```graphql
query GetConversations($limit: Int, $offset: Int) {
  conversations(limit: $limit, offset: $offset) {
    id
    title
    createdAt
    messages {
      id
      role
      content
      createdAt
    }
  }
}
```

#### Create Conversation
```graphql
mutation CreateConversation($input: ConversationInput!) {
  createConversation(input: $input) {
    id
    title
    createdAt
  }
}
```

#### Subscribe to Messages
```graphql
subscription MessageUpdates($conversationId: String!) {
  messageAdded(conversationId: $conversationId) {
    id
    role
    content
    createdAt
  }
}
```

## Error Handling

### Standard Error Response
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Input validation failed",
    "details": {
      "field": "input",
      "reason": "Field is required"
    },
    "timestamp": "2024-01-15T10:00:00Z",
    "request_id": "uuid"
  }
}
```

### HTTP Status Codes
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `422` - Validation Error
- `429` - Rate Limited
- `500` - Internal Server Error
- `503` - Service Unavailable

## Rate Limiting

### Default Limits
- **API Calls**: 1000 requests/hour per API key
- **WebSocket Connections**: 10 concurrent connections per user
- **File Uploads**: 100MB per request, 1GB per hour
- **Analytics Queries**: 100 requests/hour per user

### Rate Limit Headers
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1642248000
```

### Rate Limit Exceeded Response
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Try again in 60 seconds.",
    "retry_after": 60
  }
}
```
```
