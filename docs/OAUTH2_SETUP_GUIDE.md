# GremlinsAI OAuth2 Setup Guide

## 🔐 Quick Setup for Google OAuth2 Authentication

### 1. **Google Cloud Console Setup**

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing project
3. Enable the **Google+ API** and **OAuth2 API**
4. Go to **Credentials** → **Create Credentials** → **OAuth 2.0 Client IDs**
5. Configure OAuth consent screen:
   - Application name: "GremlinsAI"
   - Authorized domains: `localhost` (for development)
   - Scopes: `email`, `profile`, `openid`
6. Create OAuth 2.0 Client ID:
   - Application type: **Web application**
   - Authorized redirect URIs: `http://localhost:3000/auth/callback`

### 2. **Environment Configuration**

Copy the credentials to your `.env` file:

```bash
# OAuth2 Configuration
GOOGLE_CLIENT_ID="your-client-id.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET="your-client-secret"
JWT_SECRET_KEY="your-super-secret-jwt-key-change-this-in-production"
JWT_ALGORITHM="HS256"
JWT_EXPIRATION_HOURS="24"
```

### 3. **Database Migration**

Run the OAuth2 migration:

```bash
# Apply the OAuth2 user model migration
alembic upgrade head
```

### 4. **Start the Backend**

```bash
# Install dependencies (if not already done)
pip install PyJWT httpx cryptography

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. **Test OAuth2 Endpoints**

```bash
# Test OAuth2 configuration
curl http://localhost:8000/api/v1/auth/config

# Should return:
{
  "google_client_id": "your-client-id.apps.googleusercontent.com",
  "redirect_uri": "http://localhost:3000/auth/callback",
  "scopes": ["openid", "email", "profile"]
}
```

## 🌐 Frontend Integration Examples

### **React/Next.js Example**

```jsx
// components/LoginButton.jsx
import { useState } from 'react';

export default function LoginButton() {
  const [user, setUser] = useState(null);

  const handleLogin = async () => {
    // Get OAuth2 config
    const config = await fetch('/api/v1/auth/config').then(r => r.json());
    
    // Redirect to Google OAuth2
    const params = new URLSearchParams({
      client_id: config.google_client_id,
      redirect_uri: config.redirect_uri,
      response_type: 'code',
      scope: config.scopes.join(' '),
      access_type: 'offline'
    });
    
    window.location.href = `https://accounts.google.com/o/oauth2/v2/auth?${params}`;
  };

  const handleCallback = async (code) => {
    try {
      // Exchange Google code for GremlinsAI token
      const response = await fetch('/api/v1/auth/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ google_token: code })
      });
      
      const data = await response.json();
      localStorage.setItem('gremlins_token', data.access_token);
      setUser(data.user);
    } catch (error) {
      console.error('Login failed:', error);
    }
  };

  return (
    <div>
      {user ? (
        <div>Welcome, {user.name}!</div>
      ) : (
        <button onClick={handleLogin}>Login with Google</button>
      )}
    </div>
  );
}
```

### **Vue.js Example**

```vue
<!-- components/LoginComponent.vue -->
<template>
  <div>
    <button v-if="!user" @click="login">Login with Google</button>
    <div v-else>Welcome, {{ user.name }}!</div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      user: null
    };
  },
  methods: {
    async login() {
      const config = await fetch('/api/v1/auth/config').then(r => r.json());
      
      const params = new URLSearchParams({
        client_id: config.google_client_id,
        redirect_uri: config.redirect_uri,
        response_type: 'code',
        scope: config.scopes.join(' ')
      });
      
      window.location.href = `https://accounts.google.com/o/oauth2/v2/auth?${params}`;
    }
  }
};
</script>
```

### **API Client with Authentication**

```javascript
// utils/apiClient.js
class GremlinsAPIClient {
  constructor() {
    this.baseURL = 'http://localhost:8000/api/v1';
    this.token = localStorage.getItem('gremlins_token');
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    };

    // Add authentication header
    if (this.token) {
      config.headers.Authorization = `Bearer ${this.token}`;
    }

    const response = await fetch(url, config);
    
    if (response.status === 401) {
      // Token expired, redirect to login
      localStorage.removeItem('gremlins_token');
      window.location.href = '/login';
      return;
    }

    return response.json();
  }

  // Document upload with authentication
  async uploadDocument(file, metadata = {}) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('metadata', JSON.stringify(metadata));

    return this.request('/documents/upload', {
      method: 'POST',
      body: formData,
      headers: {} // Don't set Content-Type for FormData
    });
  }

  // Get user info
  async getCurrentUser() {
    return this.request('/auth/me');
  }
}

export default new GremlinsAPIClient();
```

## 🔧 Development Tips

### **Testing Authentication**

```bash
# Get a test token (after setting up OAuth2)
# 1. Go to http://localhost:8000/docs
# 2. Use the /auth/token endpoint with a Google ID token
# 3. Copy the returned access_token

# Test authenticated endpoints
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     http://localhost:8000/api/v1/auth/me

# Test document upload
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -F "file=@test.txt" \
     http://localhost:8000/api/v1/documents/upload
```

### **Common Issues**

1. **"OAuth2 not configured"** - Check `GOOGLE_CLIENT_ID` in `.env`
2. **"Invalid token"** - Verify Google OAuth2 setup and client ID
3. **"Authentication required"** - All endpoints now require OAuth2 tokens
4. **CORS issues** - Add your frontend domain to CORS settings

### **Production Deployment**

1. **Update redirect URIs** in Google Cloud Console
2. **Use HTTPS** for production OAuth2 flows
3. **Set secure JWT_SECRET_KEY** (not the example one)
4. **Configure proper CORS** for your frontend domain
5. **Use environment variables** for all sensitive configuration

## ✅ **You're Ready!**

Your GremlinsAI backend now has production-ready OAuth2 authentication. Users must authenticate with Google to access any functionality, ensuring proper security and user isolation.
