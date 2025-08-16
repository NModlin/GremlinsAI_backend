# GremlinsAI Frontend Integration Guide v9.0.0 - Comprehensive Edition

## Table of Contents

1. [Quick Start](#quick-start)
2. [Complete API Reference](#complete-api-reference)
3. [Authentication & Security](#authentication--security)
4. [Multi-Language Code Examples](#multi-language-code-examples)
5. [Step-by-Step Tutorials](#step-by-step-tutorials)
6. [WebSocket Real-Time Features](#websocket-real-time-features)
7. [GraphQL Integration](#graphql-integration)
8. [Multi-Modal Processing](#multi-modal-processing)
9. [Error Handling & Best Practices](#error-handling--best-practices)
10. [Production Deployment](#production-deployment)

## Quick Start

### Environment Configuration

```javascript
// Configuration for GremlinsAI v9.0.0
const GREMLINS_CONFIG = {
  baseURL: 'http://localhost:8000',
  apiVersion: 'v1',
  endpoints: {
    rest: '/api/v1',
    graphql: '/graphql',
    websocket: '/api/v1/ws',
    docs: '/docs',
    portal: '/developer-portal'
  },
  features: {
    totalEndpoints: 103,
    realTimeSupport: true,
    multiModalProcessing: true,
    vectorSearch: true,
    multiAgentWorkflows: true
  }
};

// Environment variables for different frameworks
// React (.env)
REACT_APP_GREMLINS_BASE_URL=http://localhost:8000
REACT_APP_GREMLINS_API_KEY=your_api_key_here
REACT_APP_GREMLINS_WS_URL=ws://localhost:8000/api/v1/ws

// Vue (.env)
VUE_APP_GREMLINS_BASE_URL=http://localhost:8000
VUE_APP_GREMLINS_API_KEY=your_api_key_here

// Next.js (.env.local)
NEXT_PUBLIC_GREMLINS_BASE_URL=http://localhost:8000
GREMLINS_API_KEY=your_api_key_here
```

### Basic Client Setup

```javascript
class GremlinsAIClient {
  constructor(config = {}) {
    this.baseURL = config.baseURL || 'http://localhost:8000';
    this.apiKey = config.apiKey || process.env.GREMLINS_API_KEY;
    this.timeout = config.timeout || 30000;
    this.retryAttempts = config.retryAttempts || 3;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const config = {
      timeout: this.timeout,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.apiKey}`,
        'X-API-Version': '9.0.0',
        ...options.headers
      },
      ...options
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        const error = await response.json();
        throw new GremlinsAPIError(error);
      }
      
      return await response.json();
    } catch (error) {
      if (error instanceof GremlinsAPIError) throw error;
      throw new GremlinsAPIError({
        error_code: 'NETWORK_ERROR',
        error_message: error.message,
        severity: 'high'
      });
    }
  }
}

// Error handling class
class GremlinsAPIError extends Error {
  constructor(errorData) {
    super(errorData.error_message || 'Unknown API error');
    this.code = errorData.error_code;
    this.severity = errorData.severity;
    this.details = errorData.error_details;
    this.suggestedAction = errorData.suggested_action;
    this.documentationUrl = errorData.documentation_url;
  }
}
```

## Complete API Reference

### Core Agent Endpoints (7 endpoints)

```javascript
// 1. POST /api/v1/agent/invoke - Simple agent invocation
async function invokeAgent(input, options = {}) {
  return await client.request('/api/v1/agent/invoke', {
    method: 'POST',
    body: JSON.stringify({
      input,
      conversation_id: options.conversationId,
      save_conversation: options.saveConversation || false
    })
  });
}

// 2. POST /api/v1/agent/chat - Context-aware chat
async function chatWithAgent(input, conversationId, useMultiAgent = false) {
  return await client.request(`/api/v1/agent/chat?use_multi_agent=${useMultiAgent}`, {
    method: 'POST',
    body: JSON.stringify({
      input,
      conversation_id: conversationId,
      save_conversation: true
    })
  });
}

// Example usage
const response = await invokeAgent("What is machine learning?", {
  saveConversation: true
});
console.log(response.output);
```

### Chat History Management (12 endpoints)

```javascript
// Conversation management
class ConversationManager {
  constructor(client) {
    this.client = client;
  }

  // Create new conversation
  async createConversation(title, initialMessage = null) {
    return await this.client.request('/api/v1/history/conversations', {
      method: 'POST',
      body: JSON.stringify({
        title,
        initial_message: initialMessage
      })
    });
  }

  // List conversations with pagination
  async listConversations(limit = 50, offset = 0) {
    const params = new URLSearchParams({ limit, offset });
    return await this.client.request(`/api/v1/history/conversations?${params}`);
  }

  // Get specific conversation
  async getConversation(conversationId, includeMessages = true) {
    const params = new URLSearchParams({ include_messages: includeMessages });
    return await this.client.request(
      `/api/v1/history/conversations/${conversationId}?${params}`
    );
  }

  // Update conversation
  async updateConversation(conversationId, updates) {
    return await this.client.request(`/api/v1/history/conversations/${conversationId}`, {
      method: 'PUT',
      body: JSON.stringify(updates)
    });
  }

  // Delete conversation
  async deleteConversation(conversationId) {
    return await this.client.request(`/api/v1/history/conversations/${conversationId}`, {
      method: 'DELETE'
    });
  }

  // Get messages for conversation
  async getMessages(conversationId, limit = 100, offset = 0) {
    const params = new URLSearchParams({ limit, offset });
    return await this.client.request(
      `/api/v1/history/conversations/${conversationId}/messages?${params}`
    );
  }

  // Add message to conversation
  async addMessage(conversationId, role, content, toolCalls = null) {
    return await this.client.request('/api/v1/history/messages', {
      method: 'POST',
      body: JSON.stringify({
        conversation_id: conversationId,
        role,
        content,
        tool_calls: toolCalls
      })
    });
  }

  // Get conversation context for AI
  async getConversationContext(conversationId, messageLimit = 10) {
    const params = new URLSearchParams({ message_limit: messageLimit });
    return await this.client.request(
      `/api/v1/history/conversations/${conversationId}/context?${params}`
    );
  }
}

// Usage example
const conversationManager = new ConversationManager(client);
const conversation = await conversationManager.createConversation(
  "AI Discussion", 
  "Let's talk about artificial intelligence"
);
```

### Document Management & RAG (15 endpoints)

```javascript
class DocumentManager {
  constructor(client) {
    this.client = client;
  }

  // Upload document file
  async uploadDocument(file, metadata = {}) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('metadata', JSON.stringify(metadata));

    return await this.client.request('/api/v1/documents/upload', {
      method: 'POST',
      body: formData,
      headers: {} // Remove Content-Type to let browser set it for FormData
    });
  }

  // Create document from text
  async createDocument(title, content, options = {}) {
    return await this.client.request('/api/v1/documents/', {
      method: 'POST',
      body: JSON.stringify({
        title,
        content,
        content_type: options.contentType || 'text/plain',
        doc_metadata: options.metadata || {},
        tags: options.tags || [],
        chunk_size: options.chunkSize || 1000,
        chunk_overlap: options.chunkOverlap || 200
      })
    });
  }

  // Semantic search
  async searchDocuments(query, options = {}) {
    return await this.client.request('/api/v1/documents/search', {
      method: 'POST',
      body: JSON.stringify({
        query,
        limit: options.limit || 10,
        search_type: options.searchType || 'chunks',
        filters: options.filters || {}
      })
    });
  }

  // RAG query
  async ragQuery(query, options = {}) {
    return await this.client.request('/api/v1/documents/rag', {
      method: 'POST',
      body: JSON.stringify({
        query,
        use_multi_agent: options.useMultiAgent || false,
        search_limit: options.searchLimit || 5,
        conversation_id: options.conversationId
      })
    });
  }

  // List documents
  async listDocuments(options = {}) {
    const params = new URLSearchParams({
      limit: options.limit || 50,
      offset: options.offset || 0,
      ...(options.tags && { tags: options.tags.join(',') }),
      ...(options.contentType && { content_type: options.contentType })
    });
    
    return await this.client.request(`/api/v1/documents/?${params}`);
  }

  // Get document by ID
  async getDocument(documentId) {
    return await this.client.request(`/api/v1/documents/${documentId}`);
  }

  // Delete document
  async deleteDocument(documentId) {
    return await this.client.request(`/api/v1/documents/${documentId}`, {
      method: 'DELETE'
    });
  }
}

// Usage example
const docManager = new DocumentManager(client);

// Upload a file
const fileInput = document.getElementById('file-input');
const file = fileInput.files[0];
const uploadResult = await docManager.uploadDocument(file, {
  category: 'research',
  source: 'user_upload'
});

// Search documents
const searchResults = await docManager.searchDocuments("machine learning algorithms", {
  limit: 5,
  searchType: 'chunks'
});

// RAG query
const ragResponse = await docManager.ragQuery(
  "What are the benefits of machine learning?",
  { useMultiAgent: true, searchLimit: 3 }
);
```

### Multi-Agent System (8 endpoints)

```javascript
class MultiAgentManager {
  constructor(client) {
    this.client = client;
  }

  // Execute multi-agent workflow
  async executeWorkflow(workflowType, input, options = {}) {
    return await this.client.request('/api/v1/multi-agent/execute', {
      method: 'POST',
      body: JSON.stringify({
        workflow_type: workflowType,
        input,
        conversation_id: options.conversationId,
        agent_config: options.agentConfig || {}
      })
    });
  }

  // Get available workflows
  async getWorkflows() {
    return await this.client.request('/api/v1/multi-agent/workflows');
  }

  // Get agent capabilities
  async getCapabilities() {
    return await this.client.request('/api/v1/multi-agent/capabilities');
  }

  // Execute custom agent workflow
  async executeCustomWorkflow(agents, input, options = {}) {
    return await this.client.request('/api/v1/multi-agent/custom', {
      method: 'POST',
      body: JSON.stringify({
        agents,
        input,
        workflow_config: options.workflowConfig || {},
        conversation_id: options.conversationId
      })
    });
  }

  // Get workflow status
  async getWorkflowStatus(workflowId) {
    return await this.client.request(`/api/v1/multi-agent/status/${workflowId}`);
  }
}

// Usage examples
const multiAgent = new MultiAgentManager(client);

// Execute research workflow
const researchResult = await multiAgent.executeWorkflow(
  'research_analyze_write',
  'Analyze the impact of AI on healthcare',
  { conversationId: 'conv_123' }
);

// Get available workflows
const workflows = await multiAgent.getWorkflows();
console.log('Available workflows:', workflows.workflows);
```
