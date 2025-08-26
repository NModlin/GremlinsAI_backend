# GremlinsAI Frontend Quick Reference

## Essential API Endpoints

| Endpoint | Method | Request | Response | Purpose |
|----------|--------|---------|----------|---------|
| `/` | GET | - | `{message, status}` | Health check |
| `/api/v1/agent/simple-chat` | POST | `{input: string}` | `{output: string, citations: array}` | Chat with RAG |
| `/api/v1/upload/upload` | POST | FormData | `{document_id, filename, chunks}` | Upload document |
| `/api/v1/upload/list` | GET | - | `{documents: array, total: number}` | List documents |
| `/api/v1/upload/query` | POST | `{query, max_results, similarity_threshold}` | `{results: array, answer: string}` | Direct RAG query |

## Quick Setup

### Basic Chat Interface
```javascript
async function sendMessage(message) {
    const response = await fetch('http://localhost:8000/api/v1/agent/simple-chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ input: message })
    });
    
    if (response.ok) {
        const data = await response.json();
        return { text: data.output, citations: data.citations };
    }
    
    throw new Error(`HTTP ${response.status}`);
}
```

### Document Upload
```javascript
async function uploadDocument(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch('http://localhost:8000/api/v1/upload/upload', {
        method: 'POST',
        body: formData
    });
    
    if (response.ok) {
        return await response.json();
    }
    
    throw new Error(`Upload failed: ${response.status}`);
}
```

## Common Issues & Quick Fixes

### "Sorry, I encountered an error"
**Cause**: API endpoint mismatch
**Fix**: Ensure using `/api/v1/agent/simple-chat` with `{input: "message"}` format

### CORS Errors
**Cause**: Missing CORS headers
**Fix**: Backend needs CORS middleware configured

### 404 Not Found
**Cause**: Wrong endpoint URL
**Fix**: Check exact endpoint paths in backend documentation

### 422 Unprocessable Entity
**Cause**: Wrong request format
**Fix**: Use `{input: "text"}` not `{message: "text"}`

## Debugging Checklist

1. **Backend Running?** → `curl http://localhost:8000/`
2. **Console Errors?** → F12 → Console tab
3. **Network Issues?** → F12 → Network tab
4. **Request Format?** → Check `{input: "message"}` format
5. **Response Format?** → Expect `{output: "text", citations: []}`

## Environment Configuration

### Development
```javascript
const config = {
    baseURL: 'http://localhost:8000',
    debug: true,
    timeout: 30000
};
```

### Production
```javascript
const config = {
    baseURL: 'https://api.gremlinsai.com',
    debug: false,
    timeout: 10000
};
```

## Error Handling Template

```javascript
async function safeApiCall(url, options) {
    try {
        const response = await fetch(url, options);
        
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API call failed:', error);
        
        if (error.message.includes('Failed to fetch')) {
            throw new Error('Cannot connect to GremlinsAI backend. Please ensure the server is running.');
        }
        
        throw error;
    }
}
```

## Testing Commands

### Backend Health
```bash
curl http://localhost:8000/
```

### Chat Test
```bash
curl -X POST http://localhost:8000/api/v1/agent/simple-chat \
  -H "Content-Type: application/json" \
  -d '{"input": "Hello, world!"}'
```

### Upload Test
```bash
curl -X POST http://localhost:8000/api/v1/upload/upload \
  -F "file=@test.txt"
```

## Performance Tips

### Request Debouncing
```javascript
let requestTimeout;
function debouncedSend(message) {
    clearTimeout(requestTimeout);
    requestTimeout = setTimeout(() => sendMessage(message), 300);
}
```

### Response Caching
```javascript
const cache = new Map();
async function cachedRequest(key, requestFn) {
    if (cache.has(key)) return cache.get(key);
    const result = await requestFn();
    cache.set(key, result);
    return result;
}
```

### Request Timeout
```javascript
const controller = new AbortController();
setTimeout(() => controller.abort(), 30000);

fetch(url, { 
    ...options, 
    signal: controller.signal 
});
```

## HTML Template

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GremlinsAI Chat</title>
    <style>
        .chat-container { max-width: 800px; margin: 0 auto; padding: 20px; }
        .messages { height: 400px; overflow-y: auto; border: 1px solid #ddd; padding: 15px; margin-bottom: 15px; }
        .message { margin-bottom: 15px; padding: 10px; border-radius: 8px; }
        .user-message { background: #e3f2fd; text-align: right; }
        .ai-message { background: #f5f5f5; }
        .input-area { display: flex; gap: 10px; }
        .input-area input { flex: 1; padding: 12px; border: 1px solid #ddd; border-radius: 6px; }
        .input-area button { padding: 12px 24px; background: #2196f3; color: white; border: none; border-radius: 6px; cursor: pointer; }
        .error { background: #ffebee; color: #c62828; padding: 10px; border-radius: 4px; margin: 10px 0; }
        .citation { color: #1976d2; cursor: pointer; text-decoration: underline; }
    </style>
</head>
<body>
    <div class="chat-container">
        <h1>GremlinsAI Chat Interface</h1>
        <div id="messages" class="messages"></div>
        <div class="input-area">
            <input type="text" id="messageInput" placeholder="Type your message..." onkeypress="if(event.key==='Enter') sendMessage()" />
            <button onclick="sendMessage()">Send</button>
        </div>
    </div>

    <script>
        async function sendMessage() {
            const input = document.getElementById('messageInput');
            const messages = document.getElementById('messages');
            const message = input.value.trim();
            
            if (!message) return;
            
            // Add user message
            messages.innerHTML += `<div class="message user-message">${message}</div>`;
            input.value = '';
            
            try {
                const response = await fetch('http://localhost:8000/api/v1/agent/simple-chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ input: message })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    let responseText = data.output;
                    
                    if (data.citations && data.citations.length > 0) {
                        const citationText = data.citations.map(c => 
                            `<span class="citation">[${c.document}, Page ${c.page}]</span>`
                        ).join(' ');
                        responseText += `<br><br>Sources: ${citationText}`;
                    }
                    
                    messages.innerHTML += `<div class="message ai-message">${responseText}</div>`;
                } else {
                    throw new Error(`HTTP ${response.status}`);
                }
            } catch (error) {
                messages.innerHTML += `<div class="error">Error: ${error.message}</div>`;
            }
            
            messages.scrollTop = messages.scrollHeight;
        }
    </script>
</body>
</html>
```

## Support Resources

- **Troubleshooting Guide**: [frontend_troubleshooting_guide.md](frontend_troubleshooting_guide.md)
- **Comprehensive Guide**: [frontend_integration_comprehensive.md](frontend_integration_comprehensive.md)
- **API Documentation**: `http://localhost:8000/docs` (when backend is running)
- **Example Code**: `/examples/frontend/` directory
