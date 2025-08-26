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
10. [Frontend Debugging & Troubleshooting](#frontend-debugging--troubleshooting)
11. [RAG System Integration Lessons](#rag-system-integration-lessons)
12. [Production Deployment](#production-deployment)

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

---

## Frontend Debugging & Troubleshooting

### Common Issues and Solutions

#### 1. "Sorry, I encountered an error" Messages

**Problem**: Generic error messages in chat interface without specific details.

**Root Causes**:
- API endpoint mismatches between frontend and backend
- Request/response format inconsistencies
- CORS configuration issues
- Backend service unavailability

**Debugging Steps**:

```javascript
// Add comprehensive logging to your chat functions
async function sendChatMessage(message) {
    try {
        console.log('🚀 Making chat request to:', API_ENDPOINT);
        console.log('📤 Request body:', { input: message });

        const response = await fetch(API_ENDPOINT, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ input: message })
        });

        console.log('📊 Response status:', response.status);
        console.log('✅ Response ok:', response.ok);

        if (response.ok) {
            const data = await response.json();
            console.log('📥 Response data:', data);
            return data;
        } else {
            const errorText = await response.text();
            console.error('❌ Response error:', errorText);
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }
    } catch (error) {
        console.error('🔥 Chat service error:', error);
        throw new Error(`Chat service error: ${error.message}`);
    }
}
```

**Solution Checklist**:
- ✅ Verify API endpoint URLs match backend routes exactly
- ✅ Check request/response format compatibility
- ✅ Ensure CORS headers are properly configured
- ✅ Test backend endpoints independently with curl/Postman
- ✅ Add detailed console logging for debugging

#### 2. API Endpoint Mismatches

**Problem**: Frontend calls wrong endpoints or uses incorrect HTTP methods.

**Common Mismatches**:
```javascript
// ❌ Wrong - Frontend expects different endpoint
fetch('/api/v1/agent/chat', { ... })
// ✅ Correct - Backend actually serves
fetch('/api/v1/agent/simple-chat', { ... })

// ❌ Wrong - Incorrect request format
{ message: "text" }
// ✅ Correct - Backend expects
{ input: "text" }

// ❌ Wrong - Expecting wrong response format
{ response: "text" }
// ✅ Correct - Backend returns
{ output: "text", citations: [] }
```

**Prevention Strategy**:
```javascript
// Create a centralized API configuration
const API_CONFIG = {
    BASE_URL: 'http://localhost:8000',
    ENDPOINTS: {
        CHAT: '/api/v1/agent/simple-chat',
        UPLOAD: '/api/v1/upload/upload',
        QUERY: '/api/v1/upload/query',
        LIST_DOCS: '/api/v1/upload/list'
    },
    FORMATS: {
        CHAT_REQUEST: (message) => ({ input: message }),
        CHAT_RESPONSE: (data) => ({ text: data.output, citations: data.citations })
    }
};

// Use configuration consistently
const response = await fetch(
    `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.CHAT}`,
    {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(API_CONFIG.FORMATS.CHAT_REQUEST(message))
    }
);
```

#### 3. RAG vs Regular Chat Function Conflicts

**Problem**: Multiple chat functions with different logic paths causing confusion.

**Issue Pattern**:
```javascript
// ❌ Problematic - Two different functions with different endpoints
async function getRagResponse(message) {
    // Calls /api/v1/upload/query
}

async function getRegularResponse(message) {
    // Calls /api/v1/agent/simple-chat
}

// Frontend logic decides which to call
if (isRagEnabled && documents.length > 0) {
    response = await getRagResponse(message);  // May fail
} else {
    response = await getRegularResponse(message);  // Works
}
```

**Solution - Unified Approach**:
```javascript
// ✅ Better - Single function that handles both cases
async function getChatResponse(message) {
    try {
        console.log('Making unified chat request');

        // Use single endpoint that handles RAG automatically
        const response = await fetch('/api/v1/agent/simple-chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ input: message })
        });

        if (response.ok) {
            const data = await response.json();

            // Backend automatically provides RAG response if documents available
            return {
                text: data.output,
                citations: data.citations || [],
                hasRAG: (data.citations && data.citations.length > 0)
            };
        }

        throw new Error(`HTTP ${response.status}`);
    } catch (error) {
        console.error('Chat error:', error);
        throw error;
    }
}
```

### Debugging Tools and Techniques

#### Browser Developer Tools Usage

**Console Debugging**:
```javascript
// Add debug mode toggle
const DEBUG_MODE = true;

function debugLog(category, message, data = null) {
    if (DEBUG_MODE) {
        console.group(`🔍 ${category}`);
        console.log(message);
        if (data) console.log('Data:', data);
        console.groupEnd();
    }
}

// Usage in your functions
debugLog('API Request', 'Sending chat message', { endpoint, body });
debugLog('API Response', 'Received response', { status, data });
debugLog('Error', 'Request failed', { error: error.message });
```

**Network Tab Analysis**:
1. Open Developer Tools (F12)
2. Go to Network tab
3. Send a request
4. Look for your API call
5. Check:
   - Request URL (is it correct?)
   - Request Method (POST/GET)
   - Request Headers (Content-Type, etc.)
   - Request Payload (is the format correct?)
   - Response Status (200, 404, 500, etc.)
   - Response Headers (CORS headers present?)
   - Response Body (what did the server return?)

#### CORS Troubleshooting

**Common CORS Errors**:
```
Access to fetch at 'http://localhost:8000/api/v1/agent/simple-chat'
from origin 'file://' has been blocked by CORS policy
```

**Backend CORS Configuration** (FastAPI):
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Frontend CORS Testing**:
```javascript
// Test CORS with a simple request
async function testCORS() {
    try {
        const response = await fetch('http://localhost:8000/', {
            method: 'GET',
            mode: 'cors'
        });
        console.log('CORS test passed:', response.status);
    } catch (error) {
        console.error('CORS test failed:', error);
    }
}
```

### Error Handling Best Practices

#### Graceful Error Display

```javascript
// ❌ Poor error handling
catch (error) {
    alert('Error occurred');
}

// ✅ Better error handling
catch (error) {
    console.error('Detailed error:', error);

    let userMessage;
    if (error.message.includes('fetch')) {
        userMessage = 'Unable to connect to server. Please check if the backend is running.';
    } else if (error.message.includes('400')) {
        userMessage = 'Invalid request format. Please try again.';
    } else if (error.message.includes('500')) {
        userMessage = 'Server error occurred. Please try again later.';
    } else {
        userMessage = 'An unexpected error occurred. Please try again.';
    }

    displayErrorMessage(userMessage);

    // Optional: Send error to monitoring service
    if (window.errorReporting) {
        window.errorReporting.captureException(error);
    }
}

function displayErrorMessage(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.textContent = message;
    errorDiv.style.cssText = `
        background: #fee;
        border: 1px solid #fcc;
        color: #c66;
        padding: 10px;
        margin: 10px 0;
        border-radius: 4px;
    `;

    document.getElementById('messages').appendChild(errorDiv);

    // Auto-remove after 5 seconds
    setTimeout(() => errorDiv.remove(), 5000);
}
```

#### Retry Logic

```javascript
async function fetchWithRetry(url, options, maxRetries = 3) {
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
            console.log(`Attempt ${attempt}/${maxRetries}`);
            const response = await fetch(url, options);

            if (response.ok) {
                return response;
            }

            // Don't retry on client errors (4xx)
            if (response.status >= 400 && response.status < 500) {
                throw new Error(`Client error: ${response.status}`);
            }

            // Retry on server errors (5xx) or network issues
            if (attempt === maxRetries) {
                throw new Error(`Server error after ${maxRetries} attempts: ${response.status}`);
            }

        } catch (error) {
            if (attempt === maxRetries) {
                throw error;
            }

            // Exponential backoff
            const delay = Math.pow(2, attempt) * 1000;
            console.log(`Retrying in ${delay}ms...`);
            await new Promise(resolve => setTimeout(resolve, delay));
        }
    }
}
```

---

## RAG System Integration Lessons

### Key Learnings from Implementation

#### 1. Backend-Frontend API Contract

**Critical Lesson**: Always verify the exact API contract between frontend and backend.

**What We Learned**:
- Frontend expected: `POST /api/v1/agent/simple-chat` with `{input: "message"}`
- Backend initially had: `POST /api/v1/agent/chat` with `{message: "text"}`
- Response format mismatches caused silent failures

**Best Practice**:
```javascript
// Define and test API contracts explicitly
const API_CONTRACT = {
    CHAT_ENDPOINT: {
        url: '/api/v1/agent/simple-chat',
        method: 'POST',
        request: { input: 'string' },
        response: { output: 'string', citations: 'array' }
    }
};

// Test contract compliance
async function testAPIContract() {
    const testMessage = 'Hello, world!';
    const response = await fetch(API_CONTRACT.CHAT_ENDPOINT.url, {
        method: API_CONTRACT.CHAT_ENDPOINT.method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ input: testMessage })
    });

    const data = await response.json();

    // Verify response structure
    console.assert('output' in data, 'Response missing output field');
    console.assert('citations' in data, 'Response missing citations field');
    console.assert(typeof data.output === 'string', 'Output should be string');
    console.assert(Array.isArray(data.citations), 'Citations should be array');
}
```

#### 2. Multiple Chat Function Paths

**Problem Discovered**: Having separate `getRagResponse()` and `getRegularResponse()` functions created complexity and failure points.

**Solution**: Use a unified chat endpoint that automatically handles RAG when documents are available.

```javascript
// ❌ Complex - Multiple functions with different logic
async function sendMessage(message) {
    if (isRagEnabled && documents.length > 0) {
        return await getRagResponse(message);  // Different endpoint
    } else {
        return await getRegularResponse(message);  // Different endpoint
    }
}

// ✅ Simple - Single function, backend handles RAG logic
async function sendMessage(message) {
    return await getChatResponse(message);  // Same endpoint always
}
```

#### 3. Document State Management

**Lesson**: Frontend document state must stay synchronized with backend document availability.

**Implementation**:
```javascript
class DocumentManager {
    constructor() {
        this.documents = [];
        this.isRagEnabled = false;
    }

    async uploadDocument(file) {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch('/api/v1/upload/upload', {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            const result = await response.json();
            this.documents.push(result);
            this.isRagEnabled = true;
            this.updateUI();
            return result;
        }

        throw new Error('Upload failed');
    }

    async refreshDocumentList() {
        const response = await fetch('/api/v1/upload/list');
        if (response.ok) {
            const data = await response.json();
            this.documents = data.documents;
            this.isRagEnabled = data.total > 0;
            this.updateUI();
        }
    }

    updateUI() {
        // Update RAG indicator
        const indicator = document.getElementById('ragIndicator');
        if (indicator) {
            indicator.style.display = this.isRagEnabled ? 'block' : 'none';
        }

        // Update document list
        const docList = document.getElementById('documentList');
        if (docList) {
            docList.innerHTML = this.documents.map(doc =>
                `<div class="document-item">${doc.name} (${doc.chunks} chunks)</div>`
            ).join('');
        }
    }
}
```

#### 4. Error Message Specificity

**Lesson**: Generic error messages like "Sorry, I encountered an error" provide no debugging value.

**Better Approach**:
```javascript
// ❌ Generic error handling
catch (error) {
    showMessage('Sorry, I encountered an error. Please try again.');
}

// ✅ Specific error handling
catch (error) {
    let specificMessage;

    if (error.message.includes('Failed to fetch')) {
        specificMessage = 'Cannot connect to GremlinsAI backend. Please ensure the server is running on http://localhost:8000';
    } else if (error.message.includes('404')) {
        specificMessage = 'API endpoint not found. Please check if you\'re using the correct GremlinsAI version.';
    } else if (error.message.includes('422')) {
        specificMessage = 'Invalid request format. Please check your message and try again.';
    } else if (error.message.includes('500')) {
        specificMessage = 'GremlinsAI server error. Please check the server logs and try again.';
    } else {
        specificMessage = `Unexpected error: ${error.message}. Please check the console for details.`;
    }

    showMessage(specificMessage);
    console.error('Detailed error information:', error);
}
```

#### 5. Development vs Production Configuration

**Lesson**: Hardcoded localhost URLs and development settings need environment-specific configuration.

```javascript
// ✅ Environment-aware configuration
class GremlinsAIConfig {
    constructor() {
        this.environment = this.detectEnvironment();
        this.config = this.getConfigForEnvironment();
    }

    detectEnvironment() {
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
            return 'development';
        } else if (window.location.hostname.includes('staging')) {
            return 'staging';
        } else {
            return 'production';
        }
    }

    getConfigForEnvironment() {
        const configs = {
            development: {
                baseURL: 'http://localhost:8000',
                debug: true,
                timeout: 30000
            },
            staging: {
                baseURL: 'https://staging-api.gremlinsai.com',
                debug: true,
                timeout: 15000
            },
            production: {
                baseURL: 'https://api.gremlinsai.com',
                debug: false,
                timeout: 10000
            }
        };

        return configs[this.environment];
    }

    getEndpoint(path) {
        return `${this.config.baseURL}${path}`;
    }
}

// Usage
const config = new GremlinsAIConfig();
const chatEndpoint = config.getEndpoint('/api/v1/agent/simple-chat');
```

### Testing Strategies

#### Unit Testing Chat Functions

```javascript
// Test chat function with mocked responses
describe('Chat Functions', () => {
    beforeEach(() => {
        global.fetch = jest.fn();
    });

    test('should handle successful chat response', async () => {
        const mockResponse = {
            output: 'Test response',
            citations: [{ document: 'test.pdf', page: 1 }]
        };

        fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => mockResponse
        });

        const result = await getChatResponse('test message');

        expect(result.text).toBe('Test response');
        expect(result.citations).toHaveLength(1);
        expect(fetch).toHaveBeenCalledWith(
            expect.stringContaining('/api/v1/agent/simple-chat'),
            expect.objectContaining({
                method: 'POST',
                body: JSON.stringify({ input: 'test message' })
            })
        );
    });

    test('should handle API errors gracefully', async () => {
        fetch.mockResolvedValueOnce({
            ok: false,
            status: 500,
            text: async () => 'Internal Server Error'
        });

        await expect(getChatResponse('test')).rejects.toThrow('HTTP 500');
    });
});
```

#### Integration Testing

```javascript
// Test full chat flow with real backend
describe('Integration Tests', () => {
    const testConfig = {
        baseURL: 'http://localhost:8000',
        timeout: 5000
    };

    test('should complete full chat workflow', async () => {
        // 1. Check backend availability
        const healthResponse = await fetch(`${testConfig.baseURL}/`);
        expect(healthResponse.ok).toBe(true);

        // 2. Upload test document
        const formData = new FormData();
        formData.append('file', new Blob(['Test content'], { type: 'text/plain' }), 'test.txt');

        const uploadResponse = await fetch(`${testConfig.baseURL}/api/v1/upload/upload`, {
            method: 'POST',
            body: formData
        });
        expect(uploadResponse.ok).toBe(true);

        // 3. Send chat message
        const chatResponse = await fetch(`${testConfig.baseURL}/api/v1/agent/simple-chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ input: 'What is in the document?' })
        });

        expect(chatResponse.ok).toBe(true);
        const chatData = await chatResponse.json();
        expect(chatData).toHaveProperty('output');
        expect(chatData).toHaveProperty('citations');
    });
});
```

### Performance Optimization

#### Request Debouncing

```javascript
// Prevent rapid-fire requests
class ChatManager {
    constructor() {
        this.requestTimeout = null;
        this.isProcessing = false;
    }

    async sendMessage(message) {
        // Prevent duplicate requests
        if (this.isProcessing) {
            console.log('Request already in progress, ignoring');
            return;
        }

        // Debounce rapid requests
        if (this.requestTimeout) {
            clearTimeout(this.requestTimeout);
        }

        this.requestTimeout = setTimeout(async () => {
            this.isProcessing = true;
            try {
                const response = await this.performChatRequest(message);
                this.handleResponse(response);
            } catch (error) {
                this.handleError(error);
            } finally {
                this.isProcessing = false;
            }
        }, 300); // 300ms debounce
    }
}
```

#### Response Caching

```javascript
class ResponseCache {
    constructor(maxSize = 50, ttl = 300000) { // 5 minutes TTL
        this.cache = new Map();
        this.maxSize = maxSize;
        this.ttl = ttl;
    }

    get(key) {
        const item = this.cache.get(key);
        if (!item) return null;

        if (Date.now() - item.timestamp > this.ttl) {
            this.cache.delete(key);
            return null;
        }

        return item.data;
    }

    set(key, data) {
        // Remove oldest items if cache is full
        if (this.cache.size >= this.maxSize) {
            const firstKey = this.cache.keys().next().value;
            this.cache.delete(firstKey);
        }

        this.cache.set(key, {
            data,
            timestamp: Date.now()
        });
    }
}

// Usage in chat function
const responseCache = new ResponseCache();

async function getCachedChatResponse(message) {
    const cacheKey = `chat:${message}`;
    const cached = responseCache.get(cacheKey);

    if (cached) {
        console.log('Using cached response');
        return cached;
    }

    const response = await getChatResponse(message);
    responseCache.set(cacheKey, response);
    return response;
}
```
