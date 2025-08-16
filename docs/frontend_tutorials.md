# GremlinsAI Frontend Integration Tutorials

## Tutorial 1: Building a Chat Interface

### Step 1: Basic HTML Structure

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GremlinsAI Chat Interface</title>
    <style>
        .chat-container { max-width: 800px; margin: 0 auto; padding: 20px; }
        .messages { height: 400px; overflow-y: auto; border: 1px solid #ccc; padding: 10px; margin-bottom: 10px; }
        .message { margin-bottom: 10px; padding: 8px; border-radius: 8px; }
        .user-message { background-color: #e3f2fd; text-align: right; }
        .ai-message { background-color: #f5f5f5; }
        .input-area { display: flex; gap: 10px; }
        .input-area input { flex: 1; padding: 10px; border: 1px solid #ccc; border-radius: 4px; }
        .input-area button { padding: 10px 20px; background: #2196f3; color: white; border: none; border-radius: 4px; cursor: pointer; }
    </style>
</head>
<body>
    <div class="chat-container">
        <h1>GremlinsAI Chat</h1>
        <div id="messages" class="messages"></div>
        <div class="input-area">
            <input type="text" id="messageInput" placeholder="Type your message..." />
            <button onclick="sendMessage()">Send</button>
        </div>
    </div>
</body>
</html>
```

### Step 2: JavaScript Chat Implementation

```javascript
class ChatInterface {
    constructor() {
        this.client = new GremlinsAIClient({
            baseURL: 'http://localhost:8000',
            apiKey: 'your_api_key_here'
        });
        this.conversationId = null;
        this.messagesContainer = document.getElementById('messages');
        this.messageInput = document.getElementById('messageInput');
        
        this.initializeChat();
    }

    async initializeChat() {
        try {
            // Create a new conversation
            const conversation = await this.client.request('/api/v1/history/conversations', {
                method: 'POST',
                body: JSON.stringify({
                    title: `Chat Session ${new Date().toLocaleString()}`
                })
            });
            
            this.conversationId = conversation.id;
            this.addMessage('system', 'Chat initialized. How can I help you today?');
        } catch (error) {
            console.error('Failed to initialize chat:', error);
            this.addMessage('system', 'Failed to initialize chat. Please check your connection.');
        }
    }

    addMessage(role, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role === 'user' ? 'user-message' : 'ai-message'}`;
        messageDiv.innerHTML = `
            <strong>${role === 'user' ? 'You' : 'GremlinsAI'}:</strong>
            <div>${content}</div>
            <small>${new Date().toLocaleTimeString()}</small>
        `;
        
        this.messagesContainer.appendChild(messageDiv);
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

    async sendMessage() {
        const input = this.messageInput.value.trim();
        if (!input) return;

        // Add user message to UI
        this.addMessage('user', input);
        this.messageInput.value = '';

        // Show typing indicator
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message ai-message typing';
        typingDiv.innerHTML = '<em>GremlinsAI is typing...</em>';
        this.messagesContainer.appendChild(typingDiv);

        try {
            // Send message to GremlinsAI
            const response = await this.client.request('/api/v1/agent/chat', {
                method: 'POST',
                body: JSON.stringify({
                    input: input,
                    conversation_id: this.conversationId,
                    save_conversation: true
                })
            });

            // Remove typing indicator
            this.messagesContainer.removeChild(typingDiv);

            // Add AI response
            this.addMessage('ai', response.output);

        } catch (error) {
            // Remove typing indicator
            this.messagesContainer.removeChild(typingDiv);
            
            console.error('Failed to send message:', error);
            this.addMessage('system', 'Failed to send message. Please try again.');
        }
    }

    // Handle Enter key press
    handleKeyPress(event) {
        if (event.key === 'Enter') {
            this.sendMessage();
        }
    }
}

// Initialize chat when page loads
document.addEventListener('DOMContentLoaded', () => {
    const chat = new ChatInterface();
    
    // Add Enter key listener
    document.getElementById('messageInput').addEventListener('keypress', (e) => {
        chat.handleKeyPress(e);
    });
    
    // Make sendMessage available globally
    window.sendMessage = () => chat.sendMessage();
});
```

### Step 3: Enhanced Features

```javascript
// Add conversation history loading
class EnhancedChatInterface extends ChatInterface {
    constructor() {
        super();
        this.loadConversationHistory();
    }

    async loadConversationHistory() {
        try {
            const conversations = await this.client.request('/api/v1/history/conversations?limit=10');
            this.populateConversationList(conversations.conversations);
        } catch (error) {
            console.error('Failed to load conversation history:', error);
        }
    }

    populateConversationList(conversations) {
        // Add conversation selector to HTML
        const selector = document.createElement('select');
        selector.id = 'conversationSelector';
        selector.innerHTML = '<option value="">New Conversation</option>';
        
        conversations.forEach(conv => {
            const option = document.createElement('option');
            option.value = conv.id;
            option.textContent = conv.title;
            selector.appendChild(option);
        });

        selector.addEventListener('change', (e) => {
            if (e.target.value) {
                this.loadConversation(e.target.value);
            } else {
                this.initializeChat();
            }
        });

        document.querySelector('.chat-container').insertBefore(selector, document.getElementById('messages'));
    }

    async loadConversation(conversationId) {
        try {
            const conversation = await this.client.request(
                `/api/v1/history/conversations/${conversationId}?include_messages=true`
            );
            
            this.conversationId = conversationId;
            this.messagesContainer.innerHTML = '';
            
            conversation.messages.forEach(msg => {
                this.addMessage(msg.role, msg.content);
            });
        } catch (error) {
            console.error('Failed to load conversation:', error);
        }
    }
}
```

## Tutorial 2: Document Upload and Search Interface

### Step 1: HTML Structure for Document Management

```html
<div class="document-manager">
    <h2>Document Management</h2>
    
    <!-- Upload Section -->
    <div class="upload-section">
        <h3>Upload Document</h3>
        <input type="file" id="fileInput" accept=".txt,.pdf,.docx,.md" />
        <input type="text" id="documentTitle" placeholder="Document title (optional)" />
        <button onclick="uploadDocument()">Upload</button>
        <div id="uploadStatus"></div>
    </div>

    <!-- Search Section -->
    <div class="search-section">
        <h3>Search Documents</h3>
        <input type="text" id="searchQuery" placeholder="Enter search query..." />
        <button onclick="searchDocuments()">Search</button>
        <div id="searchResults"></div>
    </div>

    <!-- RAG Query Section -->
    <div class="rag-section">
        <h3>Ask Questions About Your Documents</h3>
        <textarea id="ragQuery" placeholder="Ask a question about your documents..."></textarea>
        <button onclick="performRAGQuery()">Ask</button>
        <div id="ragResults"></div>
    </div>

    <!-- Document List -->
    <div class="document-list">
        <h3>Your Documents</h3>
        <div id="documentsList"></div>
    </div>
</div>
```

### Step 2: Document Management Implementation

```javascript
class DocumentManager {
    constructor() {
        this.client = new GremlinsAIClient({
            baseURL: 'http://localhost:8000',
            apiKey: 'your_api_key_here'
        });
        
        this.loadDocuments();
    }

    async uploadDocument() {
        const fileInput = document.getElementById('fileInput');
        const titleInput = document.getElementById('documentTitle');
        const statusDiv = document.getElementById('uploadStatus');
        
        if (!fileInput.files[0]) {
            statusDiv.innerHTML = '<span style="color: red;">Please select a file</span>';
            return;
        }

        const file = fileInput.files[0];
        const title = titleInput.value || file.name;

        statusDiv.innerHTML = '<span style="color: blue;">Uploading...</span>';

        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('metadata', JSON.stringify({
                title: title,
                upload_date: new Date().toISOString(),
                file_type: file.type
            }));

            const response = await this.client.request('/api/v1/documents/upload', {
                method: 'POST',
                body: formData,
                headers: {} // Let browser set Content-Type for FormData
            });

            statusDiv.innerHTML = '<span style="color: green;">Upload successful!</span>';
            fileInput.value = '';
            titleInput.value = '';
            
            // Refresh document list
            this.loadDocuments();

        } catch (error) {
            console.error('Upload failed:', error);
            statusDiv.innerHTML = `<span style="color: red;">Upload failed: ${error.message}</span>`;
        }
    }

    async searchDocuments() {
        const query = document.getElementById('searchQuery').value.trim();
        const resultsDiv = document.getElementById('searchResults');
        
        if (!query) {
            resultsDiv.innerHTML = '<p>Please enter a search query</p>';
            return;
        }

        resultsDiv.innerHTML = '<p>Searching...</p>';

        try {
            const response = await this.client.request('/api/v1/documents/search', {
                method: 'POST',
                body: JSON.stringify({
                    query: query,
                    limit: 10,
                    search_type: 'chunks'
                })
            });

            this.displaySearchResults(response.results);

        } catch (error) {
            console.error('Search failed:', error);
            resultsDiv.innerHTML = `<p style="color: red;">Search failed: ${error.message}</p>`;
        }
    }

    displaySearchResults(results) {
        const resultsDiv = document.getElementById('searchResults');
        
        if (results.length === 0) {
            resultsDiv.innerHTML = '<p>No results found</p>';
            return;
        }

        const resultsHTML = results.map(result => `
            <div class="search-result" style="border: 1px solid #ddd; padding: 10px; margin: 10px 0; border-radius: 4px;">
                <h4>${result.document_title}</h4>
                <p><strong>Score:</strong> ${result.score.toFixed(3)}</p>
                <p><strong>Content:</strong> ${result.content}</p>
                <small>Document ID: ${result.document_id}</small>
            </div>
        `).join('');

        resultsDiv.innerHTML = resultsHTML;
    }

    async performRAGQuery() {
        const query = document.getElementById('ragQuery').value.trim();
        const resultsDiv = document.getElementById('ragResults');
        
        if (!query) {
            resultsDiv.innerHTML = '<p>Please enter a question</p>';
            return;
        }

        resultsDiv.innerHTML = '<p>Processing your question...</p>';

        try {
            const response = await this.client.request('/api/v1/documents/rag', {
                method: 'POST',
                body: JSON.stringify({
                    query: query,
                    use_multi_agent: true,
                    search_limit: 5
                })
            });

            resultsDiv.innerHTML = `
                <div class="rag-result" style="border: 1px solid #4CAF50; padding: 15px; border-radius: 4px; background-color: #f9f9f9;">
                    <h4>Answer:</h4>
                    <p>${response.answer}</p>
                    <h5>Sources:</h5>
                    <ul>
                        ${response.sources.map(source => `
                            <li>${source.document_title} (Score: ${source.score.toFixed(3)})</li>
                        `).join('')}
                    </ul>
                </div>
            `;

        } catch (error) {
            console.error('RAG query failed:', error);
            resultsDiv.innerHTML = `<p style="color: red;">Query failed: ${error.message}</p>`;
        }
    }

    async loadDocuments() {
        const listDiv = document.getElementById('documentsList');
        
        try {
            const response = await this.client.request('/api/v1/documents/?limit=50');
            
            if (response.documents.length === 0) {
                listDiv.innerHTML = '<p>No documents uploaded yet</p>';
                return;
            }

            const documentsHTML = response.documents.map(doc => `
                <div class="document-item" style="border: 1px solid #ddd; padding: 10px; margin: 5px 0; border-radius: 4px;">
                    <h5>${doc.title}</h5>
                    <p><strong>Type:</strong> ${doc.content_type}</p>
                    <p><strong>Size:</strong> ${(doc.file_size / 1024).toFixed(1)} KB</p>
                    <p><strong>Created:</strong> ${new Date(doc.created_at).toLocaleString()}</p>
                    <button onclick="documentManager.deleteDocument('${doc.id}')" style="background: #f44336; color: white; border: none; padding: 5px 10px; border-radius: 3px; cursor: pointer;">Delete</button>
                </div>
            `).join('');

            listDiv.innerHTML = documentsHTML;

        } catch (error) {
            console.error('Failed to load documents:', error);
            listDiv.innerHTML = '<p style="color: red;">Failed to load documents</p>';
        }
    }

    async deleteDocument(documentId) {
        if (!confirm('Are you sure you want to delete this document?')) {
            return;
        }

        try {
            await this.client.request(`/api/v1/documents/${documentId}`, {
                method: 'DELETE'
            });
            
            // Refresh document list
            this.loadDocuments();

        } catch (error) {
            console.error('Failed to delete document:', error);
            alert('Failed to delete document');
        }
    }
}

// Initialize document manager
let documentManager;
document.addEventListener('DOMContentLoaded', () => {
    documentManager = new DocumentManager();
    
    // Make functions available globally
    window.uploadDocument = () => documentManager.uploadDocument();
    window.searchDocuments = () => documentManager.searchDocuments();
    window.performRAGQuery = () => documentManager.performRAGQuery();
});
```
