# GremlinsAI Frontend Examples

This directory contains comprehensive frontend implementation examples that demonstrate how to build user interfaces for the GremlinsAI backend system. Each example is production-ready and showcases different aspects of the GremlinsAI platform.

## 📁 Available Examples

### 1. [Chat UI](./chat-ui/) - React + TypeScript
**Simple, responsive chat interface for AI conversations**

- ✅ **Beginner-friendly** - Perfect starting point for new developers
- 🎯 **Core Features**: Real-time chat, conversation history, responsive design
- 🛠️ **Tech Stack**: React 18, TypeScript, CSS Modules
- 📱 **Mobile-first** design with accessibility support
- ⚡ **Quick Setup**: Get running in under 5 minutes

**Best for**: Simple chat applications, learning the basics, rapid prototyping

### 2. [Agent Dashboard](./agent-dashboard/) - Vue.js + TypeScript  
**Advanced agent management and workflow automation**

- 🚀 **Intermediate level** - Demonstrates advanced patterns
- 🎯 **Core Features**: Multi-agent management, workflow builder, performance analytics
- 🛠️ **Tech Stack**: Vue.js 3, TypeScript, Pinia, Vite
- 📊 **Rich UI**: Charts, dashboards, drag-and-drop interfaces
- 🔄 **Automation**: Workflow templates and scheduling

**Best for**: Agent management systems, workflow automation, business applications

### 3. [Full System](./full-system/) - Next.js + TypeScript
**Enterprise-grade complete system implementation**

- 🏢 **Advanced level** - Production-ready enterprise solution
- 🎯 **Core Features**: Everything from chat to analytics, multi-tenant, SSO
- 🛠️ **Tech Stack**: Next.js 13+, TypeScript, Tailwind CSS, Prisma
- 🔐 **Enterprise**: Authentication, RBAC, audit logging, compliance
- 📈 **Scalable**: Microservices-ready, Docker, Kubernetes support

**Best for**: Enterprise applications, SaaS platforms, complex integrations

## 🚀 Quick Start Guide

### Prerequisites
- Node.js 16+ and npm/yarn/pnpm
- GremlinsAI backend running on `http://localhost:8000`
- API key for authentication

### Choose Your Path

#### 🎯 **New to GremlinsAI?** → Start with [Chat UI](./chat-ui/)
```bash
cd examples/frontend/chat-ui
npm install
cp .env.example .env.local
# Edit .env.local with your API key
npm start
```

#### 🔧 **Building Agent Tools?** → Try [Agent Dashboard](./agent-dashboard/)
```bash
cd examples/frontend/agent-dashboard
npm install
cp .env.example .env.local
# Edit .env.local with your configuration
npm run dev
```

#### 🏢 **Enterprise Solution?** → Explore [Full System](./full-system/)
```bash
cd examples/frontend/full-system
npm install
cp .env.example .env.local
# Configure all environment variables
npm run dev
```

## 🛠️ Technology Stack Comparison

| Feature | Chat UI | Agent Dashboard | Full System |
|---------|---------|-----------------|-------------|
| **Framework** | React 18 | Vue.js 3 | Next.js 13+ |
| **Language** | TypeScript | TypeScript | TypeScript |
| **Styling** | CSS Modules | CSS + SCSS | Tailwind CSS |
| **State Management** | React Hooks | Pinia | Zustand |
| **Build Tool** | Create React App | Vite | Next.js |
| **Testing** | Jest + RTL | Vitest + VTU | Jest + Playwright |
| **Complexity** | Simple | Moderate | Advanced |
| **Setup Time** | 5 minutes | 15 minutes | 30 minutes |

## 📋 Feature Matrix

| Feature | Chat UI | Agent Dashboard | Full System |
|---------|:-------:|:---------------:|:-----------:|
| **Basic Chat** | ✅ | ✅ | ✅ |
| **Conversation History** | ✅ | ✅ | ✅ |
| **Real-time Updates** | ✅ | ✅ | ✅ |
| **Multi-Agent Support** | ❌ | ✅ | ✅ |
| **Workflow Builder** | ❌ | ✅ | ✅ |
| **Analytics Dashboard** | ❌ | ✅ | ✅ |
| **User Management** | ❌ | ❌ | ✅ |
| **Authentication** | Basic | Basic | Enterprise |
| **File Upload** | ❌ | ❌ | ✅ |
| **Voice Input** | ❌ | ❌ | ✅ |
| **Mobile App** | Responsive | Responsive | PWA |
| **Offline Support** | ❌ | ❌ | ✅ |
| **Multi-tenant** | ❌ | ❌ | ✅ |

## 🎨 UI/UX Patterns

### Design Systems
- **Chat UI**: Clean, minimal design focused on readability
- **Agent Dashboard**: Professional dashboard with data visualization
- **Full System**: Modern enterprise UI with comprehensive design system

### Accessibility
All examples follow WCAG 2.1 guidelines:
- ♿ Keyboard navigation support
- 🔍 Screen reader compatibility
- 🎨 High contrast mode support
- 📱 Responsive design for all devices

### Theming
- 🌙 Dark/light mode support
- 🎨 Customizable color schemes
- 📐 Consistent spacing and typography
- 🔧 CSS custom properties for easy customization

## 🔧 Development Workflow

### Local Development
```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Run tests
npm test

# Build for production
npm run build
```

### Environment Configuration
Each example includes:
- `.env.example` - Template with all required variables
- Environment-specific configurations
- Feature flags for optional functionality
- Development vs production settings

### Code Quality
- **ESLint** - Code linting and formatting
- **Prettier** - Code formatting
- **TypeScript** - Type safety
- **Husky** - Git hooks for quality checks

## 📚 Learning Path

### 1. **Start Simple** (Chat UI)
- Learn basic GremlinsAI integration
- Understand API patterns
- Master React/TypeScript basics
- Implement real-time features

### 2. **Add Complexity** (Agent Dashboard)
- Multi-agent orchestration
- Advanced state management
- Data visualization
- Workflow automation

### 3. **Go Enterprise** (Full System)
- Authentication and authorization
- Multi-tenant architecture
- Performance optimization
- Production deployment

## 🔗 Integration Patterns

### API Integration
```typescript
// Consistent API client across all examples
import { GremlinsAPIClient } from '@/services/api';

const apiClient = new GremlinsAPIClient(
  process.env.REACT_APP_API_BASE_URL,
  process.env.REACT_APP_API_KEY
);

// Usage
const response = await apiClient.chat({
  input: 'Hello, AI!',
  conversation_id: conversationId,
  save_conversation: true
});
```

### WebSocket Integration
```typescript
// Real-time updates across all examples
import { useWebSocket } from '@/hooks/useWebSocket';

const { connectionStatus, lastMessage, sendMessage } = useWebSocket(
  process.env.REACT_APP_WS_BASE_URL,
  {
    onMessage: handleIncomingMessage,
    onError: handleWebSocketError,
  }
);
```

### Error Handling
```typescript
// Consistent error handling patterns
import { ErrorHandler } from '@/utils/errorHandler';

try {
  const result = await apiCall();
  return result;
} catch (error) {
  const userMessage = ErrorHandler.getDisplayMessage(error);
  showNotification(userMessage, 'error');
  throw error;
}
```

## 🚀 Deployment Options

### Development
- Local development servers
- Hot module replacement
- Development debugging tools

### Staging
- Docker containers
- Environment-specific configurations
- CI/CD pipeline integration

### Production
- Static site generation (where applicable)
- CDN deployment
- Performance monitoring
- Error tracking

## 📖 Documentation

Each example includes:
- **README.md** - Setup and usage instructions
- **API Documentation** - Integration examples
- **Component Documentation** - Storybook (where applicable)
- **Deployment Guide** - Production deployment instructions

## 🤝 Contributing

We welcome contributions to improve these examples:

1. **Bug Reports** - Found an issue? Let us know!
2. **Feature Requests** - Have an idea? We'd love to hear it!
3. **Code Contributions** - Submit a PR with improvements
4. **Documentation** - Help improve our guides and examples

### Contribution Guidelines
- Follow existing code style and patterns
- Add tests for new features
- Update documentation as needed
- Ensure accessibility compliance

## 📞 Support

- 📖 [Complete Documentation](../../docs/frontend_integration_guide.md)
- 🐛 [Report Issues](https://github.com/your-org/gremlinsai/issues)
- 💬 [Community Discord](https://discord.gg/gremlinsai)
- 📧 [Email Support](mailto:support@gremlinsai.com)

## 📄 License

All examples are provided under the MIT License. See individual LICENSE files for details.

---

**Ready to build amazing AI-powered interfaces?** Choose your example and start coding! 🚀
