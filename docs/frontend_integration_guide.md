# GremlinsAI Frontend Integration Guide

## Table of Contents
1. [Getting Started](#getting-started)
2. [Authentication](#authentication)
3. [API Endpoints](#api-endpoints)
4. [WebSocket Connections](#websocket-connections)
5. [Error Handling](#error-handling)
6. [Rate Limiting](#rate-limiting)
7. [TypeScript Definitions](#typescript-definitions)
8. [Best Practices](#best-practices)

## Getting Started

### Base URL Configuration
```javascript
const API_BASE_URL = 'http://localhost:8000/api/v1';
const WS_BASE_URL = 'ws://localhost:8000/api/v1/ws';
```

### Environment Setup

Environment variables vary by framework. Choose the appropriate format for your project:

#### React (Create React App)
Create a `.env` file in your project root:
```env
REACT_APP_API_BASE_URL=http://localhost:8000/api/v1
REACT_APP_WS_BASE_URL=ws://localhost:8000/api/v1/ws
REACT_APP_API_KEY=your_api_key_here
REACT_APP_DEFAULT_USER_ID=default-user
REACT_APP_REQUEST_TIMEOUT=30000
REACT_APP_ENABLE_WEBSOCKETS=true
REACT_APP_DEBUG_MODE=false
```

#### Vue.js (Vite)
Create a `.env` file in your project root:
```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_WS_BASE_URL=ws://localhost:8000/api/v1/ws
VITE_API_KEY=your_api_key_here
VITE_DEFAULT_USER_ID=default-user
VITE_REQUEST_TIMEOUT=30000
VITE_ENABLE_WEBSOCKETS=true
VITE_DEBUG_MODE=false
```

#### Next.js
Create a `.env.local` file in your project root:
```env
# Public variables (available in browser)
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_BASE_URL=ws://localhost:8000/api/v1/ws
NEXT_PUBLIC_DEFAULT_USER_ID=default-user
NEXT_PUBLIC_REQUEST_TIMEOUT=30000
NEXT_PUBLIC_ENABLE_WEBSOCKETS=true

# Server-side only variables
GREMLINS_API_KEY=your_api_key_here
DATABASE_URL=postgresql://user:password@localhost:5432/gremlinsai
NEXTAUTH_SECRET=your_nextauth_secret
```

#### Angular
Create environment files in `src/environments/`:

**environment.ts:**
```typescript
export const environment = {
  production: false,
  apiBaseUrl: 'http://localhost:8000/api/v1',
  wsBaseUrl: 'ws://localhost:8000/api/v1/ws',
  apiKey: 'your_api_key_here',
  defaultUserId: 'default-user',
  requestTimeout: 30000,
  enableWebSockets: true,
  debugMode: true,
};
```

**environment.prod.ts:**
```typescript
export const environment = {
  production: true,
  apiBaseUrl: 'https://api.yourdomain.com/api/v1',
  wsBaseUrl: 'wss://api.yourdomain.com/api/v1/ws',
  apiKey: process.env['GREMLINS_API_KEY'] || '',
  defaultUserId: 'default-user',
  requestTimeout: 30000,
  enableWebSockets: true,
  debugMode: false,
};
```

## Authentication

### API Key Authentication
GremlinsAI uses API key authentication for secure access. Here's how to set up the API client using the native fetch API:

```typescript
class GremlinsAPIClient {
  private baseURL: string;
  private apiKey: string;
  private requestTimeout: number;

  constructor(baseURL: string, apiKey: string, options?: { timeout?: number }) {
    if (!baseURL) {
      throw new Error('API base URL is required');
    }
    if (!apiKey || apiKey.trim() === '') {
      throw new Error('API key is required and cannot be empty');
    }

    this.baseURL = baseURL;
    this.apiKey = apiKey.trim();
    this.requestTimeout = options?.timeout || 30000;
  }

  private async makeRequest<T>(
    method: 'GET' | 'POST' | 'PUT' | 'DELETE',
    endpoint: string,
    data?: any,
    params?: Record<string, any>
  ): Promise<T> {
    const url = new URL(endpoint, this.baseURL);

    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        url.searchParams.append(key, String(value));
      });
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.requestTimeout);

    try {
      const response = await fetch(url.toString(), {
        method,
        headers: {
          'Authorization': `Bearer ${this.apiKey}`,
          'Content-Type': 'application/json',
          'X-Request-ID': this.generateRequestId(),
          'X-Client-Version': '1.0.0',
        },
        body: data ? JSON.stringify(data) : undefined,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(this.handleError({ response: { data: errorData, status: response.status } }));
      }

      return response.json();
    } catch (error: any) {
      clearTimeout(timeoutId);

      if (error.name === 'AbortError') {
        throw new Error('Request timeout - please try again');
      }

      throw error;
    }
  }

  private generateRequestId(): string {
    return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private handleError(error: any): string {
    if (error.response?.data) {
      const status = error.response.status;

      switch (status) {
        case 401:
          return 'Authentication failed. Please check your API key.';
        case 403:
          return 'Access forbidden. You do not have permission to perform this action.';
        case 404:
          return 'Resource not found. Please check the request URL.';
        case 429:
          return 'Too many requests. Please wait before trying again.';
        case 500:
          return 'Server error. Please try again later.';
        default:
          return error.response.data.error_message || 'An unexpected error occurred.';
      }
    }

    return error.message || 'Network error occurred.';
  }
}

// Create API client instance
const createAPIClient = (): GremlinsAPIClient => {
  const baseURL = process.env.REACT_APP_API_BASE_URL; // Adjust prefix for your framework
  const apiKey = process.env.REACT_APP_API_KEY;

  if (!baseURL) {
    throw new Error('API base URL environment variable is required');
  }

  if (!apiKey) {
    throw new Error('API key environment variable is required');
  }

  return new GremlinsAPIClient(baseURL, apiKey, {
    timeout: parseInt(process.env.REACT_APP_REQUEST_TIMEOUT || '30000', 10)
  });
};

const apiClient = createAPIClient();
```

## API Endpoints

### Core Agent Endpoints

#### Simple Agent Invocation
```javascript
async function invokeAgent(input) {
  try {
    const response = await apiClient.post('/agent/invoke', {
      input: input
    });
    return response.data;
  } catch (error) {
    throw new Error(`Agent invocation failed: ${error.message}`);
  }
}
```

#### Chat with Conversation History
```javascript
async function chatWithAgent(input, conversationId = null, saveConversation = true) {
  try {
    const response = await apiClient.post('/agent/chat', {
      input,
      conversation_id: conversationId,
      save_conversation: saveConversation,
      use_multi_agent: false
    });
    return response.data;
  } catch (error) {
    throw new Error(`Chat failed: ${error.message}`);
  }
}
```

### Conversation Management

#### Create New Conversation
```javascript
async function createConversation(title, userId = 'default-user') {
  try {
    const response = await apiClient.post('/history/conversations', {
      title,
      user_id: userId
    });
    return response.data;
  } catch (error) {
    throw new Error(`Failed to create conversation: ${error.message}`);
  }
}
```

#### Get Conversation Messages
```javascript
async function getConversationMessages(conversationId, limit = 50, offset = 0) {
  try {
    const response = await apiClient.get(
      `/history/conversations/${conversationId}/messages`,
      { params: { limit, offset } }
    );
    return response.data;
  } catch (error) {
    throw new Error(`Failed to get messages: ${error.message}`);
  }
}
```

#### List User Conversations
```javascript
async function getUserConversations(userId = 'default-user', limit = 20, offset = 0) {
  try {
    const response = await apiClient.get('/history/conversations', {
      params: { user_id: userId, limit, offset }
    });
    return response.data;
  } catch (error) {
    throw new Error(`Failed to get conversations: ${error.message}`);
  }
}
```

### Multi-Agent Workflows

#### Execute Multi-Agent Workflow
```javascript
async function executeMultiAgentWorkflow(input, workflowType = 'research_analyze_write') {
  try {
    const response = await apiClient.post('/multi-agent/execute', {
      input,
      workflow_type: workflowType,
      save_conversation: true
    });
    return response.data;
  } catch (error) {
    throw new Error(`Multi-agent workflow failed: ${error.message}`);
  }
}
```

#### Get Agent Capabilities
```javascript
async function getAgentCapabilities() {
  try {
    const response = await apiClient.get('/multi-agent/capabilities');
    return response.data;
  } catch (error) {
    throw new Error(`Failed to get agent capabilities: ${error.message}`);
  }
}
```

### Document Management & RAG

#### Upload Document
```javascript
async function uploadDocument(file, metadata = {}) {
  try {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('metadata', JSON.stringify(metadata));

    const response = await fetch(`${API_BASE_URL}/documents/upload`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
      },
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Upload failed: ${response.statusText}`);
    }

    return response.json();
  } catch (error) {
    throw new Error(`Document upload failed: ${error.message}`);
  }
}
```

#### Search Documents
```javascript
async function searchDocuments(query, options = {}) {
  try {
    const response = await apiClient.post('/documents/search', {
      query,
      limit: options.limit || 10,
      threshold: options.threshold || 0.7,
      filters: options.filters || {}
    });
    return response.data;
  } catch (error) {
    throw new Error(`Document search failed: ${error.message}`);
  }
}
```

#### Get Document by ID
```javascript
async function getDocument(documentId) {
  try {
    const response = await apiClient.get(`/documents/${documentId}`);
    return response.data;
  } catch (error) {
    throw new Error(`Failed to get document: ${error.message}`);
  }
}
```

### Task Orchestration

#### Create Task
```javascript
async function createTask(taskData) {
  try {
    const response = await apiClient.post('/orchestrator/tasks', {
      name: taskData.name,
      type: taskData.type,
      parameters: taskData.parameters,
      priority: taskData.priority || 'medium',
      scheduled_for: taskData.scheduledFor
    });
    return response.data;
  } catch (error) {
    throw new Error(`Task creation failed: ${error.message}`);
  }
}
```

#### Get Task Status
```javascript
async function getTaskStatus(taskId) {
  try {
    const response = await apiClient.get(`/orchestrator/tasks/${taskId}`);
    return response.data;
  } catch (error) {
    throw new Error(`Failed to get task status: ${error.message}`);
  }
}
```

#### List Tasks
```javascript
async function listTasks(filters = {}) {
  try {
    const response = await apiClient.get('/orchestrator/tasks', {
      params: {
        status: filters.status,
        type: filters.type,
        limit: filters.limit || 20,
        offset: filters.offset || 0
      }
    });
    return response.data;
  } catch (error) {
    throw new Error(`Failed to list tasks: ${error.message}`);
  }
}
```

### Real-time API

#### Subscribe to Events
```javascript
async function subscribeToEvents(eventTypes, callback) {
  try {
    const response = await apiClient.post('/realtime/subscribe', {
      event_types: eventTypes,
      callback_url: callback
    });
    return response.data;
  } catch (error) {
    throw new Error(`Subscription failed: ${error.message}`);
  }
}
```

#### Get Real-time Status
```javascript
async function getRealtimeStatus() {
  try {
    const response = await apiClient.get('/realtime/status');
    return response.data;
  } catch (error) {
    throw new Error(`Failed to get real-time status: ${error.message}`);
  }
}
```

### Multi-Modal Processing

#### Process Audio
```javascript
async function processAudio(audioFile, options = {}) {
  try {
    const formData = new FormData();
    formData.append('audio', audioFile);
    formData.append('options', JSON.stringify({
      transcribe: options.transcribe !== false,
      language: options.language || 'auto',
      format: options.format || 'wav'
    }));

    const response = await fetch(`${API_BASE_URL}/multimodal/audio`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
      },
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Audio processing failed: ${response.statusText}`);
    }

    return response.json();
  } catch (error) {
    throw new Error(`Audio processing failed: ${error.message}`);
  }
}
```

#### Process Image
```javascript
async function processImage(imageFile, options = {}) {
  try {
    const formData = new FormData();
    formData.append('image', imageFile);
    formData.append('options', JSON.stringify({
      analyze: options.analyze !== false,
      extract_text: options.extractText || false,
      detect_objects: options.detectObjects || false
    }));

    const response = await fetch(`${API_BASE_URL}/multimodal/image`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
      },
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Image processing failed: ${response.statusText}`);
    }

    return response.json();
  } catch (error) {
    throw new Error(`Image processing failed: ${error.message}`);
  }
}
```

### GraphQL API

#### Execute GraphQL Query
```javascript
async function executeGraphQLQuery(query, variables = {}) {
  try {
    const response = await fetch(`${API_BASE_URL.replace('/api/v1', '')}/graphql`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query,
        variables
      }),
    });

    if (!response.ok) {
      throw new Error(`GraphQL query failed: ${response.statusText}`);
    }

    const result = await response.json();

    if (result.errors) {
      throw new Error(`GraphQL errors: ${result.errors.map(e => e.message).join(', ')}`);
    }

    return result.data;
  } catch (error) {
    throw new Error(`GraphQL query failed: ${error.message}`);
  }
}
```

#### Example GraphQL Queries
```javascript
// Get conversation with messages
const GET_CONVERSATION = `
  query GetConversation($id: ID!) {
    conversation(id: $id) {
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
`;

// Execute the query
const conversationData = await executeGraphQLQuery(GET_CONVERSATION, {
  id: 'conversation-id'
});
```

### Developer Portal Integration

#### Get API Documentation
```javascript
async function getAPIDocumentation() {
  try {
    const response = await apiClient.get('/developer-portal/docs');
    return response.data;
  } catch (error) {
    throw new Error(`Failed to get API documentation: ${error.message}`);
  }
}
```

#### Get SDK Information
```javascript
async function getSDKInfo() {
  try {
    const response = await apiClient.get('/developer-portal/sdks');
    return response.data;
  } catch (error) {
    throw new Error(`Failed to get SDK information: ${error.message}`);
  }
}
```

## WebSocket Connections

### Real-time Chat Connection
```javascript
class GremlinsWebSocket {
  constructor(url, apiKey) {
    this.url = url;
    this.apiKey = apiKey;
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000;
  }

  connect() {
    try {
      this.ws = new WebSocket(`${this.url}/chat?token=${this.apiKey}`);
      
      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.reconnectAttempts = 0;
      };

      this.ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        this.handleMessage(data);
      };

      this.ws.onclose = () => {
        console.log('WebSocket disconnected');
        this.handleReconnect();
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
    }
  }

  sendMessage(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      throw new Error('WebSocket is not connected');
    }
  }

  handleMessage(data) {
    // Override this method to handle incoming messages
    console.log('Received message:', data);
  }

  handleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      setTimeout(() => {
        this.reconnectAttempts++;
        console.log(`Reconnecting... Attempt ${this.reconnectAttempts}`);
        this.connect();
      }, this.reconnectDelay * this.reconnectAttempts);
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
    }
  }
}
```

### Usage Example
```javascript
const wsClient = new GremlinsWebSocket(
  process.env.REACT_APP_WS_BASE_URL,
  process.env.REACT_APP_API_KEY
);

wsClient.handleMessage = (data) => {
  if (data.type === 'agent_response') {
    updateChatUI(data.message);
  } else if (data.type === 'error') {
    showError(data.error);
  }
};

wsClient.connect();

// Send a message
wsClient.sendMessage({
  type: 'chat',
  input: 'Hello, how can you help me?',
  conversation_id: currentConversationId
});
```

## Error Handling

### Standard Error Response Format
```typescript
interface GremlinsError {
  error_code: string;
  error_message: string;
  error_details?: string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  category: string;
  suggested_action: string;
  documentation_url: string;
  request_id: string;
  timestamp: string;
  affected_services: string[];
  validation_errors?: ValidationError[];
}

interface ValidationError {
  field: string;
  message: string;
  invalid_value: any;
  expected_type: string;
}
```

### Error Handling Utility
```javascript
class ErrorHandler {
  static handle(error) {
    if (error.response?.data) {
      const errorData = error.response.data;
      
      switch (errorData.error_code) {
        case 'GREMLINS_1001':
          return 'Authentication failed. Please check your API key.';
        case 'GREMLINS_1003':
          return 'Invalid input. Please check your request data.';
        case 'GREMLINS_2001':
          return 'Agent processing failed. Please try again.';
        case 'GREMLINS_3001':
          return 'Database error. Please contact support.';
        case 'GREMLINS_4001':
          return 'External service unavailable. Please try again later.';
        default:
          return errorData.error_message || 'An unexpected error occurred.';
      }
    }
    
    return error.message || 'Network error occurred.';
  }

  static isRetryable(error) {
    const retryableCodes = ['GREMLINS_4001', 'GREMLINS_5001'];
    return error.response?.data?.error_code && 
           retryableCodes.includes(error.response.data.error_code);
  }
}
```

## Rate Limiting

### Rate Limit Headers
Monitor these headers in responses:
- `X-RateLimit-Limit`: Maximum requests per window
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Time when the rate limit resets

### Rate Limit Handling
```javascript
class RateLimitHandler {
  constructor() {
    this.requestQueue = [];
    this.isProcessing = false;
  }

  async makeRequest(requestFn) {
    return new Promise((resolve, reject) => {
      this.requestQueue.push({ requestFn, resolve, reject });
      this.processQueue();
    });
  }

  async processQueue() {
    if (this.isProcessing || this.requestQueue.length === 0) {
      return;
    }

    this.isProcessing = true;

    while (this.requestQueue.length > 0) {
      const { requestFn, resolve, reject } = this.requestQueue.shift();

      try {
        const response = await requestFn();
        
        // Check rate limit headers
        const remaining = parseInt(response.headers['x-ratelimit-remaining'] || '0');
        const resetTime = parseInt(response.headers['x-ratelimit-reset'] || '0');

        if (remaining <= 1 && resetTime > Date.now()) {
          // Wait until rate limit resets
          const waitTime = resetTime - Date.now();
          await new Promise(resolve => setTimeout(resolve, waitTime));
        }

        resolve(response);
      } catch (error) {
        if (error.response?.status === 429) {
          // Rate limited, wait and retry
          const retryAfter = parseInt(error.response.headers['retry-after'] || '60');
          await new Promise(resolve => setTimeout(resolve, retryAfter * 1000));
          this.requestQueue.unshift({ requestFn, resolve, reject });
        } else {
          reject(error);
        }
      }
    }

    this.isProcessing = false;
  }
}
```

## TypeScript Definitions

### Core API Types
```typescript
// API Response Types
interface AgentResponse {
  output: string;
  conversation_id?: string;
  message_id?: string;
  context_used: boolean;
  execution_time: number;
  extra_data?: {
    agent_used: boolean;
    context_used: boolean;
    execution_time: number;
  };
}

interface ConversationResponse {
  id: string;
  title: string;
  user_id: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  last_message_at?: string;
}

interface MessageResponse {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
  tool_calls?: Record<string, any>;
  extra_data?: Record<string, any>;
}

interface MessageListResponse {
  conversation_id: string;
  messages: MessageResponse[];
  total: number;
  limit: number;
  offset: number;
}

interface ConversationListResponse {
  conversations: ConversationResponse[];
  total: number;
  limit: number;
  offset: number;
}

// Request Types
interface ChatRequest {
  input: string;
  conversation_id?: string;
  save_conversation?: boolean;
  use_multi_agent?: boolean;
}

interface ConversationCreateRequest {
  title: string;
  user_id?: string;
}

interface MultiAgentWorkflowRequest {
  input: string;
  workflow_type: 'research_analyze_write' | 'simple_research' | 'complex_analysis';
  save_conversation?: boolean;
}

// WebSocket Types
interface WebSocketMessage {
  type: 'chat' | 'agent_response' | 'error' | 'status' | 'ping' | 'pong';
  data: any;
  timestamp: string;
  request_id?: string;
}

interface WebSocketConfig {
  url: string;
  apiKey: string;
  reconnectAttempts?: number;
  reconnectDelay?: number;
  heartbeatInterval?: number;
}

// Hook Return Types
interface UseGremlinsAPIReturn {
  conversations: ConversationResponse[];
  currentConversation: ConversationResponse | null;
  messages: MessageResponse[];
  isLoading: boolean;
  error: string | null;
  sendMessage: (input: string, conversationId?: string) => Promise<void>;
  createConversation: (title: string) => Promise<ConversationResponse>;
  switchConversation: (conversationId: string) => Promise<void>;
  loadMoreMessages: () => Promise<void>;
  refreshConversations: () => Promise<void>;
  clearError: () => void;
}

interface UseWebSocketReturn {
  connectionStatus: 'connecting' | 'connected' | 'disconnected' | 'error';
  lastMessage: WebSocketMessage | null;
  sendMessage: (message: Omit<WebSocketMessage, 'timestamp'>) => void;
  connect: () => void;
  disconnect: () => void;
}

interface UseConversationsReturn {
  conversations: ConversationResponse[];
  currentConversation: ConversationResponse | null;
  isLoading: boolean;
  error: string | null;
  hasMore: boolean;
  loadConversations: (reset?: boolean) => Promise<void>;
  createConversation: (title: string) => Promise<ConversationResponse>;
  selectConversation: (conversation: ConversationResponse) => void;
  deleteConversation: (conversationId: string) => Promise<void>;
  updateConversationTitle: (conversationId: string, title: string) => Promise<void>;
  refreshConversations: () => Promise<void>;
  loadMoreConversations: () => Promise<void>;
  clearError: () => void;
}

// Component Props Types
interface ChatInterfaceProps {
  className?: string;
  onConversationChange?: (conversation: ConversationResponse | null) => void;
  onMessageSent?: (message: MessageResponse) => void;
  onError?: (error: string) => void;
}

interface MessageListProps {
  messages: MessageResponse[];
  isLoading?: boolean;
  onLoadMore?: () => void;
  hasMore?: boolean;
  className?: string;
}

interface MessageInputProps {
  onSendMessage: (input: string) => void;
  disabled?: boolean;
  placeholder?: string;
  maxLength?: number;
  className?: string;
}

interface ConversationSidebarProps {
  conversations: ConversationResponse[];
  currentConversation: ConversationResponse | null;
  onConversationSelect: (conversation: ConversationResponse) => void;
  onNewConversation: () => void;
  isLoading?: boolean;
  className?: string;
}

// Utility Types
interface OptimisticMessage extends Omit<MessageResponse, 'id'> {
  id: string;
  isOptimistic?: boolean;
  isPending?: boolean;
  error?: string;
}

interface RateLimitHandler {
  makeRequest<T>(requestFn: () => Promise<T>): Promise<T>;
}

// Document Types
interface DocumentMetadata {
  title?: string;
  description?: string;
  tags?: string[];
  category?: string;
}

interface DocumentResponse {
  id: string;
  filename: string;
  content_type: string;
  size: number;
  metadata: DocumentMetadata;
  created_at: string;
  updated_at: string;
}

interface DocumentSearchRequest {
  query: string;
  limit?: number;
  threshold?: number;
  filters?: Record<string, any>;
}

// Task Types
interface TaskRequest {
  name: string;
  type: string;
  parameters: Record<string, any>;
  priority?: 'low' | 'medium' | 'high';
  scheduledFor?: string;
}

interface TaskResponse {
  id: string;
  name: string;
  type: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  parameters: Record<string, any>;
  result?: any;
  error?: string;
  created_at: string;
  updated_at: string;
}

// Multi-modal Types
interface AudioProcessingOptions {
  transcribe?: boolean;
  language?: string;
  format?: string;
}

interface ImageProcessingOptions {
  analyze?: boolean;
  extractText?: boolean;
  detectObjects?: boolean;
}

interface MultiModalResponse {
  id: string;
  type: 'audio' | 'image' | 'video';
  processing_status: 'processing' | 'completed' | 'failed';
  results: Record<string, any>;
  created_at: string;
}
```

### API Client Class
```typescript
class GremlinsAPIClient {
  private baseURL: string;
  private apiKey: string;
  private rateLimitHandler: RateLimitHandler;

  constructor(baseURL: string, apiKey: string) {
    this.baseURL = baseURL;
    this.apiKey = apiKey;
    this.rateLimitHandler = new RateLimitHandler();
  }

  async invokeAgent(input: string): Promise<AgentResponse> {
    return this.rateLimitHandler.makeRequest(() =>
      this.makeRequest<AgentResponse>('POST', '/agent/invoke', { input })
    );
  }

  async chat(request: ChatRequest): Promise<AgentResponse> {
    return this.rateLimitHandler.makeRequest(() =>
      this.makeRequest<AgentResponse>('POST', '/agent/chat', request)
    );
  }

  async createConversation(request: ConversationCreateRequest): Promise<ConversationResponse> {
    return this.rateLimitHandler.makeRequest(() =>
      this.makeRequest<ConversationResponse>('POST', '/history/conversations', request)
    );
  }

  async getConversationMessages(
    conversationId: string,
    limit = 50,
    offset = 0
  ): Promise<MessageListResponse> {
    return this.rateLimitHandler.makeRequest(() =>
      this.makeRequest<MessageListResponse>(
        'GET',
        `/history/conversations/${conversationId}/messages`,
        null,
        { limit, offset }
      )
    );
  }

  private async makeRequest<T>(
    method: 'GET' | 'POST' | 'PUT' | 'DELETE',
    endpoint: string,
    data?: any,
    params?: Record<string, any>
  ): Promise<T> {
    const url = new URL(endpoint, this.baseURL);

    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        url.searchParams.append(key, String(value));
      });
    }

    const response = await fetch(url.toString(), {
      method,
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json',
        'X-Request-ID': this.generateRequestId(),
      },
      body: data ? JSON.stringify(data) : undefined,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(ErrorHandler.handle({ response: { data: errorData } }));
    }

    return response.json();
  }

  private generateRequestId(): string {
    return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}
```

## Testing

### Unit Testing

#### Testing API Client
```typescript
// api.test.ts
import { GremlinsAPIClient } from './api';

global.fetch = jest.fn();
const mockFetch = fetch as jest.MockedFunction<typeof fetch>;

describe('GremlinsAPIClient', () => {
  let apiClient: GremlinsAPIClient;

  beforeEach(() => {
    jest.clearAllMocks();
    apiClient = new GremlinsAPIClient('https://api.test.com/v1', 'test-key');
  });

  it('makes authenticated requests', async () => {
    const mockResponse = { output: 'Test response' };
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    } as Response);

    const result = await apiClient.invokeAgent('Test input');
    expect(result).toEqual(mockResponse);
  });
});
```

#### Testing React Components
```typescript
// ChatInterface.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { ChatInterface } from './ChatInterface';

jest.mock('../hooks/useGremlinsAPI', () => ({
  useGremlinsAPI: () => ({
    messages: [],
    sendMessage: jest.fn(),
  }),
}));

describe('ChatInterface', () => {
  it('renders welcome screen', () => {
    render(<ChatInterface />);
    expect(screen.getByText('Welcome to GremlinsAI')).toBeInTheDocument();
  });
});
```

### End-to-End Testing

#### Cypress Configuration
```typescript
// cypress/e2e/chat-flow.cy.ts
describe('Chat Flow', () => {
  it('completes full chat interaction', () => {
    cy.intercept('POST', '/api/v1/agent/chat', { fixture: 'chat-response.json' });
    cy.visit('/');
    cy.get('[data-testid="message-input"]').type('Hello');
    cy.get('[data-testid="send-button"]').click();
    cy.get('[data-testid="message-list"]').should('contain', 'Hello');
  });
});
```

## Best Practices

### 1. State Management
```typescript
// React Context for Global State
interface GremlinsContextType {
  conversations: ConversationResponse[];
  currentConversation: ConversationResponse | null;
  messages: MessageResponse[];
  isLoading: boolean;
  error: string | null;
  apiClient: GremlinsAPIClient;
}

const GremlinsContext = createContext<GremlinsContextType | null>(null);

export const useGremlins = () => {
  const context = useContext(GremlinsContext);
  if (!context) {
    throw new Error('useGremlins must be used within a GremlinsProvider');
  }
  return context;
};
```

### 2. Performance Optimization
```typescript
// Debounced search
const useDebounce = (value: string, delay: number) => {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
};

// Virtual scrolling for large message lists
const useVirtualScrolling = (items: any[], itemHeight: number, containerHeight: number) => {
  const [scrollTop, setScrollTop] = useState(0);

  const startIndex = Math.floor(scrollTop / itemHeight);
  const endIndex = Math.min(
    startIndex + Math.ceil(containerHeight / itemHeight) + 1,
    items.length
  );

  const visibleItems = items.slice(startIndex, endIndex);

  return {
    visibleItems,
    startIndex,
    totalHeight: items.length * itemHeight,
    offsetY: startIndex * itemHeight,
    onScroll: (e: React.UIEvent) => setScrollTop(e.currentTarget.scrollTop),
  };
};
```

---

## Next Steps

1. **Explore Example Implementations**: Check out the example projects in the `examples/frontend/` directory
2. **Set Up Development Environment**: Follow the setup instructions in each example's README
3. **Customize for Your Needs**: Use the examples as starting points and modify them for your specific requirements
4. **Join the Community**: Contribute improvements and share your implementations

For more detailed examples and complete implementations, see:
- [Chat Interface Example](../examples/frontend/chat-ui/)
- [Agent Management Example](../examples/frontend/agent-dashboard/)
- [Complete System Example](../examples/frontend/full-system/)
