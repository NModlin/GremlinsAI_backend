# Getting Started with the gremlinsAI API

Welcome! This guide will walk you through making your first API call to our agent and exploring the comprehensive capabilities of the gremlinsAI platform.

## 1. Overview

gremlinsAI is a sophisticated, headless, multi-modal AI system that provides:

- **Core Agent Intelligence** with LangGraph and tool integration
- **Persistent Conversation Management** with full chat history
- **Multi-Agent Collaboration** with specialized agent workflows
- **Document Knowledge Capabilities** with vector search and RAG
- **Advanced Orchestration** with asynchronous task execution
- **Modern API Architecture** with REST, GraphQL, and WebSocket APIs

## 2. API Architecture

The gremlinsAI platform provides three complementary API interfaces:

### REST API
Traditional REST endpoints for all system functionality:
- **Base URL**: `http://localhost:8000/api/v1/`
- **Documentation**: Available at `http://localhost:8000/docs`
- **Format**: JSON request/response

### GraphQL API
Modern, flexible query language with real-time subscriptions:
- **Endpoint**: `http://localhost:8000/graphql`
- **Playground**: Interactive query builder available
- **Features**: Queries, mutations, and subscriptions

### WebSocket API
Real-time bidirectional communication:
- **Endpoint**: `ws://localhost:8000/api/v1/ws/ws`
- **Protocol**: JSON message-based communication
- **Features**: Live updates and subscriptions

## 3. Quick Start

### Prerequisites

Make sure you have Python 3.11+ and the following packages installed:

```bash
pip install requests websockets graphql-core
```

### Your First API Call

Use the following Python script to invoke our agent:

```python
import requests

API_URL = "http://localhost:8000/api/v1/agent/invoke"

payload = {
    "input": "What are the latest advancements in AI?"
}

response = requests.post(API_URL, json=payload)

if response.status_code == 200:
    result = response.json()
    print("Success:")
    print(f"Response: {result['output']}")
    print(f"Execution Time: {result['execution_time']:.2f}s")
else:
    print(f"Error {response.status_code}:")
    print(response.text)
```

### GraphQL Query Example

```python
import requests

GRAPHQL_URL = "http://localhost:8000/graphql"

query = """
query GetConversations {
  conversations(limit: 5) {
    id
    title
    created_at
    messages {
      role
      content
      created_at
    }
  }
}
"""

response = requests.post(GRAPHQL_URL, json={"query": query})
print(response.json())
```

### WebSocket Connection Example

```python
import asyncio
import websockets
import json

async def websocket_example():
    uri = "ws://localhost:8000/api/v1/ws/ws"
    
    async with websockets.connect(uri) as websocket:
        # Subscribe to conversation updates
        subscribe_message = {
            "type": "subscribe",
            "subscription_type": "conversation",
            "conversation_id": "your-conversation-id"
        }
        
        await websocket.send(json.dumps(subscribe_message))
        
        # Listen for updates
        async for message in websocket:
            data = json.loads(message)
            print(f"Received: {data}")

# Run the WebSocket example
asyncio.run(websocket_example())
```

## 4. Core Concepts

### Conversations
All interactions are organized into conversations that persist across sessions:

```python
# Create a new conversation
response = requests.post("http://localhost:8000/api/v1/history/conversations", 
                        json={"title": "My AI Chat"})
conversation_id = response.json()["id"]

# Add a message to the conversation
requests.post(f"http://localhost:8000/api/v1/history/conversations/{conversation_id}/messages",
              json={"role": "user", "content": "Hello, AI!"})
```

### Multi-Agent Workflows
Execute complex workflows using specialized agents:

```python
# Execute a multi-agent research workflow
payload = {
    "workflow_type": "research_analyze_write",
    "input": "Analyze the impact of AI on healthcare",
    "conversation_id": conversation_id,
    "save_conversation": True
}

response = requests.post("http://localhost:8000/api/v1/multi-agent/execute", json=payload)
```

### Document Knowledge (RAG)
Upload documents and query them using semantic search:

```python
# Upload a document
files = {"file": open("document.pdf", "rb")}
response = requests.post("http://localhost:8000/api/v1/documents/upload", files=files)

# Query documents
query_payload = {
    "query": "What are the key findings?",
    "limit": 5,
    "use_rag": True
}
response = requests.post("http://localhost:8000/api/v1/documents/search", json=query_payload)
```

### Asynchronous Task Execution
Execute long-running tasks asynchronously:

```python
# Execute an async task
task_payload = {
    "task_type": "comprehensive_workflow",
    "payload": {
        "name": "Research Project",
        "input": "Comprehensive analysis of renewable energy trends"
    },
    "execution_mode": "async"
}

response = requests.post("http://localhost:8000/api/v1/orchestrator/execute", json=task_payload)
task_id = response.json()["task_id"]

# Check task status
status_response = requests.get(f"http://localhost:8000/api/v1/orchestrator/tasks/{task_id}/status")
```

## 5. Authentication & Security

Currently, the API operates without authentication for development purposes. In production deployments:

- API keys will be required for all requests
- Rate limiting will be enforced
- HTTPS will be mandatory for all communications

```python
# Future authentication pattern
headers = {
    "Authorization": "Bearer YOUR_API_KEY",
    "Content-Type": "application/json"
}

response = requests.post(API_URL, headers=headers, json=payload)
```

## 6. Error Handling

The API uses standard HTTP status codes and provides detailed error information:

```python
try:
    response = requests.post(API_URL, json=payload)
    response.raise_for_status()  # Raises an HTTPError for bad responses
    
    result = response.json()
    print(result)
    
except requests.exceptions.HTTPError as e:
    error_data = response.json()
    print(f"API Error: {error_data.get('message', 'Unknown error')}")
    print(f"Details: {error_data.get('details', 'No details available')}")
    
except requests.exceptions.RequestException as e:
    print(f"Request failed: {e}")
```

## 7. Rate Limits & Best Practices

### Best Practices
- **Reuse Conversations**: Keep related interactions in the same conversation
- **Use Appropriate APIs**: Choose REST for simple operations, GraphQL for complex queries, WebSocket for real-time updates
- **Handle Errors Gracefully**: Always implement proper error handling
- **Monitor Performance**: Use the built-in execution time metrics

### Performance Tips
- **Batch Operations**: Use multi-agent workflows for complex tasks
- **Async Execution**: Use async mode for long-running operations
- **Efficient Queries**: Use GraphQL to request only needed data
- **Connection Reuse**: Reuse HTTP connections when making multiple requests

## 8. Next Steps

- **Explore the API Documentation**: Visit `http://localhost:8000/docs` for interactive API documentation
- **Try GraphQL Playground**: Access `http://localhost:8000/graphql` for interactive GraphQL queries
- **Check Out Examples**: See the `examples/` directory for comprehensive code samples
- **Read the Tutorials**: Explore specific use cases in the `docs/tutorials/` directory
- **Join the Community**: Connect with other developers using gremlinsAI

## 9. Support & Resources

- **API Documentation**: `http://localhost:8000/docs`
- **GraphQL Playground**: `http://localhost:8000/graphql`
- **System Health**: `http://localhost:8000/api/v1/realtime/system/status`
- **GitHub Repository**: [Link to repository]
- **Community Forum**: [Link to forum]
- **Support Email**: support@gremlinsai.com

---

Ready to build something amazing with gremlinsAI? Let's get started! 🚀
