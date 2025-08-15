# GremlinsAI Complete System Example

A comprehensive, production-ready frontend application showcasing all GremlinsAI backend features. Built with Next.js 13+ (App Router), TypeScript, and Tailwind CSS, this example demonstrates enterprise-grade patterns and best practices.

## Features

### 🤖 **Complete AI Integration**
- Single-agent and multi-agent conversations
- Real-time chat with WebSocket support
- Agent performance monitoring and analytics
- Custom agent configuration and management

### 💬 **Advanced Chat System**
- Conversation history and management
- Message search and filtering
- Export conversations to various formats
- Voice input and text-to-speech output
- File upload and processing capabilities

### 🔄 **Workflow Management**
- Visual workflow builder with drag-and-drop
- Pre-built workflow templates
- Workflow scheduling and automation
- Progress tracking and result visualization
- Conditional logic and branching support

### 📊 **Analytics & Monitoring**
- Real-time performance dashboards
- Usage analytics and cost tracking
- Agent effectiveness metrics
- System health monitoring
- Custom reporting and data export

### 🔐 **Enterprise Features**
- Multi-tenant architecture support
- Role-based access control (RBAC)
- API key management
- Audit logging and compliance
- SSO integration (OAuth, SAML)

### 🎨 **Modern UI/UX**
- Responsive design for all devices
- Dark/light theme support
- Accessibility compliance (WCAG 2.1)
- Internationalization (i18n) support
- Progressive Web App (PWA) capabilities

## Screenshots

![Dashboard Overview](./screenshots/dashboard.png)
![Chat Interface](./screenshots/chat.png)
![Workflow Builder](./screenshots/workflow-builder.png)
![Analytics Dashboard](./screenshots/analytics.png)
![Mobile View](./screenshots/mobile.png)

## Quick Start

### Prerequisites

- Node.js 18+ and npm/yarn/pnpm
- GremlinsAI backend running on `http://localhost:8000`
- API key for authentication
- (Optional) Database for user management and analytics

### Installation

1. Navigate to the full-system directory:
```bash
cd examples/frontend/full-system
npm install
```

2. Set up environment variables:
```bash
cp .env.example .env.local
```

3. Configure your environment:
```env
# GremlinsAI Backend
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_BASE_URL=ws://localhost:8000/api/v1/ws
GREMLINS_API_KEY=your_api_key_here

# Database (Optional - for user management)
DATABASE_URL=postgresql://user:password@localhost:5432/gremlinsai

# Authentication (Optional - for multi-user support)
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your_nextauth_secret
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# Analytics (Optional)
GOOGLE_ANALYTICS_ID=GA_MEASUREMENT_ID
MIXPANEL_TOKEN=your_mixpanel_token

# Feature Flags
NEXT_PUBLIC_ENABLE_VOICE_INPUT=true
NEXT_PUBLIC_ENABLE_FILE_UPLOAD=true
NEXT_PUBLIC_ENABLE_WORKFLOWS=true
NEXT_PUBLIC_ENABLE_ANALYTICS=true
```

4. Run database migrations (if using database):
```bash
npm run db:migrate
```

5. Start the development server:
```bash
npm run dev
```

6. Open [http://localhost:3000](http://localhost:3000) in your browser

## Project Architecture

```
full-system/
├── app/                          # Next.js 13+ App Router
│   ├── (auth)/                   # Authentication routes
│   ├── (dashboard)/              # Main application routes
│   │   ├── chat/                 # Chat interface
│   │   ├── agents/               # Agent management
│   │   ├── workflows/            # Workflow builder
│   │   ├── analytics/            # Analytics dashboard
│   │   └── settings/             # User settings
│   ├── api/                      # API routes
│   │   ├── auth/                 # Authentication endpoints
│   │   ├── users/                # User management
│   │   └── webhooks/             # Webhook handlers
│   ├── globals.css               # Global styles
│   ├── layout.tsx                # Root layout
│   └── page.tsx                  # Home page
├── components/                   # Reusable components
│   ├── ui/                       # Base UI components
│   ├── chat/                     # Chat-specific components
│   ├── workflow/                 # Workflow components
│   ├── analytics/                # Analytics components
│   └── layout/                   # Layout components
├── lib/                          # Utility libraries
│   ├── api/                      # API client and utilities
│   ├── auth/                     # Authentication utilities
│   ├── db/                       # Database utilities
│   ├── utils/                    # General utilities
│   └── validations/              # Form validations
├── hooks/                        # Custom React hooks
├── stores/                       # State management (Zustand)
├── types/                        # TypeScript type definitions
├── public/                       # Static assets
├── prisma/                       # Database schema (if using Prisma)
├── tests/                        # Test files
├── docs/                         # Documentation
└── config files                  # Various config files
```

## Key Components

### Chat System
```typescript
// components/chat/ChatInterface.tsx
import { useChatStore } from '@/stores/chat';
import { useWebSocket } from '@/hooks/useWebSocket';

export function ChatInterface() {
  const { messages, sendMessage, isLoading } = useChatStore();
  const { connectionStatus } = useWebSocket();

  return (
    <div className="flex h-full">
      <ConversationSidebar />
      <div className="flex-1 flex flex-col">
        <MessageList messages={messages} />
        <MessageInput 
          onSend={sendMessage} 
          disabled={isLoading || connectionStatus !== 'connected'} 
        />
      </div>
    </div>
  );
}
```

### Workflow Builder
```typescript
// components/workflow/WorkflowBuilder.tsx
import { useWorkflowStore } from '@/stores/workflow';
import { DragDropContext, Droppable, Draggable } from '@hello-pangea/dnd';

export function WorkflowBuilder() {
  const { workflow, updateWorkflow, executeWorkflow } = useWorkflowStore();

  const handleDragEnd = (result: DropResult) => {
    // Handle drag and drop logic
    updateWorkflow(newWorkflow);
  };

  return (
    <DragDropContext onDragEnd={handleDragEnd}>
      <div className="grid grid-cols-12 gap-4 h-full">
        <AgentPalette className="col-span-3" />
        <WorkflowCanvas className="col-span-6" workflow={workflow} />
        <PropertiesPanel className="col-span-3" />
      </div>
    </DragDropContext>
  );
}
```

### Analytics Dashboard
```typescript
// components/analytics/AnalyticsDashboard.tsx
import { useAnalyticsStore } from '@/stores/analytics';
import { Chart } from '@/components/ui/Chart';

export function AnalyticsDashboard() {
  const { metrics, timeRange, setTimeRange } = useAnalyticsStore();

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <MetricCard title="Total Conversations" value={metrics.totalConversations} />
        <MetricCard title="Avg Response Time" value={`${metrics.avgResponseTime}ms`} />
        <MetricCard title="Success Rate" value={`${metrics.successRate}%`} />
        <MetricCard title="Active Users" value={metrics.activeUsers} />
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Chart
          title="Response Times"
          data={metrics.responseTimeData}
          type="line"
        />
        <Chart
          title="Agent Usage"
          data={metrics.agentUsageData}
          type="bar"
        />
      </div>
    </div>
  );
}
```

## State Management

### Chat Store (Zustand)
```typescript
// stores/chat.ts
import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

interface ChatState {
  conversations: Conversation[];
  currentConversation: Conversation | null;
  messages: Message[];
  isLoading: boolean;
  error: string | null;
}

interface ChatActions {
  sendMessage: (input: string) => Promise<void>;
  createConversation: (title: string) => Promise<void>;
  switchConversation: (id: string) => Promise<void>;
  loadMessages: (conversationId: string) => Promise<void>;
}

export const useChatStore = create<ChatState & ChatActions>()(
  devtools(
    persist(
      (set, get) => ({
        // State
        conversations: [],
        currentConversation: null,
        messages: [],
        isLoading: false,
        error: null,

        // Actions
        sendMessage: async (input: string) => {
          set({ isLoading: true, error: null });
          try {
            const response = await apiClient.chat({
              input,
              conversation_id: get().currentConversation?.id,
              save_conversation: true,
            });
            
            // Update messages and conversation
            await get().loadMessages(response.conversation_id);
          } catch (error) {
            set({ error: error.message, isLoading: false });
          }
        },

        createConversation: async (title: string) => {
          try {
            const conversation = await apiClient.createConversation({ title });
            set(state => ({
              conversations: [conversation, ...state.conversations],
              currentConversation: conversation,
              messages: [],
            }));
          } catch (error) {
            set({ error: error.message });
          }
        },

        // ... other actions
      }),
      {
        name: 'chat-store',
        partialize: (state) => ({
          conversations: state.conversations,
          currentConversation: state.currentConversation,
        }),
      }
    ),
    { name: 'chat-store' }
  )
);
```

## Advanced Features

### Real-time Collaboration
```typescript
// hooks/useCollaboration.ts
export function useCollaboration(workflowId: string) {
  const [collaborators, setCollaborators] = useState<User[]>([]);
  const [cursors, setCursors] = useState<CursorPosition[]>([]);

  useEffect(() => {
    const ws = new WebSocket(`${WS_BASE_URL}/collaborate/${workflowId}`);
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      switch (data.type) {
        case 'user-joined':
          setCollaborators(prev => [...prev, data.user]);
          break;
        case 'cursor-moved':
          setCursors(prev => updateCursor(prev, data.userId, data.position));
          break;
        case 'workflow-updated':
          // Handle real-time workflow updates
          break;
      }
    };

    return () => ws.close();
  }, [workflowId]);

  return { collaborators, cursors };
}
```

### Voice Integration
```typescript
// hooks/useVoiceInput.ts
export function useVoiceInput() {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');

  const startListening = useCallback(() => {
    if (!('webkitSpeechRecognition' in window)) {
      throw new Error('Speech recognition not supported');
    }

    const recognition = new webkitSpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;

    recognition.onstart = () => setIsListening(true);
    recognition.onend = () => setIsListening(false);
    
    recognition.onresult = (event) => {
      const transcript = Array.from(event.results)
        .map(result => result[0].transcript)
        .join('');
      
      setTranscript(transcript);
    };

    recognition.start();
  }, []);

  return { isListening, transcript, startListening };
}
```

### File Processing
```typescript
// components/chat/FileUpload.tsx
export function FileUpload({ onFileProcessed }: { onFileProcessed: (result: any) => void }) {
  const [isProcessing, setIsProcessing] = useState(false);

  const handleFileUpload = async (file: File) => {
    setIsProcessing(true);
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await fetch('/api/files/process', {
        method: 'POST',
        body: formData,
      });
      
      const result = await response.json();
      onFileProcessed(result);
    } catch (error) {
      console.error('File processing failed:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="border-2 border-dashed border-gray-300 rounded-lg p-6">
      <input
        type="file"
        onChange={(e) => e.target.files?.[0] && handleFileUpload(e.target.files[0])}
        accept=".pdf,.doc,.docx,.txt,.csv,.json"
        className="hidden"
        id="file-upload"
      />
      <label htmlFor="file-upload" className="cursor-pointer">
        {isProcessing ? (
          <div className="text-center">
            <Spinner />
            <p>Processing file...</p>
          </div>
        ) : (
          <div className="text-center">
            <Upload className="mx-auto h-12 w-12 text-gray-400" />
            <p>Click to upload or drag and drop</p>
            <p className="text-sm text-gray-500">PDF, DOC, TXT, CSV, JSON</p>
          </div>
        )}
      </label>
    </div>
  );
}
```

## Testing Strategy

### Unit Tests (Jest + Testing Library)
```typescript
// tests/components/ChatInterface.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ChatInterface } from '@/components/chat/ChatInterface';

describe('ChatInterface', () => {
  it('sends message when form is submitted', async () => {
    const mockSendMessage = jest.fn();
    
    render(<ChatInterface onSendMessage={mockSendMessage} />);
    
    const input = screen.getByPlaceholderText('Type your message...');
    const sendButton = screen.getByRole('button', { name: /send/i });
    
    fireEvent.change(input, { target: { value: 'Hello AI' } });
    fireEvent.click(sendButton);
    
    await waitFor(() => {
      expect(mockSendMessage).toHaveBeenCalledWith('Hello AI');
    });
  });
});
```

### E2E Tests (Playwright)
```typescript
// tests/e2e/chat-flow.spec.ts
import { test, expect } from '@playwright/test';

test('complete chat flow', async ({ page }) => {
  await page.goto('/chat');
  
  // Create new conversation
  await page.click('[data-testid="new-conversation"]');
  await page.fill('[data-testid="conversation-title"]', 'Test Chat');
  await page.click('[data-testid="create-conversation"]');
  
  // Send message
  await page.fill('[data-testid="message-input"]', 'Hello, how are you?');
  await page.click('[data-testid="send-button"]');
  
  // Wait for response
  await expect(page.locator('[data-testid="message-list"]')).toContainText('Hello, how are you?');
  await expect(page.locator('[data-testid="message-list"]')).toContainText('I\'m doing well');
});
```

## Deployment

### Docker Deployment
```dockerfile
# Dockerfile
FROM node:18-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

COPY . .
RUN npm run build

FROM node:18-alpine AS runner
WORKDIR /app

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000
CMD ["node", "server.js"]
```

### Kubernetes Deployment
```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: gremlinsai-frontend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: gremlinsai-frontend
  template:
    metadata:
      labels:
        app: gremlinsai-frontend
    spec:
      containers:
      - name: frontend
        image: gremlinsai/frontend:latest
        ports:
        - containerPort: 3000
        env:
        - name: NEXT_PUBLIC_API_BASE_URL
          value: "https://api.gremlinsai.com/api/v1"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-secret
              key: url
```

## Performance Optimization

### Bundle Analysis
```bash
npm run analyze
```

### Image Optimization
```typescript
// next.config.js
module.exports = {
  images: {
    domains: ['api.gremlinsai.com'],
    formats: ['image/webp', 'image/avif'],
  },
  experimental: {
    optimizeCss: true,
    optimizePackageImports: ['@heroicons/react'],
  },
};
```

### Caching Strategy
```typescript
// lib/cache.ts
import { unstable_cache } from 'next/cache';

export const getCachedAnalytics = unstable_cache(
  async (userId: string, timeRange: string) => {
    return await fetchAnalytics(userId, timeRange);
  },
  ['analytics'],
  {
    revalidate: 300, // 5 minutes
    tags: ['analytics'],
  }
);
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## License

This example is provided under the MIT License. See LICENSE file for details.

## Support

- 📖 [Documentation](../../../docs/frontend_integration_guide.md)
- 🐛 [Report Issues](https://github.com/your-org/gremlinsai/issues)
- 💬 [Community Discord](https://discord.gg/gremlinsai)
- 📧 [Email Support](mailto:support@gremlinsai.com)
