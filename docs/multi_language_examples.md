# GremlinsAI Multi-Language Integration Examples

## JavaScript/TypeScript Examples

### React Hook for GremlinsAI

```typescript
// useGremlinsAI.ts
import { useState, useEffect, useCallback } from 'react';

interface GremlinsConfig {
  baseURL: string;
  apiKey: string;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export const useGremlinsAI = (config: GremlinsConfig) => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversation, setCurrentConversation] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const apiRequest = useCallback(async (endpoint: string, options: RequestInit = {}) => {
    const response = await fetch(`${config.baseURL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${config.apiKey}`,
        'X-API-Version': '9.0.0',
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error_message || 'API request failed');
    }

    return response.json();
  }, [config]);

  const createConversation = useCallback(async (title: string) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const conversation = await apiRequest('/api/v1/history/conversations', {
        method: 'POST',
        body: JSON.stringify({ title }),
      });
      
      setConversations(prev => [conversation, ...prev]);
      setCurrentConversation(conversation.id);
      setMessages([]);
      
      return conversation;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create conversation');
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [apiRequest]);

  const sendMessage = useCallback(async (content: string) => {
    if (!currentConversation) {
      throw new Error('No active conversation');
    }

    setIsLoading(true);
    setError(null);

    // Add user message immediately
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMessage]);

    try {
      const response = await apiRequest('/api/v1/agent/chat', {
        method: 'POST',
        body: JSON.stringify({
          input: content,
          conversation_id: currentConversation,
          save_conversation: true,
        }),
      });

      const aiMessage: Message = {
        id: response.message_id || Date.now().toString(),
        role: 'assistant',
        content: response.output,
        timestamp: new Date(),
      };
      
      setMessages(prev => [...prev, aiMessage]);
      
      return response;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send message');
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [currentConversation, apiRequest]);

  const loadConversations = useCallback(async () => {
    try {
      const response = await apiRequest('/api/v1/history/conversations?limit=50');
      setConversations(response.conversations);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load conversations');
    }
  }, [apiRequest]);

  const loadMessages = useCallback(async (conversationId: string) => {
    try {
      const response = await apiRequest(
        `/api/v1/history/conversations/${conversationId}?include_messages=true`
      );
      
      const formattedMessages: Message[] = response.messages.map((msg: any) => ({
        id: msg.id,
        role: msg.role,
        content: msg.content,
        timestamp: new Date(msg.created_at),
      }));
      
      setMessages(formattedMessages);
      setCurrentConversation(conversationId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load messages');
    }
  }, [apiRequest]);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  return {
    conversations,
    currentConversation,
    messages,
    isLoading,
    error,
    createConversation,
    sendMessage,
    loadMessages,
    loadConversations,
  };
};
```

### Vue.js Composition API

```typescript
// useGremlinsAI.ts (Vue 3)
import { ref, reactive, computed } from 'vue';

export function useGremlinsAI(config: { baseURL: string; apiKey: string }) {
  const state = reactive({
    conversations: [] as Conversation[],
    currentConversation: null as string | null,
    messages: [] as Message[],
    isLoading: false,
    error: null as string | null,
  });

  const apiRequest = async (endpoint: string, options: RequestInit = {}) => {
    const response = await fetch(`${config.baseURL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${config.apiKey}`,
        'X-API-Version': '9.0.0',
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error_message || 'API request failed');
    }

    return response.json();
  };

  const sendMessage = async (content: string) => {
    if (!state.currentConversation) {
      throw new Error('No active conversation');
    }

    state.isLoading = true;
    state.error = null;

    try {
      const response = await apiRequest('/api/v1/agent/chat', {
        method: 'POST',
        body: JSON.stringify({
          input: content,
          conversation_id: state.currentConversation,
          save_conversation: true,
        }),
      });

      // Add messages to state
      state.messages.push(
        { id: Date.now().toString(), role: 'user', content, timestamp: new Date() },
        { id: response.message_id, role: 'assistant', content: response.output, timestamp: new Date() }
      );

      return response;
    } catch (err) {
      state.error = err instanceof Error ? err.message : 'Failed to send message';
      throw err;
    } finally {
      state.isLoading = false;
    }
  };

  return {
    ...state,
    sendMessage,
    // ... other methods
  };
}
```

## Python Examples

### Using requests library

```python
import requests
import json
from typing import Dict, List, Optional, Any

class GremlinsAIClient:
    def __init__(self, base_url: str = "http://localhost:8000", api_key: str = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}',
            'X-API-Version': '9.0.0'
        })

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make a request to the GremlinsAI API."""
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            try:
                error_data = response.json()
                raise GremlinsAIError(
                    error_data.get('error_message', str(e)),
                    error_data.get('error_code', 'HTTP_ERROR'),
                    response.status_code
                )
            except json.JSONDecodeError:
                raise GremlinsAIError(str(e), 'HTTP_ERROR', response.status_code)
        except requests.exceptions.RequestException as e:
            raise GremlinsAIError(str(e), 'REQUEST_ERROR')

    def chat(self, message: str, conversation_id: Optional[str] = None, 
             use_multi_agent: bool = False) -> Dict[str, Any]:
        """Send a chat message to GremlinsAI."""
        data = {
            'input': message,
            'save_conversation': True
        }
        
        if conversation_id:
            data['conversation_id'] = conversation_id
            
        params = {'use_multi_agent': use_multi_agent} if use_multi_agent else {}
        
        return self._request('POST', '/api/v1/agent/chat', 
                           json=data, params=params)

    def create_conversation(self, title: str, initial_message: Optional[str] = None) -> Dict[str, Any]:
        """Create a new conversation."""
        data = {'title': title}
        if initial_message:
            data['initial_message'] = initial_message
            
        return self._request('POST', '/api/v1/history/conversations', json=data)

    def get_conversations(self, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """Get list of conversations."""
        params = {'limit': limit, 'offset': offset}
        return self._request('GET', '/api/v1/history/conversations', params=params)

    def upload_document(self, file_path: str, title: Optional[str] = None, 
                       metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Upload a document for RAG processing."""
        with open(file_path, 'rb') as f:
            files = {'file': f}
            data = {}
            
            if metadata:
                data['metadata'] = json.dumps(metadata)
                
            # Remove Content-Type header for file upload
            headers = {k: v for k, v in self.session.headers.items() 
                      if k.lower() != 'content-type'}
            
            response = requests.post(
                f"{self.base_url}/api/v1/documents/upload",
                files=files,
                data=data,
                headers=headers
            )
            response.raise_for_status()
            return response.json()

    def search_documents(self, query: str, limit: int = 10, 
                        search_type: str = 'chunks') -> Dict[str, Any]:
        """Search documents using semantic search."""
        data = {
            'query': query,
            'limit': limit,
            'search_type': search_type
        }
        return self._request('POST', '/api/v1/documents/search', json=data)

    def rag_query(self, query: str, use_multi_agent: bool = True, 
                  search_limit: int = 5, conversation_id: Optional[str] = None) -> Dict[str, Any]:
        """Perform a RAG query against uploaded documents."""
        data = {
            'query': query,
            'use_multi_agent': use_multi_agent,
            'search_limit': search_limit
        }
        
        if conversation_id:
            data['conversation_id'] = conversation_id
            
        return self._request('POST', '/api/v1/documents/rag', json=data)

    def execute_multi_agent_workflow(self, workflow_type: str, input_text: str,
                                   conversation_id: Optional[str] = None,
                                   agent_config: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute a multi-agent workflow."""
        data = {
            'workflow_type': workflow_type,
            'input': input_text
        }
        
        if conversation_id:
            data['conversation_id'] = conversation_id
        if agent_config:
            data['agent_config'] = agent_config
            
        return self._request('POST', '/api/v1/multi-agent/execute', json=data)

class GremlinsAIError(Exception):
    """Custom exception for GremlinsAI API errors."""
    def __init__(self, message: str, error_code: str = None, status_code: int = None):
        super().__init__(message)
        self.error_code = error_code
        self.status_code = status_code

# Usage example
if __name__ == "__main__":
    client = GremlinsAIClient(api_key="your_api_key_here")
    
    try:
        # Create a conversation
        conversation = client.create_conversation("Python API Test")
        conv_id = conversation['id']
        
        # Send a message
        response = client.chat("What is machine learning?", conversation_id=conv_id)
        print(f"AI Response: {response['output']}")
        
        # Upload a document
        doc_response = client.upload_document(
            "example.txt", 
            metadata={"category": "research", "source": "python_client"}
        )
        print(f"Document uploaded: {doc_response['id']}")
        
        # Perform RAG query
        rag_response = client.rag_query("What does the document say about AI?")
        print(f"RAG Answer: {rag_response['answer']}")
        
    except GremlinsAIError as e:
        print(f"API Error: {e} (Code: {e.error_code})")
```

### Using httpx (async)

```python
import httpx
import asyncio
from typing import Dict, List, Optional, Any

class AsyncGremlinsAIClient:
    def __init__(self, base_url: str = "http://localhost:8000", api_key: str = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}',
            'X-API-Version': '9.0.0'
        }

    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make an async request to the GremlinsAI API."""
        url = f"{self.base_url}{endpoint}"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(
                    method, url, headers=self.headers, **kwargs
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                try:
                    error_data = response.json()
                    raise GremlinsAIError(
                        error_data.get('error_message', str(e)),
                        error_data.get('error_code', 'HTTP_ERROR'),
                        response.status_code
                    )
                except Exception:
                    raise GremlinsAIError(str(e), 'HTTP_ERROR', response.status_code)

    async def chat(self, message: str, conversation_id: Optional[str] = None) -> Dict[str, Any]:
        """Send a chat message asynchronously."""
        data = {
            'input': message,
            'save_conversation': True
        }
        
        if conversation_id:
            data['conversation_id'] = conversation_id
            
        return await self._request('POST', '/api/v1/agent/chat', json=data)

    async def stream_chat(self, message: str, conversation_id: Optional[str] = None):
        """Stream chat responses (if WebSocket is available)."""
        # This would implement WebSocket streaming
        # For now, we'll simulate with regular chat
        response = await self.chat(message, conversation_id)
        yield response['output']

# Usage example
async def main():
    client = AsyncGremlinsAIClient(api_key="your_api_key_here")
    
    try:
        response = await client.chat("Hello, GremlinsAI!")
        print(f"Response: {response['output']}")
        
        # Stream example
        async for chunk in client.stream_chat("Tell me a story"):
            print(chunk, end='', flush=True)
            
    except GremlinsAIError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
```
