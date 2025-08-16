# GremlinsAI Chat Interface Example

A simple, responsive chat interface built with React that demonstrates how to integrate with the GremlinsAI backend for real-time AI conversations.

## Features

- 💬 Real-time chat with AI agents
- 📱 Responsive design for mobile and desktop
- 🔄 Conversation history management
- ⚡ Optimistic UI updates
- 🎨 Modern, accessible design
- 🔒 Secure API integration
- 📝 TypeScript support

## Screenshots

![Chat Interface](./screenshots/chat-interface.png)
![Mobile View](./screenshots/mobile-view.png)

## Quick Start

### Prerequisites

- Node.js 16+ and npm/yarn
- GremlinsAI backend running on `http://localhost:8000`
- API key for authentication

### Installation

1. Clone and navigate to the chat-ui directory:
```bash
cd examples/frontend/chat-ui
npm install
```

2. Set up environment variables:
```bash
cp .env.example .env.local
```

3. Edit `.env.local` with your configuration:
```env
REACT_APP_API_BASE_URL=http://localhost:8000/api/v1
REACT_APP_WS_BASE_URL=ws://localhost:8000/api/v1/ws
REACT_APP_API_KEY=your_api_key_here
```

4. Start the development server:
```bash
npm start
```

5. Open [http://localhost:3000](http://localhost:3000) in your browser

## Project Structure

```
chat-ui/
├── public/
│   ├── index.html
│   └── favicon.ico
├── src/
│   ├── components/
│   │   ├── ChatInterface/
│   │   │   ├── ChatInterface.tsx
│   │   │   ├── ChatInterface.module.css
│   │   │   └── index.ts
│   │   ├── MessageList/
│   │   │   ├── MessageList.tsx
│   │   │   ├── MessageList.module.css
│   │   │   └── index.ts
│   │   ├── MessageInput/
│   │   │   ├── MessageInput.tsx
│   │   │   ├── MessageInput.module.css
│   │   │   └── index.ts
│   │   ├── ConversationSidebar/
│   │   │   ├── ConversationSidebar.tsx
│   │   │   ├── ConversationSidebar.module.css
│   │   │   └── index.ts
│   │   └── LoadingSpinner/
│   │       ├── LoadingSpinner.tsx
│   │       ├── LoadingSpinner.module.css
│   │       └── index.ts
│   ├── hooks/
│   │   ├── useGremlinsAPI.ts
│   │   ├── useWebSocket.ts
│   │   ├── useConversations.ts
│   │   └── useOptimisticMessages.ts
│   ├── services/
│   │   ├── api.ts
│   │   ├── websocket.ts
│   │   └── types.ts
│   ├── utils/
│   │   ├── formatters.ts
│   │   ├── constants.ts
│   │   └── helpers.ts
│   ├── styles/
│   │   ├── globals.css
│   │   ├── variables.css
│   │   └── components.css
│   ├── App.tsx
│   ├── App.css
│   ├── index.tsx
│   └── index.css
├── package.json
├── tsconfig.json
├── .env.example
└── README.md
```

## Key Components

### ChatInterface
The main component that orchestrates the entire chat experience:
- Manages conversation state
- Handles message sending and receiving
- Coordinates with other components

### MessageList
Displays the conversation history:
- Virtual scrolling for performance
- Message formatting and styling
- Loading states and error handling

### MessageInput
Input component for sending messages:
- Auto-resize textarea
- Send button with loading states
- Keyboard shortcuts (Enter to send, Shift+Enter for new line)

### ConversationSidebar
Sidebar for managing conversations:
- List of recent conversations
- Create new conversation
- Switch between conversations

## API Integration

### Basic Usage

```typescript
import { useGremlinsAPI } from './hooks/useGremlinsAPI';

function ChatComponent() {
  const { sendMessage, conversations, currentConversation, messages, isLoading } = useGremlinsAPI();

  const handleSendMessage = async (input: string) => {
    try {
      await sendMessage(input, currentConversation?.id);
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  };

  return (
    <div>
      <MessageList messages={messages} isLoading={isLoading} />
      <MessageInput onSendMessage={handleSendMessage} disabled={isLoading} />
    </div>
  );
}
```

### WebSocket Integration

```typescript
import { useWebSocket } from './hooks/useWebSocket';

function useRealTimeChat() {
  const { sendMessage, lastMessage, connectionStatus } = useWebSocket(
    process.env.REACT_APP_WS_BASE_URL!,
    {
      onMessage: (message) => {
        // Handle incoming messages
        console.log('Received:', message);
      },
      onError: (error) => {
        console.error('WebSocket error:', error);
      },
    }
  );

  return { sendMessage, lastMessage, connectionStatus };
}
```

## Customization

### Theming

The interface uses CSS custom properties for easy theming:

```css
:root {
  --primary-color: #007bff;
  --secondary-color: #6c757d;
  --success-color: #28a745;
  --danger-color: #dc3545;
  --warning-color: #ffc107;
  --info-color: #17a2b8;
  
  --background-color: #ffffff;
  --surface-color: #f8f9fa;
  --text-color: #212529;
  --text-muted: #6c757d;
  
  --border-radius: 8px;
  --box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  --transition: all 0.2s ease-in-out;
}
```

### Adding Custom Message Types

```typescript
interface CustomMessage extends MessageResponse {
  messageType?: 'text' | 'image' | 'file' | 'code';
  metadata?: {
    language?: string;
    fileName?: string;
    fileSize?: number;
  };
}

function MessageRenderer({ message }: { message: CustomMessage }) {
  switch (message.messageType) {
    case 'code':
      return <CodeBlock code={message.content} language={message.metadata?.language} />;
    case 'image':
      return <ImageMessage src={message.content} alt="Shared image" />;
    default:
      return <TextMessage content={message.content} />;
  }
}
```

## Performance Considerations

### Virtual Scrolling
For conversations with many messages, the interface uses virtual scrolling:

```typescript
import { FixedSizeList as List } from 'react-window';

function VirtualMessageList({ messages }: { messages: MessageResponse[] }) {
  const Row = ({ index, style }: { index: number; style: React.CSSProperties }) => (
    <div style={style}>
      <MessageItem message={messages[index]} />
    </div>
  );

  return (
    <List
      height={600}
      itemCount={messages.length}
      itemSize={80}
      width="100%"
    >
      {Row}
    </List>
  );
}
```

### Optimistic Updates
Messages appear immediately while being sent to the server:

```typescript
function useOptimisticMessages() {
  const [messages, setMessages] = useState<MessageResponse[]>([]);
  const [optimisticMessages, setOptimisticMessages] = useState<MessageResponse[]>([]);

  const addOptimisticMessage = (content: string) => {
    const tempMessage: MessageResponse = {
      id: `temp_${Date.now()}`,
      content,
      role: 'user',
      created_at: new Date().toISOString(),
      conversation_id: currentConversationId,
    };
    
    setOptimisticMessages(prev => [...prev, tempMessage]);
    return tempMessage.id;
  };

  const removeOptimisticMessage = (id: string) => {
    setOptimisticMessages(prev => prev.filter(msg => msg.id !== id));
  };

  return {
    allMessages: [...messages, ...optimisticMessages],
    addOptimisticMessage,
    removeOptimisticMessage,
  };
}
```

## Accessibility

The interface follows WCAG 2.1 guidelines:

- **Keyboard Navigation**: Full keyboard support for all interactions
- **Screen Reader Support**: Proper ARIA labels and live regions
- **Focus Management**: Logical focus order and visible focus indicators
- **Color Contrast**: Meets AA contrast requirements
- **Responsive Design**: Works on all screen sizes and orientations

### Screen Reader Announcements

```typescript
function useScreenReaderAnnouncements() {
  const announce = (message: string, priority: 'polite' | 'assertive' = 'polite') => {
    const announcement = document.createElement('div');
    announcement.setAttribute('aria-live', priority);
    announcement.setAttribute('aria-atomic', 'true');
    announcement.className = 'sr-only';
    announcement.textContent = message;
    
    document.body.appendChild(announcement);
    setTimeout(() => document.body.removeChild(announcement), 1000);
  };

  return { announce };
}
```

## Testing

### Unit Tests
```bash
npm test
```

### E2E Tests
```bash
npm run test:e2e
```

### Test Coverage
```bash
npm run test:coverage
```

## Deployment

### Build for Production
```bash
npm run build
```

### Deploy to Netlify
```bash
npm install -g netlify-cli
netlify deploy --prod --dir=build
```

### Deploy to Vercel
```bash
npm install -g vercel
vercel --prod
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
