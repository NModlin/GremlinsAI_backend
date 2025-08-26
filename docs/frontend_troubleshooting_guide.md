# GremlinsAI Frontend Troubleshooting Guide

## Quick Diagnostic Checklist

When encountering frontend issues, run through this checklist:

### 1. Backend Connectivity
```bash
# Test if backend is running
curl http://localhost:8000/
# Expected: {"message": "Simple RAG Server", "status": "running"}

# Test specific endpoint
curl -X POST http://localhost:8000/api/v1/agent/simple-chat \
  -H "Content-Type: application/json" \
  -d '{"input": "test message"}'
```

### 2. Browser Console Check
1. Open Developer Tools (F12)
2. Go to Console tab
3. Look for:
   - Red error messages
   - Network request failures
   - CORS errors
   - JavaScript syntax errors

### 3. Network Tab Analysis
1. Open Developer Tools → Network tab
2. Trigger the failing action
3. Check for:
   - Request URL correctness
   - HTTP status codes (200, 404, 500, etc.)
   - Request/response headers
   - Request payload format

## Common Error Patterns

### "Sorry, I encountered an error"

**Symptoms**: Generic error message in chat interface

**Debugging Steps**:
```javascript
// Add this debugging code to your chat function
console.log('🚀 Request URL:', requestUrl);
console.log('📤 Request body:', requestBody);
console.log('📊 Response status:', response.status);
console.log('📥 Response data:', await response.clone().json());
```

**Common Causes**:
- API endpoint mismatch (`/api/v1/agent/chat` vs `/api/v1/agent/simple-chat`)
- Request format mismatch (`{message: "text"}` vs `{input: "text"}`)
- Backend not running or crashed
- CORS configuration issues

### CORS Errors

**Symptoms**: 
```
Access to fetch at 'http://localhost:8000/...' from origin 'file://' 
has been blocked by CORS policy
```

**Solutions**:
1. Ensure backend has CORS middleware configured
2. Use a local web server instead of opening HTML files directly
3. Check that `allow_origins` includes your frontend origin

### API Endpoint Not Found (404)

**Symptoms**: HTTP 404 errors in Network tab

**Common Mismatches**:
```javascript
// ❌ Frontend calls
fetch('/api/v1/agent/chat')
// ✅ Backend serves
fetch('/api/v1/agent/simple-chat')

// ❌ Frontend calls  
fetch('/api/v1/upload/query')
// ✅ Backend serves
fetch('/api/v1/agent/simple-chat') // for chat with RAG
```

### Request Format Errors (422)

**Symptoms**: HTTP 422 Unprocessable Entity

**Common Format Issues**:
```javascript
// ❌ Wrong request format
{ message: "Hello" }
// ✅ Correct format
{ input: "Hello" }

// ❌ Wrong response handling
data.response
// ✅ Correct response handling  
data.output
```

## Debugging Tools

### Enhanced Logging Function
```javascript
function debugLog(category, message, data = null) {
    const timestamp = new Date().toISOString();
    console.group(`🔍 [${timestamp}] ${category}`);
    console.log(message);
    if (data) {
        console.log('Data:', data);
    }
    console.trace('Call stack');
    console.groupEnd();
}

// Usage
debugLog('API Request', 'Sending chat message', { endpoint, body });
debugLog('API Response', 'Received response', { status, data });
debugLog('Error', 'Request failed', { error: error.message });
```

### Network Request Inspector
```javascript
// Wrap fetch with debugging
const originalFetch = window.fetch;
window.fetch = async function(...args) {
    const [url, options] = args;
    
    console.log('🌐 Fetch Request:', {
        url,
        method: options?.method || 'GET',
        headers: options?.headers,
        body: options?.body
    });
    
    try {
        const response = await originalFetch(...args);
        console.log('🌐 Fetch Response:', {
            url,
            status: response.status,
            statusText: response.statusText,
            headers: Object.fromEntries(response.headers.entries())
        });
        return response;
    } catch (error) {
        console.error('🌐 Fetch Error:', { url, error });
        throw error;
    }
};
```

## Testing Strategies

### Manual Testing Checklist

**Backend Health Check**:
- [ ] Backend server starts without errors
- [ ] Health endpoint responds: `GET http://localhost:8000/`
- [ ] API documentation accessible: `http://localhost:8000/docs`

**Document Upload Flow**:
- [ ] File upload works: drag & drop or click upload
- [ ] Upload progress indicator shows
- [ ] Document appears in sidebar after upload
- [ ] Document processing completes (shows chunk count)

**Chat Functionality**:
- [ ] Chat input accepts text
- [ ] Send button triggers request
- [ ] Loading indicator appears during processing
- [ ] Response appears in chat interface
- [ ] Citations display correctly (if documents uploaded)
- [ ] Error messages are specific and helpful

**RAG Integration**:
- [ ] RAG indicator shows when documents are uploaded
- [ ] Chat responses reference uploaded documents
- [ ] Citations are clickable and functional
- [ ] Document search works correctly

### Automated Testing Setup

```javascript
// Basic integration test
async function runIntegrationTest() {
    const results = [];
    
    // Test 1: Backend connectivity
    try {
        const response = await fetch('http://localhost:8000/');
        results.push({
            test: 'Backend Health',
            status: response.ok ? 'PASS' : 'FAIL',
            details: `Status: ${response.status}`
        });
    } catch (error) {
        results.push({
            test: 'Backend Health',
            status: 'FAIL',
            details: error.message
        });
    }
    
    // Test 2: Chat endpoint
    try {
        const response = await fetch('http://localhost:8000/api/v1/agent/simple-chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ input: 'test message' })
        });
        
        const data = await response.json();
        const hasRequiredFields = 'output' in data && 'citations' in data;
        
        results.push({
            test: 'Chat Endpoint',
            status: response.ok && hasRequiredFields ? 'PASS' : 'FAIL',
            details: `Status: ${response.status}, Fields: ${Object.keys(data).join(', ')}`
        });
    } catch (error) {
        results.push({
            test: 'Chat Endpoint',
            status: 'FAIL',
            details: error.message
        });
    }
    
    // Display results
    console.table(results);
    return results;
}

// Run test
runIntegrationTest();
```

## Performance Troubleshooting

### Slow Response Times

**Diagnostic Steps**:
1. Check Network tab for request timing
2. Look for backend processing delays
3. Monitor browser memory usage
4. Check for JavaScript blocking operations

**Common Causes**:
- Large document processing
- Inefficient search algorithms
- Memory leaks in frontend
- Network latency issues

**Solutions**:
```javascript
// Add request timeout
const controller = new AbortController();
const timeoutId = setTimeout(() => controller.abort(), 30000); // 30s timeout

try {
    const response = await fetch(url, {
        ...options,
        signal: controller.signal
    });
    clearTimeout(timeoutId);
    return response;
} catch (error) {
    if (error.name === 'AbortError') {
        throw new Error('Request timed out after 30 seconds');
    }
    throw error;
}
```

### Memory Leaks

**Detection**:
```javascript
// Monitor memory usage
function logMemoryUsage() {
    if (performance.memory) {
        console.log('Memory Usage:', {
            used: Math.round(performance.memory.usedJSHeapSize / 1048576) + ' MB',
            total: Math.round(performance.memory.totalJSHeapSize / 1048576) + ' MB',
            limit: Math.round(performance.memory.jsHeapSizeLimit / 1048576) + ' MB'
        });
    }
}

// Call periodically
setInterval(logMemoryUsage, 10000);
```

**Prevention**:
- Remove event listeners when components unmount
- Clear intervals and timeouts
- Avoid global variable accumulation
- Use WeakMap/WeakSet for temporary references

## Environment-Specific Issues

### Development Environment
- Use `http://localhost:8000` for backend URL
- Enable debug logging
- Allow longer timeouts for debugging

### Production Environment  
- Use HTTPS URLs
- Disable debug logging
- Implement proper error reporting
- Add request retry logic
- Configure appropriate timeouts

### File Protocol Issues
When opening HTML files directly (`file://`):
- CORS restrictions are stricter
- Some APIs may not work
- Use a local web server instead:

```bash
# Python 3
python -m http.server 8080

# Node.js
npx serve .

# PHP
php -S localhost:8080
```

## Recovery Procedures

### When Everything Fails
1. **Clear browser cache and cookies**
2. **Restart backend server**
3. **Check backend logs for errors**
4. **Verify API endpoints with curl/Postman**
5. **Test with minimal HTML page**
6. **Check network connectivity**
7. **Verify CORS configuration**

### Minimal Test Page
```html
<!DOCTYPE html>
<html>
<head>
    <title>GremlinsAI Test</title>
</head>
<body>
    <button onclick="testBackend()">Test Backend</button>
    <div id="result"></div>
    
    <script>
    async function testBackend() {
        const result = document.getElementById('result');
        
        try {
            const response = await fetch('http://localhost:8000/api/v1/agent/simple-chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ input: 'test' })
            });
            
            const data = await response.json();
            result.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
        } catch (error) {
            result.innerHTML = `<div style="color: red;">Error: ${error.message}</div>`;
        }
    }
    </script>
</body>
</html>
```

This minimal page can help isolate whether issues are in your main application or in the basic connectivity.
