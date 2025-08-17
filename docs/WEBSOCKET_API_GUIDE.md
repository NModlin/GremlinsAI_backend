# GremlinsAI WebSocket API Guide v10.0.0

## Table of Contents

1. [Overview](#overview)
2. [Connection Management](#connection-management)
3. [Real-time Chat](#real-time-chat)
4. [Collaboration Features](#collaboration-features)
5. [System Events](#system-events)
6. [Error Handling](#error-handling)
7. [Frontend Integration Examples](#frontend-integration-examples)
8. [Performance Optimization](#performance-optimization)

## Overview

GremlinsAI provides comprehensive WebSocket APIs for real-time communication, enabling:
- **Real-time chat** with AI agents
- **Collaborative editing** with operational transform
- **Live system events** and notifications
- **Multi-user sessions** with sub-200ms latency

**WebSocket Endpoints:**
- General WebSocket: `ws://localhost:8000/api/v1/ws/ws`
- Collaboration: `ws://localhost:8000/api/v1/collaborate/{session_id}`

## Connection Management

### Basic Connection
```javascript
// Connect to general WebSocket
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/ws');

// Connection event handlers
ws.onopen = (event) => {
  console.log('WebSocket connected');
  // Send authentication if required
  ws.send(JSON.stringify({
    type: 'authenticate',
    token: 'your-api-key'
  }));
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  handleMessage(message);
};

ws.onclose = (event) => {
  console.log('WebSocket disconnected:', event.code, event.reason);
  // Implement reconnection logic
  setTimeout(reconnect, 1000);
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};
```

### Connection with Authentication
```javascript
// Connect with API key in query parameters
const apiKey = localStorage.getItem('gremlins_api_key');
const wsUrl = `ws://localhost:8000/api/v1/ws/ws?token=${apiKey}`;
const ws = new WebSocket(wsUrl);

// Or authenticate after connection
ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'authenticate',
    token: apiKey
  }));
};
```

### Automatic Reconnection
```javascript
class WebSocketManager {
  constructor(url, options = {}) {
    this.url = url;
    this.options = options;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectInterval = 1000;
    this.ws = null;
    this.messageQueue = [];
    
    this.connect();
  }
  
  connect() {
    this.ws = new WebSocket(this.url);
    
    this.ws.onopen = (event) => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
      
      // Send queued messages
      while (this.messageQueue.length > 0) {
        const message = this.messageQueue.shift();
        this.send(message);
      }
      
      if (this.options.onOpen) {
        this.options.onOpen(event);
      }
    };
    
    this.ws.onmessage = (event) => {
      if (this.options.onMessage) {
        this.options.onMessage(JSON.parse(event.data));
      }
    };
    
    this.ws.onclose = (event) => {
      console.log('WebSocket disconnected');
      this.handleReconnect();
      
      if (this.options.onClose) {
        this.options.onClose(event);
      }
    };
    
    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      if (this.options.onError) {
        this.options.onError(error);
      }
    };
  }
  
  handleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = this.reconnectInterval * Math.pow(2, this.reconnectAttempts - 1);
      
      console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
      setTimeout(() => this.connect(), delay);
    } else {
      console.error('Max reconnection attempts reached');
    }
  }
  
  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    } else {
      // Queue message for when connection is restored
      this.messageQueue.push(data);
    }
  }
  
  close() {
    if (this.ws) {
      this.ws.close();
    }
  }
}
```

## Real-time Chat

### Subscribe to Conversation Updates
```javascript
// Subscribe to a specific conversation
ws.send(JSON.stringify({
  type: 'subscribe',
  subscription_type: 'conversation',
  conversation_id: 'uuid-here'
}));

// Handle incoming messages
function handleMessage(message) {
  switch (message.type) {
    case 'message':
      displayMessage(message.data);
      break;
    case 'typing_indicator':
      showTypingIndicator(message.data);
      break;
    case 'agent_thinking':
      showAgentThinking(message.data);
      break;
  }
}
```

### Send Chat Messages
```javascript
// Send a message to the AI agent
function sendMessage(content, conversationId) {
  ws.send(JSON.stringify({
    type: 'send_message',
    conversation_id: conversationId,
    content: content,
    timestamp: new Date().toISOString()
  }));
}

// Send typing indicator
function sendTypingIndicator(conversationId, isTyping) {
  ws.send(JSON.stringify({
    type: 'typing_indicator',
    conversation_id: conversationId,
    is_typing: isTyping,
    timestamp: new Date().toISOString()
  }));
}
```

### Message Types

#### Incoming Message
```javascript
{
  "type": "message",
  "conversation_id": "uuid",
  "message": {
    "id": "uuid",
    "role": "assistant",
    "content": "Hello! How can I help you today?",
    "timestamp": "2024-01-15T10:00:00Z",
    "metadata": {
      "execution_time": 1.23,
      "tokens_used": 150,
      "tools_used": ["web_search"]
    }
  }
}
```

#### Agent Thinking Indicator
```javascript
{
  "type": "agent_thinking",
  "conversation_id": "uuid",
  "data": {
    "agent_type": "researcher",
    "status": "analyzing_query",
    "estimated_time": 3.5,
    "progress": 0.3
  }
}
```

#### Multi-Agent Workflow Update
```javascript
{
  "type": "workflow_update",
  "workflow_id": "uuid",
  "data": {
    "current_agent": "analyst",
    "stage": "data_analysis",
    "progress": 0.6,
    "agents_completed": ["researcher"],
    "agents_remaining": ["writer"]
  }
}
```

## Collaboration Features

### Join Collaboration Session
```javascript
// Connect to collaboration session
const sessionId = 'collaboration-session-uuid';
const participantId = 'user-123';
const displayName = 'Alice';

const collaborationWs = new WebSocket(
  `ws://localhost:8000/api/v1/collaborate/${sessionId}?participant_id=${participantId}&display_name=${displayName}`
);

// Join session
collaborationWs.onopen = () => {
  collaborationWs.send(JSON.stringify({
    type: 'join_session',
    participant_type: 'human_user'
  }));
};
```

### Document Operations
```javascript
// Send document edit operation
function sendDocumentOperation(operation) {
  collaborationWs.send(JSON.stringify({
    type: 'document_update',
    operation: operation,
    timestamp: new Date().toISOString()
  }));
}

// Insert text
sendDocumentOperation({
  type: 'insert',
  position: 10,
  content: 'Hello world'
});

// Delete text
sendDocumentOperation({
  type: 'delete',
  position: 5,
  length: 9
});

// Replace text
sendDocumentOperation({
  type: 'replace',
  position: 0,
  length: 5,
  content: 'New text'
});
```

### Cursor and Selection Updates
```javascript
// Send cursor position update
function updateCursor(position) {
  collaborationWs.send(JSON.stringify({
    type: 'cursor_update',
    position: position,
    timestamp: new Date().toISOString()
  }));
}

// Send selection update
function updateSelection(start, end) {
  collaborationWs.send(JSON.stringify({
    type: 'selection_update',
    selection: {
      start: start,
      end: end
    },
    timestamp: new Date().toISOString()
  }));
}
```

### AI Agent Collaboration
```javascript
// Request AI agent assistance
function requestAgentHelp(query) {
  collaborationWs.send(JSON.stringify({
    type: 'agent_request',
    query: query,
    context: {
      document_content: getCurrentDocumentContent(),
      cursor_position: getCursorPosition()
    },
    timestamp: new Date().toISOString()
  }));
}

// Handle AI agent responses
function handleCollaborationMessage(message) {
  switch (message.type) {
    case 'user_joined':
      addParticipant(message.participant);
      break;
    case 'user_left':
      removeParticipant(message.participant_id);
      break;
    case 'document_update':
      applyDocumentOperation(message.operation);
      break;
    case 'cursor_update':
      updateParticipantCursor(message.participant_id, message.position);
      break;
    case 'agent_response':
      displayAgentSuggestion(message.response);
      break;
  }
}
```

## System Events

### Subscribe to System Events
```javascript
// Subscribe to system-wide events
ws.send(JSON.stringify({
  type: 'subscribe',
  subscription_type: 'system_events',
  events: ['agent_status', 'performance_metrics', 'error_alerts']
}));
```

### Event Types

#### Agent Status Updates
```javascript
{
  "type": "agent_status",
  "data": {
    "agent_type": "production_agent",
    "status": "busy",
    "current_task": "processing_query",
    "queue_length": 3,
    "estimated_wait_time": 5.2
  }
}
```

#### Performance Metrics
```javascript
{
  "type": "performance_metrics",
  "data": {
    "response_time_avg": 2.3,
    "success_rate": 0.94,
    "active_connections": 45,
    "queue_length": 12,
    "timestamp": "2024-01-15T10:00:00Z"
  }
}
```

#### Error Alerts
```javascript
{
  "type": "error_alert",
  "data": {
    "severity": "warning",
    "component": "llm_router",
    "message": "High response time detected",
    "details": {
      "avg_response_time": 8.5,
      "threshold": 5.0
    },
    "timestamp": "2024-01-15T10:00:00Z"
  }
}
```

## Error Handling

### WebSocket Error Types
```javascript
// Handle different error types
function handleWebSocketError(error) {
  switch (error.code) {
    case 'AUTHENTICATION_FAILED':
      // Redirect to login or refresh token
      refreshAuthToken();
      break;
    case 'RATE_LIMIT_EXCEEDED':
      // Show rate limit message and retry after delay
      showRateLimitMessage(error.retry_after);
      break;
    case 'SESSION_EXPIRED':
      // Reconnect with new session
      reconnectWithNewSession();
      break;
    case 'INVALID_MESSAGE_FORMAT':
      // Log error and continue
      console.error('Invalid message format:', error.details);
      break;
    default:
      console.error('Unknown WebSocket error:', error);
  }
}
```

### Connection State Management
```javascript
class ConnectionStateManager {
  constructor() {
    this.state = 'disconnected';
    this.listeners = [];
  }
  
  setState(newState) {
    const oldState = this.state;
    this.state = newState;
    
    this.listeners.forEach(listener => {
      listener(newState, oldState);
    });
  }
  
  onStateChange(callback) {
    this.listeners.push(callback);
  }
  
  isConnected() {
    return this.state === 'connected';
  }
  
  isConnecting() {
    return this.state === 'connecting';
  }
}

// Usage
const connectionState = new ConnectionStateManager();

connectionState.onStateChange((newState, oldState) => {
  updateUIConnectionStatus(newState);
  
  if (newState === 'connected' && oldState === 'connecting') {
    // Connection established, send queued messages
    sendQueuedMessages();
  }
});
```

## Frontend Integration Examples

### React Hook for WebSocket
```javascript
// hooks/useWebSocket.js
import { useState, useEffect, useRef, useCallback } from 'react';

export function useWebSocket(url, options = {}) {
  const [connectionStatus, setConnectionStatus] = useState('Disconnected');
  const [lastMessage, setLastMessage] = useState(null);
  const ws = useRef(null);
  const messageQueue = useRef([]);
  
  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return;
    
    setConnectionStatus('Connecting');
    ws.current = new WebSocket(url);
    
    ws.current.onopen = () => {
      setConnectionStatus('Connected');
      
      // Send queued messages
      while (messageQueue.current.length > 0) {
        const message = messageQueue.current.shift();
        ws.current.send(JSON.stringify(message));
      }
      
      if (options.onOpen) options.onOpen();
    };
    
    ws.current.onmessage = (event) => {
      const message = JSON.parse(event.data);
      setLastMessage(message);
      if (options.onMessage) options.onMessage(message);
    };
    
    ws.current.onclose = () => {
      setConnectionStatus('Disconnected');
      if (options.onClose) options.onClose();
      
      // Auto-reconnect after delay
      setTimeout(connect, 3000);
    };
    
    ws.current.onerror = (error) => {
      setConnectionStatus('Error');
      if (options.onError) options.onError(error);
    };
  }, [url, options]);
  
  const sendMessage = useCallback((message) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message));
    } else {
      messageQueue.current.push(message);
    }
  }, []);
  
  const disconnect = useCallback(() => {
    if (ws.current) {
      ws.current.close();
    }
  }, []);
  
  useEffect(() => {
    connect();
    return disconnect;
  }, [connect, disconnect]);
  
  return {
    connectionStatus,
    lastMessage,
    sendMessage,
    disconnect
  };
}
```

### Vue.js Composition API
```javascript
// composables/useWebSocket.js
import { ref, onMounted, onUnmounted } from 'vue';

export function useWebSocket(url, options = {}) {
  const connectionStatus = ref('Disconnected');
  const lastMessage = ref(null);
  let ws = null;
  let messageQueue = [];
  
  const connect = () => {
    connectionStatus.value = 'Connecting';
    ws = new WebSocket(url);
    
    ws.onopen = () => {
      connectionStatus.value = 'Connected';
      
      // Send queued messages
      while (messageQueue.length > 0) {
        const message = messageQueue.shift();
        ws.send(JSON.stringify(message));
      }
      
      if (options.onOpen) options.onOpen();
    };
    
    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      lastMessage.value = message;
      if (options.onMessage) options.onMessage(message);
    };
    
    ws.onclose = () => {
      connectionStatus.value = 'Disconnected';
      if (options.onClose) options.onClose();
      
      // Auto-reconnect
      setTimeout(connect, 3000);
    };
  };
  
  const sendMessage = (message) => {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(message));
    } else {
      messageQueue.push(message);
    }
  };
  
  const disconnect = () => {
    if (ws) {
      ws.close();
    }
  };
  
  onMounted(connect);
  onUnmounted(disconnect);
  
  return {
    connectionStatus,
    lastMessage,
    sendMessage,
    disconnect
  };
}
```

## Performance Optimization

### Message Batching
```javascript
class MessageBatcher {
  constructor(ws, batchSize = 10, flushInterval = 100) {
    this.ws = ws;
    this.batchSize = batchSize;
    this.flushInterval = flushInterval;
    this.batch = [];
    this.timer = null;
  }
  
  send(message) {
    this.batch.push(message);
    
    if (this.batch.length >= this.batchSize) {
      this.flush();
    } else if (!this.timer) {
      this.timer = setTimeout(() => this.flush(), this.flushInterval);
    }
  }
  
  flush() {
    if (this.batch.length > 0) {
      this.ws.send(JSON.stringify({
        type: 'batch',
        messages: this.batch
      }));
      this.batch = [];
    }
    
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
  }
}
```

### Connection Pooling
```javascript
class WebSocketPool {
  constructor(baseUrl, poolSize = 3) {
    this.baseUrl = baseUrl;
    this.poolSize = poolSize;
    this.connections = [];
    this.currentIndex = 0;
    
    this.initializePool();
  }
  
  initializePool() {
    for (let i = 0; i < this.poolSize; i++) {
      const ws = new WebSocket(this.baseUrl);
      this.connections.push(ws);
    }
  }
  
  getConnection() {
    const connection = this.connections[this.currentIndex];
    this.currentIndex = (this.currentIndex + 1) % this.poolSize;
    return connection;
  }
  
  send(message) {
    const connection = this.getConnection();
    if (connection.readyState === WebSocket.OPEN) {
      connection.send(JSON.stringify(message));
    }
  }
}
```

This WebSocket API guide provides comprehensive documentation for frontend developers to integrate real-time features with the GremlinsAI backend, including chat, collaboration, and system events with proper error handling and performance optimization.
