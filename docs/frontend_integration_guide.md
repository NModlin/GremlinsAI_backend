# GremlinsAI Frontend Integration Guide

> **🚨 Having Issues?** Check the [Frontend Troubleshooting Guide](frontend_troubleshooting_guide.md) for common problems and solutions.

> **📚 Need More Details?** See the [Comprehensive Frontend Integration Guide](frontend_integration_comprehensive.md) for advanced features and complete examples. (v9.0.0)

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

### Base URL Configuration (v9.0.0)
```javascript
const API_BASE_URL = 'http://localhost:8000/api/v1';
const WS_BASE_URL = 'ws://localhost:8000/api/v1/ws';
const GRAPHQL_URL = 'http://localhost:8000/graphql';
const DOCS_BASE_URL = 'http://localhost:8000/docs';
const DEVELOPER_PORTAL_URL = 'http://localhost:8000/developer-portal';

// Version information
const API_VERSION = '9.0.0';
const TOTAL_ENDPOINTS = 103;
const SUPPORTED_FEATURES = [
  'REST API (103 endpoints)',
  'GraphQL API with Subscriptions',
  'WebSocket Real-time Communication',
  'Multi-Agent Workflows',
  'Document Management & RAG',
  'Asynchronous Task Orchestration',
  'Multi-Modal Processing (Audio, Video, Image)',
  'Developer Tools & SDKs',
  'Interactive Documentation',
  'Production-Ready External Services'
];
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

### OAuth2 Authentication (v9.0.0) - PRODUCTION READY
GremlinsAI now uses **Google OAuth2** for secure authentication:

- **Authentication**: **REQUIRED** for all API endpoints
- **OAuth2 Provider**: Google OAuth2 with JWT tokens
- **Token Format**: `Authorization: Bearer <jwt_token>`
- **Token Expiration**: 24 hours (configurable)
- **User Management**: Automatic user creation and management

### OAuth2 Configuration
First, get your OAuth2 configuration from the API:

```javascript
async function getOAuth2Config() {
  const response = await fetch(`${API_BASE_URL}/auth/config`);
  const config = await response.json();
  return config;
  // Returns: { google_client_id, redirect_uri, scopes }
}
```

### Google OAuth2 Login Flow
Here's the complete OAuth2 authentication flow:

#### 1. Frontend OAuth2 Implementation

```javascript
class OAuth2Manager {
  constructor(config) {
    this.clientId = config.google_client_id;
    this.redirectUri = config.redirect_uri;
    this.scopes = config.scopes.join(' ');
    this.accessToken = localStorage.getItem('gremlins_access_token');
  }

  // Generate OAuth2 login URL
  getLoginUrl() {
    const params = new URLSearchParams({
      client_id: this.clientId,
      redirect_uri: this.redirectUri,
      response_type: 'code',
      scope: this.scopes,
      access_type: 'offline',
      prompt: 'consent'
    });

    return `https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`;
  }

  // Handle OAuth2 callback
  async handleCallback(code) {
    try {
      // Exchange authorization code for Google token
      const tokenResponse = await fetch('https://oauth2.googleapis.com/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({
          client_id: this.clientId,
          client_secret: 'YOUR_CLIENT_SECRET', // Should be handled server-side
          code: code,
          grant_type: 'authorization_code',
          redirect_uri: this.redirectUri
        })
      });

      const tokenData = await tokenResponse.json();

      // Exchange Google token for GremlinsAI token
      const gremlinsResponse = await fetch(`${API_BASE_URL}/auth/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          google_token: tokenData.id_token
        })
      });

      const gremlinsData = await gremlinsResponse.json();

      // Store the GremlinsAI access token
      this.accessToken = gremlinsData.access_token;
      localStorage.setItem('gremlins_access_token', this.accessToken);

      return gremlinsData.user;
    } catch (error) {
      console.error('OAuth2 callback failed:', error);
      throw error;
    }
  }

  // Check if user is authenticated
  isAuthenticated() {
    return !!this.accessToken;
  }

  // Logout
  logout() {
    this.accessToken = null;
    localStorage.removeItem('gremlins_access_token');
  }
}
```

#### 2. Authenticated API Client

```typescript
class GremlinsAPIClient {
  private baseURL: string;
  private accessToken: string | null;
  private requestTimeout: number;

  constructor(baseURL: string, options?: { timeout?: number }) {
    if (!baseURL) {
      throw new Error('API base URL is required');
    }

    this.baseURL = baseURL;
    this.accessToken = localStorage.getItem('gremlins_access_token');
    this.requestTimeout = options?.timeout || 30000;
  }

  setAccessToken(token: string) {
    this.accessToken = token;
    localStorage.setItem('gremlins_access_token', token);
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
          'X-Client-Version': '8.0.0',
          'X-API-Version': '8.0.0',
          'User-Agent': 'GremlinsAI-Frontend-Client/8.0.0',
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
      const errorData = error.response.data;
      const status = error.response.status;

      // Check for new comprehensive error format first
      if (errorData.error_message || errorData.detail) {
        return errorData.error_message || errorData.detail || 'An unexpected error occurred.';
      }

      // Fallback to status-based error handling
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
          return 'An unexpected error occurred.';
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

### Enhanced Real-time API

#### Subscribe to Real-time Events
```javascript
async function subscribeToEvents(eventTypes, options = {}) {
  try {
    const response = await apiClient.post('/realtime/subscribe', {
      event_types: eventTypes,
      callback_url: options.callbackUrl,
      filter_criteria: options.filterCriteria || {},
      subscription_id: options.subscriptionId || generateRequestId(),
      delivery_mode: options.deliveryMode || 'webhook', // 'webhook' or 'websocket'
      retry_policy: options.retryPolicy || {
        max_retries: 3,
        retry_delay: 1000,
        exponential_backoff: true
      }
    });
    return response.data;
  } catch (error) {
    throw new Error(`Subscription failed: ${error.message}`);
  }
}

// Example: Subscribe to conversation events
const subscription = await subscribeToEvents(['conversation_updated', 'message_created'], {
  filterCriteria: { user_id: 'current-user' },
  deliveryMode: 'websocket'
});
```

#### Get Real-time System Status
```javascript
async function getRealtimeStatus() {
  try {
    const response = await apiClient.get('/realtime/status');
    return response.data;
  } catch (error) {
    throw new Error(`Failed to get real-time status: ${error.message}`);
  }
}

// Enhanced system status with metrics
async function getSystemMetrics() {
  try {
    const response = await apiClient.get('/realtime/system/status');
    return response.data;
  } catch (error) {
    throw new Error(`Failed to get system metrics: ${error.message}`);
  }
}

// Example usage
const status = await getRealtimeStatus();
console.log('WebSocket connections:', status.active_connections);
console.log('Event queue status:', status.event_queue);

const metrics = await getSystemMetrics();
console.log('System health:', metrics.health_score);
console.log('Response times:', metrics.avg_response_time);
```

#### Real-time Information and Capabilities
```javascript
async function getRealtimeInfo() {
  try {
    const response = await apiClient.get('/realtime/info');
    return response.data;
  } catch (error) {
    throw new Error(`Failed to get real-time info: ${error.message}`);
  }
}

// Get available event types
async function getAvailableEventTypes() {
  try {
    const response = await apiClient.get('/realtime/events/types');
    return response.data;
  } catch (error) {
    throw new Error(`Failed to get event types: ${error.message}`);
  }
}

// Example usage
const realtimeInfo = await getRealtimeInfo();
console.log('Supported protocols:', realtimeInfo.supported_protocols);
console.log('Max connections:', realtimeInfo.max_connections);

const eventTypes = await getAvailableEventTypes();
console.log('Available events:', eventTypes.event_types);
```

#### Manage Subscriptions
```javascript
async function listSubscriptions() {
  try {
    const response = await apiClient.get('/realtime/subscriptions');
    return response.data;
  } catch (error) {
    throw new Error(`Failed to list subscriptions: ${error.message}`);
  }
}

async function updateSubscription(subscriptionId, updates) {
  try {
    const response = await apiClient.patch(`/realtime/subscriptions/${subscriptionId}`, updates);
    return response.data;
  } catch (error) {
    throw new Error(`Failed to update subscription: ${error.message}`);
  }
}

async function cancelSubscription(subscriptionId) {
  try {
    const response = await apiClient.delete(`/realtime/subscriptions/${subscriptionId}`);
    return response.data;
  } catch (error) {
    throw new Error(`Failed to cancel subscription: ${error.message}`);
  }
}

// Example: Manage subscriptions
const subscriptions = await listSubscriptions();
console.log('Active subscriptions:', subscriptions.subscriptions);

// Update subscription to add more event types
await updateSubscription('sub-123', {
  event_types: ['conversation_updated', 'message_created', 'agent_response']
});

// Cancel subscription when no longer needed
await cancelSubscription('sub-123');
```

### Multi-Modal Processing

#### Process Audio with Advanced Features
```javascript
async function processAudio(audioFile, options = {}) {
  try {
    const formData = new FormData();
    formData.append('audio', audioFile);
    formData.append('options', JSON.stringify({
      transcribe: options.transcribe !== false,
      language: options.language || 'auto',
      format: options.format || 'wav',
      include_timestamps: options.includeTimestamps || false,
      speaker_detection: options.speakerDetection || false,
      sentiment_analysis: options.sentimentAnalysis || false,
      keyword_extraction: options.keywordExtraction || false
    }));

    const response = await fetch(`${API_BASE_URL}/multimodal/audio`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
        'X-Request-ID': generateRequestId(),
        'X-API-Version': '8.0.0',
      },
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error_message || errorData.detail || `Audio processing failed: ${response.statusText}`);
    }

    return response.json();
  } catch (error) {
    throw new Error(`Audio processing failed: ${error.message}`);
  }
}

// Example usage with advanced features
const audioResult = await processAudio(audioFile, {
  transcribe: true,
  language: 'en',
  includeTimestamps: true,
  speakerDetection: true,
  sentimentAnalysis: true
});
console.log('Transcription:', audioResult.transcription);
console.log('Speakers:', audioResult.speakers);
console.log('Sentiment:', audioResult.sentiment);
```

#### Process Image with Computer Vision
```javascript
async function processImage(imageFile, options = {}) {
  try {
    const formData = new FormData();
    formData.append('image', imageFile);
    formData.append('options', JSON.stringify({
      analyze: options.analyze !== false,
      extract_text: options.extractText || false,
      detect_objects: options.detectObjects || false,
      face_detection: options.faceDetection || false,
      scene_analysis: options.sceneAnalysis || false,
      color_analysis: options.colorAnalysis || false,
      quality_assessment: options.qualityAssessment || false
    }));

    const response = await fetch(`${API_BASE_URL}/multimodal/image`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
        'X-Request-ID': generateRequestId(),
        'X-API-Version': '8.0.0',
      },
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error_message || errorData.detail || `Image processing failed: ${response.statusText}`);
    }

    return response.json();
  } catch (error) {
    throw new Error(`Image processing failed: ${error.message}`);
  }
}

// Example usage with computer vision
const imageResult = await processImage(imageFile, {
  analyze: true,
  extractText: true,
  detectObjects: true,
  faceDetection: true,
  sceneAnalysis: true
});
console.log('Objects detected:', imageResult.objects);
console.log('Text extracted:', imageResult.text);
console.log('Scene description:', imageResult.scene);
```

#### Process Video with Analysis
```javascript
async function processVideo(videoFile, options = {}) {
  try {
    const formData = new FormData();
    formData.append('video', videoFile);
    formData.append('options', JSON.stringify({
      extract_frames: options.extractFrames || false,
      frame_interval: options.frameInterval || 1,
      analyze_content: options.analyzeContent || false,
      detect_scenes: options.detectScenes || false,
      extract_audio: options.extractAudio || false,
      generate_summary: options.generateSummary || false
    }));

    const response = await fetch(`${API_BASE_URL}/multimodal/video`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
        'X-Request-ID': generateRequestId(),
        'X-API-Version': '8.0.0',
      },
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error_message || errorData.detail || `Video processing failed: ${response.statusText}`);
    }

    return response.json();
  } catch (error) {
    throw new Error(`Video processing failed: ${error.message}`);
  }
}

// Example usage
const videoResult = await processVideo(videoFile, {
  extractFrames: true,
  frameInterval: 5,
  analyzeContent: true,
  detectScenes: true,
  generateSummary: true
});
console.log('Scenes detected:', videoResult.scenes);
console.log('Content summary:', videoResult.summary);
```

#### Multi-Modal Content Fusion
```javascript
async function processMultiModalContent(files, options = {}) {
  try {
    const formData = new FormData();

    files.forEach((file, index) => {
      formData.append(`file_${index}`, file);
    });

    formData.append('options', JSON.stringify({
      fusion_type: options.fusionType || 'comprehensive',
      cross_modal_analysis: options.crossModalAnalysis || true,
      generate_insights: options.generateInsights || true,
      correlation_analysis: options.correlationAnalysis || false
    }));

    const response = await fetch(`${API_BASE_URL}/multimodal/fusion`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
        'X-Request-ID': generateRequestId(),
        'X-API-Version': '8.0.0',
      },
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error_message || errorData.detail || `Multi-modal fusion failed: ${response.statusText}`);
    }

    return response.json();
  } catch (error) {
    throw new Error(`Multi-modal fusion failed: ${error.message}`);
  }
}

// Example: Process image + audio together
const fusionResult = await processMultiModalContent([imageFile, audioFile], {
  fusionType: 'comprehensive',
  crossModalAnalysis: true,
  generateInsights: true
});
console.log('Fusion insights:', fusionResult.insights);
console.log('Cross-modal correlations:', fusionResult.correlations);
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

### Developer Portal & Documentation

#### Interactive Documentation Access
```javascript
// Access interactive documentation portal
async function getInteractiveDocumentation() {
  try {
    const response = await fetch(`${API_BASE_URL.replace('/api/v1', '')}/docs`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
        'X-API-Version': '8.0.0',
      }
    });

    if (!response.ok) {
      throw new Error(`Failed to access documentation: ${response.statusText}`);
    }

    return response.text(); // Returns HTML content
  } catch (error) {
    throw new Error(`Failed to get interactive documentation: ${error.message}`);
  }
}

// Get API reference documentation
async function getAPIReference() {
  try {
    const response = await fetch(`${API_BASE_URL.replace('/api/v1', '')}/docs/api-reference`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
        'X-API-Version': '8.0.0',
      }
    });

    if (!response.ok) {
      throw new Error(`Failed to access API reference: ${response.statusText}`);
    }

    return response.text(); // Returns HTML content
  } catch (error) {
    throw new Error(`Failed to get API reference: ${error.message}`);
  }
}

// Get OpenAPI specification
async function getOpenAPISpec() {
  try {
    const response = await fetch(`${API_BASE_URL.replace('/api/v1', '')}/docs/api-spec`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
        'X-API-Version': '8.0.0',
      }
    });

    if (!response.ok) {
      throw new Error(`Failed to get OpenAPI spec: ${response.statusText}`);
    }

    return response.json();
  } catch (error) {
    throw new Error(`Failed to get OpenAPI specification: ${error.message}`);
  }
}
```

#### Developer Portal Dashboard
```javascript
// Access developer portal dashboard
async function getDeveloperPortalDashboard() {
  try {
    const response = await fetch(`${API_BASE_URL.replace('/api/v1', '')}/developer-portal`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
        'X-API-Version': '8.0.0',
      }
    });

    if (!response.ok) {
      throw new Error(`Failed to access developer portal: ${response.statusText}`);
    }

    return response.text(); // Returns HTML content
  } catch (error) {
    throw new Error(`Failed to get developer portal: ${error.message}`);
  }
}

// Get system metrics for developers
async function getDeveloperMetrics() {
  try {
    const response = await fetch(`${API_BASE_URL.replace('/api/v1', '')}/developer-portal/metrics`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
        'X-API-Version': '8.0.0',
      }
    });

    if (!response.ok) {
      throw new Error(`Failed to get metrics: ${response.statusText}`);
    }

    return response.json();
  } catch (error) {
    throw new Error(`Failed to get developer metrics: ${error.message}`);
  }
}

// Test API endpoints interactively
async function testAPIEndpoint(endpoint, method = 'GET', data = null) {
  try {
    const response = await fetch(`${API_BASE_URL.replace('/api/v1', '')}/developer-portal/test-endpoint`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
        'Content-Type': 'application/json',
        'X-API-Version': '8.0.0',
      },
      body: JSON.stringify({
        endpoint,
        method,
        data
      })
    });

    if (!response.ok) {
      throw new Error(`Failed to test endpoint: ${response.statusText}`);
    }

    return response.json();
  } catch (error) {
    throw new Error(`Failed to test API endpoint: ${error.message}`);
  }
}

// Example usage
const metrics = await getDeveloperMetrics();
console.log('System health:', metrics.system_health);
console.log('API response times:', metrics.response_times);
```

## WebSocket Connections (Enhanced v8.0.0)

### Advanced Real-time Connection
```javascript
class GremlinsWebSocket {
  constructor(url, apiKey, options = {}) {
    this.url = url;
    this.apiKey = apiKey;
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = options.maxReconnectAttempts || 5;
    this.reconnectDelay = options.reconnectDelay || 1000;
    this.heartbeatInterval = options.heartbeatInterval || 30000;
    this.heartbeatTimer = null;
    this.subscriptions = new Set();
    this.messageQueue = [];
    this.connectionStatus = 'disconnected';
  }

  connect() {
    try {
      this.connectionStatus = 'connecting';
      // Updated WebSocket endpoint for v8.0.0
      this.ws = new WebSocket(`${this.url}/ws?token=${this.apiKey}&version=8.0.0`);

      this.ws.onopen = () => {
        console.log('WebSocket connected to GremlinsAI v9.0.0');
        this.connectionStatus = 'connected';
        this.reconnectAttempts = 0;
        this.startHeartbeat();
        this.processMessageQueue();
        this.resubscribeToEvents();
      };

      this.ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        this.handleMessage(data);
      };

      this.ws.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason);
        this.connectionStatus = 'disconnected';
        this.stopHeartbeat();
        this.handleReconnect();
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.connectionStatus = 'error';
      };
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
      this.connectionStatus = 'error';
    }
  }

  sendMessage(message) {
    const messageWithTimestamp = {
      ...message,
      timestamp: new Date().toISOString(),
      request_id: this.generateRequestId()
    };

    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(messageWithTimestamp));
    } else {
      // Queue message for when connection is restored
      this.messageQueue.push(messageWithTimestamp);
      if (this.connectionStatus === 'disconnected') {
        this.connect();
      }
    }
  }

  // Enhanced message handling with event types
  handleMessage(data) {
    switch (data.type) {
      case 'agent_response':
        this.onAgentResponse(data);
        break;
      case 'conversation_updated':
        this.onConversationUpdated(data);
        break;
      case 'message_created':
        this.onMessageCreated(data);
        break;
      case 'task_status_update':
        this.onTaskStatusUpdate(data);
        break;
      case 'system_notification':
        this.onSystemNotification(data);
        break;
      case 'error':
        this.onError(data);
        break;
      case 'pong':
        // Heartbeat response
        break;
      default:
        console.log('Received unknown message type:', data);
    }
  }

  // Subscription management
  subscribeToEvent(eventType, conversationId = null) {
    const subscription = {
      type: 'subscribe',
      subscription_type: eventType,
      conversation_id: conversationId,
      timestamp: new Date().toISOString()
    };

    this.subscriptions.add(JSON.stringify(subscription));
    this.sendMessage(subscription);
  }

  unsubscribeFromEvent(eventType, conversationId = null) {
    const subscription = {
      type: 'unsubscribe',
      subscription_type: eventType,
      conversation_id: conversationId,
      timestamp: new Date().toISOString()
    };

    this.subscriptions.delete(JSON.stringify({
      type: 'subscribe',
      subscription_type: eventType,
      conversation_id: conversationId
    }));
    this.sendMessage(subscription);
  }

  // Heartbeat mechanism
  startHeartbeat() {
    this.heartbeatTimer = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.sendMessage({ type: 'ping' });
      }
    }, this.heartbeatInterval);
  }

  stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  // Process queued messages
  processMessageQueue() {
    while (this.messageQueue.length > 0) {
      const message = this.messageQueue.shift();
      this.sendMessage(message);
    }
  }

  // Resubscribe to events after reconnection
  resubscribeToEvents() {
    this.subscriptions.forEach(subscriptionStr => {
      const subscription = JSON.parse(subscriptionStr);
      this.sendMessage(subscription);
    });
  }

  handleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      setTimeout(() => {
        this.reconnectAttempts++;
        console.log(`Reconnecting... Attempt ${this.reconnectAttempts}`);
        this.connect();
      }, this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1));
    } else {
      console.error('Max reconnection attempts reached');
      this.connectionStatus = 'error';
    }
  }

  generateRequestId() {
    return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  // Event handlers (override these in your implementation)
  onAgentResponse(data) { console.log('Agent response:', data); }
  onConversationUpdated(data) { console.log('Conversation updated:', data); }
  onMessageCreated(data) { console.log('Message created:', data); }
  onTaskStatusUpdate(data) { console.log('Task status update:', data); }
  onSystemNotification(data) { console.log('System notification:', data); }
  onError(data) { console.error('WebSocket error:', data); }

  disconnect() {
    this.stopHeartbeat();
    if (this.ws) {
      this.ws.close();
    }
    this.connectionStatus = 'disconnected';
  }
}
```

### Enhanced Usage Example (v8.0.0)
```javascript
const wsClient = new GremlinsWebSocket(
  process.env.REACT_APP_WS_BASE_URL,
  process.env.REACT_APP_API_KEY,
  {
    maxReconnectAttempts: 10,
    reconnectDelay: 1000,
    heartbeatInterval: 30000
  }
);

// Override event handlers for your application
wsClient.onAgentResponse = (data) => {
  updateChatUI(data.message, data.conversation_id);
  if (data.execution_time) {
    updatePerformanceMetrics(data.execution_time);
  }
};

wsClient.onConversationUpdated = (data) => {
  refreshConversationList();
  updateConversationTitle(data.conversation_id, data.title);
};

wsClient.onMessageCreated = (data) => {
  addMessageToUI(data.message);
  scrollToBottom();
};

wsClient.onTaskStatusUpdate = (data) => {
  updateTaskProgress(data.task_id, data.status, data.progress);
};

wsClient.onSystemNotification = (data) => {
  showSystemNotification(data.message, data.severity);
};

wsClient.onError = (data) => {
  showError(data.error_message || data.detail);
  if (data.error_code === 'GREMLINS_7001') {
    // WebSocket connection error - will auto-reconnect
    showReconnectingIndicator();
  }
};

wsClient.connect();

// Subscribe to specific events
wsClient.subscribeToEvent('conversation', currentConversationId);
wsClient.subscribeToEvent('task_updates');
wsClient.subscribeToEvent('system_notifications');

// Send a message with input sanitization
function sendSanitizedMessage(input, conversationId) {
  const sanitizedInput = sanitizeInput(input);
  wsClient.sendMessage({
    type: 'chat',
    input: sanitizedInput,
    conversation_id: conversationId,
    metadata: {
      client_version: '8.0.0',
      user_agent: navigator.userAgent
    }
  });
}

// Input sanitization function
function sanitizeInput(input) {
  if (typeof input !== 'string') {
    throw new Error('Input must be a string');
  }

  // Remove potentially dangerous characters
  return input
    .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '') // Remove script tags
    .replace(/javascript:/gi, '') // Remove javascript: protocol
    .replace(/on\w+\s*=/gi, '') // Remove event handlers
    .trim()
    .substring(0, 10000); // Limit length
}

// Example usage
sendSanitizedMessage('Hello, how can you help me?', currentConversationId);
```

### Security Best Practices
```javascript
// Input validation and sanitization
class InputValidator {
  static sanitizeText(text) {
    if (!text || typeof text !== 'string') {
      return '';
    }

    return text
      .replace(/[<>]/g, '') // Remove angle brackets
      .replace(/javascript:/gi, '') // Remove javascript protocol
      .replace(/on\w+=/gi, '') // Remove event handlers
      .trim()
      .substring(0, 5000); // Reasonable length limit
  }

  static validateFileUpload(file) {
    const allowedTypes = [
      'image/jpeg', 'image/png', 'image/gif', 'image/webp',
      'audio/wav', 'audio/mp3', 'audio/mpeg', 'audio/ogg',
      'video/mp4', 'video/webm', 'video/ogg',
      'application/pdf', 'text/plain'
    ];

    const maxSize = 50 * 1024 * 1024; // 50MB

    if (!allowedTypes.includes(file.type)) {
      throw new Error('File type not allowed');
    }

    if (file.size > maxSize) {
      throw new Error('File size too large');
    }

    return true;
  }

  static sanitizeFilename(filename) {
    return filename
      .replace(/[^a-zA-Z0-9.-]/g, '_') // Replace special chars with underscore
      .replace(/\.{2,}/g, '.') // Remove multiple dots
      .substring(0, 255); // Limit filename length
  }
}

// Usage in your application
function handleUserInput(input) {
  try {
    const sanitizedInput = InputValidator.sanitizeText(input);
    if (!sanitizedInput) {
      throw new Error('Invalid input provided');
    }

    sendSanitizedMessage(sanitizedInput, currentConversationId);
  } catch (error) {
    showError(`Input validation failed: ${error.message}`);
  }
}

function handleFileUpload(file) {
  try {
    InputValidator.validateFileUpload(file);
    const sanitizedFilename = InputValidator.sanitizeFilename(file.name);

    // Proceed with file upload
    uploadFile(file, sanitizedFilename);
  } catch (error) {
    showError(`File validation failed: ${error.message}`);
  }
}
```

## Error Handling

### Comprehensive Error Response Format (v8.0.0)
```typescript
interface ErrorResponse {
  success: boolean;
  error_code: string;
  error_message: string;
  error_details: string;
  detail: string; // Added for backward compatibility
  request_id: string;
  timestamp: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  category: string;
  suggested_action: string;
  documentation_url: string;
  affected_services: ServiceStatus[];
  fallback_available: boolean;
  validation_errors?: ValidationError[];
}

interface ServiceStatus {
  service_name: string;
  status: 'available' | 'degraded' | 'unavailable';
  fallback_available: boolean;
  capabilities_affected: string[];
}

interface ValidationError {
  field: string;
  message: string;
  invalid_value: any;
  expected_type: string;
}
```

### Enhanced Error Handling Utility (v8.0.0)
```javascript
class ErrorHandler {
  static handle(error) {
    if (error.response?.data) {
      const errorData = error.response.data;

      // Use the new comprehensive error format
      const message = errorData.error_message || errorData.detail || 'An unexpected error occurred.';

      // Enhanced error code handling
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
        case 'GREMLINS_5001':
          return 'Rate limit exceeded. Please wait before retrying.';
        case 'GREMLINS_6001':
          return 'Multi-modal processing failed. Check file format and try again.';
        case 'GREMLINS_7001':
          return 'WebSocket connection error. Attempting to reconnect...';
        case 'GREMLINS_8001':
          return 'Service temporarily unavailable. Fallback mode activated.';
        default:
          return message;
      }
    }

    return error.message || 'Network error occurred.';
  }

  static isRetryable(error) {
    const retryableCodes = [
      'GREMLINS_4001', // External service unavailable
      'GREMLINS_5001', // Rate limit exceeded
      'GREMLINS_7001', // WebSocket connection error
      'GREMLINS_8001'  // Service temporarily unavailable
    ];
    return error.response?.data?.error_code &&
           retryableCodes.includes(error.response.data.error_code);
  }

  static getSeverity(error) {
    return error.response?.data?.severity || 'medium';
  }

  static getAffectedServices(error) {
    return error.response?.data?.affected_services || [];
  }

  static hasFallback(error) {
    return error.response?.data?.fallback_available || false;
  }

  static getSuggestedAction(error) {
    return error.response?.data?.suggested_action || 'Please try again or contact support.';
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

// Enhanced WebSocket Types (v8.0.0)
interface WebSocketMessage {
  type: 'chat' | 'agent_response' | 'conversation_updated' | 'message_created' |
        'task_status_update' | 'system_notification' | 'error' | 'status' |
        'ping' | 'pong' | 'subscribe' | 'unsubscribe';
  data?: any;
  timestamp: string;
  request_id?: string;
  conversation_id?: string;
  subscription_type?: string;
  error_code?: string;
  error_message?: string;
  detail?: string; // For backward compatibility
}

interface WebSocketConfig {
  url: string;
  apiKey: string;
  maxReconnectAttempts?: number;
  reconnectDelay?: number;
  heartbeatInterval?: number;
  autoReconnect?: boolean;
  queueMessages?: boolean;
}

interface WebSocketSubscription {
  type: 'subscribe' | 'unsubscribe';
  subscription_type: 'conversation' | 'task_updates' | 'system_notifications' | 'agent_responses';
  conversation_id?: string;
  filter_criteria?: Record<string, any>;
  timestamp: string;
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

// Multi-Modal Types
interface AudioProcessingOptions {
  transcribe?: boolean;
  language?: string;
  format?: string;
  include_timestamps?: boolean;
  speaker_detection?: boolean;
  sentiment_analysis?: boolean;
  keyword_extraction?: boolean;
  noise_reduction?: boolean;
}

interface AudioProcessingResult {
  transcription?: string;
  language_detected?: string;
  speakers?: Array<{
    speaker_id: string;
    segments: Array<{
      start_time: number;
      end_time: number;
      text: string;
    }>;
  }>;
  sentiment?: {
    overall_sentiment: 'positive' | 'negative' | 'neutral';
    confidence: number;
    emotions?: string[];
  };
  keywords?: Array<{
    keyword: string;
    relevance: number;
    frequency: number;
  }>;
  audio_quality?: {
    signal_to_noise_ratio: number;
    clarity_score: number;
  };
  processing_time: number;
}

interface ImageProcessingOptions {
  analyze?: boolean;
  extract_text?: boolean;
  detect_objects?: boolean;
  face_detection?: boolean;
  scene_analysis?: boolean;
  color_analysis?: boolean;
  quality_assessment?: boolean;
}

interface ImageProcessingResult {
  analysis?: {
    description: string;
    confidence: number;
    categories: string[];
  };
  text_extracted?: string;
  objects?: Array<{
    label: string;
    confidence: number;
    bounding_box: {
      x: number;
      y: number;
      width: number;
      height: number;
    };
  }>;
  faces?: Array<{
    confidence: number;
    age_estimate?: number;
    gender_estimate?: string;
    emotions?: Record<string, number>;
    bounding_box: {
      x: number;
      y: number;
      width: number;
      height: number;
    };
  }>;
  scene?: {
    primary_scene: string;
    confidence: number;
    scene_attributes: string[];
  };
  colors?: {
    dominant_colors: string[];
    color_palette: Array<{
      color: string;
      percentage: number;
    }>;
  };
  quality?: {
    resolution: string;
    sharpness_score: number;
    brightness_score: number;
    contrast_score: number;
  };
  processing_time: number;
}

interface VideoProcessingOptions {
  extract_frames?: boolean;
  frame_interval?: number;
  analyze_content?: boolean;
  detect_scenes?: boolean;
  extract_audio?: boolean;
  generate_summary?: boolean;
  object_tracking?: boolean;
}

interface VideoProcessingResult {
  frames?: Array<{
    timestamp: number;
    frame_url: string;
    analysis?: ImageProcessingResult;
  }>;
  scenes?: Array<{
    start_time: number;
    end_time: number;
    description: string;
    confidence: number;
  }>;
  audio_analysis?: AudioProcessingResult;
  content_summary?: string;
  objects_tracked?: Array<{
    object_id: string;
    label: string;
    tracking_data: Array<{
      timestamp: number;
      bounding_box: {
        x: number;
        y: number;
        width: number;
        height: number;
      };
    }>;
  }>;
  metadata: {
    duration: number;
    resolution: string;
    frame_rate: number;
    file_size: number;
  };
  processing_time: number;
}

interface MultiModalFusionOptions {
  fusion_type?: 'comprehensive' | 'summary' | 'correlation';
  cross_modal_analysis?: boolean;
  generate_insights?: boolean;
  correlation_analysis?: boolean;
  output_format?: 'json' | 'text' | 'structured';
}

interface MultiModalFusionResult {
  insights?: string;
  correlations?: Array<{
    modality_1: string;
    modality_2: string;
    correlation_type: string;
    confidence: number;
    description: string;
  }>;
  unified_summary?: string;
  content_themes?: string[];
  recommendations?: string[];
  processing_metadata: {
    files_processed: number;
    modalities_detected: string[];
    processing_time: number;
  };
}

// Developer Portal Types
interface DeveloperMetrics {
  system_health: {
    overall_score: number;
    uptime_percentage: number;
    error_rate: number;
  };
  performance: {
    avg_response_time: number;
    p95_response_time: number;
    requests_per_second: number;
  };
  usage: {
    total_requests: number;
    unique_users: number;
    popular_endpoints: Array<{
      endpoint: string;
      request_count: number;
    }>;
  };
}

interface APIUsageStats {
  top_endpoints: Array<{
    endpoint: string;
    method: string;
    request_count: number;
    avg_response_time: number;
    error_rate: number;
  }>;
  request_volume: {
    hourly: number[];
    daily: number[];
    weekly: number[];
  };
  user_activity: {
    active_users: number;
    new_users: number;
    returning_users: number;
  };
}
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
