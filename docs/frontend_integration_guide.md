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
Create a `.env` file in your frontend project:
```env
REACT_APP_API_BASE_URL=http://localhost:8000/api/v1
REACT_APP_WS_BASE_URL=ws://localhost:8000/api/v1/ws
REACT_APP_API_KEY=your_api_key_here
```

## Authentication

### API Key Authentication
GremlinsAI uses API key authentication for secure access:

```javascript
const apiClient = axios.create({
  baseURL: process.env.REACT_APP_API_BASE_URL,
  headers: {
    'Authorization': `Bearer ${process.env.REACT_APP_API_KEY}`,
    'Content-Type': 'application/json'
  }
});
```

### Request Interceptor Setup
```javascript
apiClient.interceptors.request.use(
  (config) => {
    // Add request ID for tracking
    config.headers['X-Request-ID'] = generateRequestId();
    return config;
  },
  (error) => Promise.reject(error)
);

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Handle common errors
    if (error.response?.status === 401) {
      // Handle authentication error
      redirectToLogin();
    }
    return Promise.reject(error);
  }
);
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
    const response = await apiClient.post('/multi-agent/workflow', {
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
