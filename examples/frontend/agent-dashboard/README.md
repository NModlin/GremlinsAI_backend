# GremlinsAI Agent Dashboard Example

A comprehensive dashboard interface for managing and invoking different AI agents, built with Vue.js 3 and TypeScript. This example demonstrates advanced features like multi-agent workflows, agent performance monitoring, and batch operations.

## Features

- 🤖 **Multi-Agent Management**: Invoke different AI agents for specialized tasks
- 📊 **Performance Dashboard**: Monitor agent response times and success rates
- 🔄 **Workflow Automation**: Execute complex multi-agent workflows
- 📈 **Analytics & Insights**: Track usage patterns and agent effectiveness
- 🎛️ **Agent Configuration**: Customize agent parameters and behaviors
- 📱 **Responsive Design**: Works seamlessly on desktop and mobile
- 🔒 **Secure Integration**: Full authentication and error handling
- ⚡ **Real-time Updates**: Live status updates and notifications

## Screenshots

![Agent Dashboard](./screenshots/dashboard.png)
![Multi-Agent Workflow](./screenshots/workflow.png)
![Analytics View](./screenshots/analytics.png)

## Quick Start

### Prerequisites

- Node.js 16+ and npm/yarn
- GremlinsAI backend running on `http://localhost:8000`
- API key for authentication

### Installation

1. Navigate to the agent-dashboard directory:
```bash
cd examples/frontend/agent-dashboard
npm install
```

2. Set up environment variables:
```bash
cp .env.example .env.local
```

3. Edit `.env.local` with your configuration:
```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_WS_BASE_URL=ws://localhost:8000/api/v1/ws
VITE_API_KEY=your_api_key_here
```

4. Start the development server:
```bash
npm run dev
```

5. Open [http://localhost:5173](http://localhost:5173) in your browser

## Project Structure

```
agent-dashboard/
├── public/
│   ├── index.html
│   └── favicon.ico
├── src/
│   ├── components/
│   │   ├── AgentCard/
│   │   ├── WorkflowBuilder/
│   │   ├── PerformanceChart/
│   │   ├── AgentInvoker/
│   │   └── Dashboard/
│   ├── composables/
│   │   ├── useAgents.ts
│   │   ├── useWorkflows.ts
│   │   ├── useAnalytics.ts
│   │   └── useGremlinsAPI.ts
│   ├── services/
│   │   ├── api.ts
│   │   ├── websocket.ts
│   │   └── types.ts
│   ├── stores/
│   │   ├── agents.ts
│   │   ├── workflows.ts
│   │   └── analytics.ts
│   ├── views/
│   │   ├── Dashboard.vue
│   │   ├── Agents.vue
│   │   ├── Workflows.vue
│   │   └── Analytics.vue
│   ├── router/
│   │   └── index.ts
│   ├── styles/
│   │   ├── main.css
│   │   └── variables.css
│   ├── App.vue
│   └── main.ts
├── package.json
├── vite.config.ts
├── tsconfig.json
└── README.md
```

## Key Features

### Agent Management
- **Agent Discovery**: Automatically detect available AI agents
- **Agent Profiles**: View capabilities, performance metrics, and usage statistics
- **Custom Parameters**: Configure agent-specific parameters and settings
- **Health Monitoring**: Real-time status monitoring for all agents

### Multi-Agent Workflows
- **Workflow Builder**: Visual interface for creating complex agent workflows
- **Predefined Templates**: Ready-to-use workflow templates for common tasks
- **Conditional Logic**: Support for branching and conditional execution
- **Progress Tracking**: Real-time workflow execution monitoring

### Performance Analytics
- **Response Time Metrics**: Track and analyze agent response times
- **Success Rate Monitoring**: Monitor agent reliability and error rates
- **Usage Analytics**: Understand which agents are most effective
- **Cost Tracking**: Monitor API usage and associated costs

### Advanced Features
- **Batch Operations**: Execute multiple agent requests simultaneously
- **Request Queuing**: Intelligent request queuing and rate limiting
- **Result Caching**: Cache frequently requested results for better performance
- **Export Capabilities**: Export results and analytics data

## API Integration

### Agent Invocation
```typescript
import { useAgents } from '@/composables/useAgents';

const { invokeAgent, agents, isLoading } = useAgents();

// Invoke a specific agent
const result = await invokeAgent('research-agent', {
  input: 'Research the latest AI trends',
  parameters: {
    depth: 'comprehensive',
    sources: ['academic', 'industry']
  }
});
```

### Multi-Agent Workflows
```typescript
import { useWorkflows } from '@/composables/useWorkflows';

const { executeWorkflow, workflows } = useWorkflows();

// Execute a multi-agent workflow
const workflowResult = await executeWorkflow('research-analyze-write', {
  input: 'Create a report on renewable energy',
  agents: {
    researcher: { depth: 'comprehensive' },
    analyzer: { focus: 'trends' },
    writer: { style: 'professional' }
  }
});
```

### Real-time Monitoring
```typescript
import { useWebSocket } from '@/composables/useWebSocket';

const { connect, subscribe, connectionStatus } = useWebSocket();

// Subscribe to agent status updates
subscribe('agent-status', (data) => {
  console.log('Agent status update:', data);
});

// Subscribe to workflow progress
subscribe('workflow-progress', (data) => {
  updateWorkflowProgress(data);
});
```

## Customization

### Adding Custom Agents
```typescript
// src/config/agents.ts
export const customAgents = [
  {
    id: 'custom-agent',
    name: 'Custom Agent',
    description: 'A specialized agent for custom tasks',
    capabilities: ['analysis', 'generation'],
    parameters: {
      temperature: { type: 'number', default: 0.7, min: 0, max: 1 },
      maxTokens: { type: 'number', default: 1000, min: 100, max: 4000 }
    }
  }
];
```

### Custom Workflow Templates
```typescript
// src/config/workflows.ts
export const workflowTemplates = [
  {
    id: 'custom-workflow',
    name: 'Custom Research Workflow',
    description: 'A custom workflow for specialized research tasks',
    steps: [
      { agent: 'research-agent', action: 'gather-data' },
      { agent: 'analysis-agent', action: 'analyze-data' },
      { agent: 'summary-agent', action: 'create-summary' }
    ]
  }
];
```

### Theming
```css
/* src/styles/variables.css */
:root {
  --primary-color: #007bff;
  --secondary-color: #6c757d;
  --success-color: #28a745;
  --danger-color: #dc3545;
  --warning-color: #ffc107;
  
  --dashboard-bg: #f8f9fa;
  --card-bg: #ffffff;
  --text-primary: #212529;
  --text-secondary: #6c757d;
  
  --border-radius: 8px;
  --box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  --transition: all 0.3s ease;
}
```

## Performance Optimization

### Lazy Loading
```typescript
// Router with lazy-loaded components
const routes = [
  {
    path: '/dashboard',
    component: () => import('@/views/Dashboard.vue')
  },
  {
    path: '/agents',
    component: () => import('@/views/Agents.vue')
  }
];
```

### Virtual Scrolling
```vue
<template>
  <VirtualList
    :items="agents"
    :item-height="120"
    :container-height="600"
  >
    <template #default="{ item }">
      <AgentCard :agent="item" />
    </template>
  </VirtualList>
</template>
```

### Caching Strategy
```typescript
// src/services/cache.ts
export class CacheService {
  private cache = new Map();
  
  set(key: string, data: any, ttl = 300000) {
    this.cache.set(key, {
      data,
      timestamp: Date.now(),
      ttl
    });
  }
  
  get(key: string) {
    const item = this.cache.get(key);
    if (!item) return null;
    
    if (Date.now() - item.timestamp > item.ttl) {
      this.cache.delete(key);
      return null;
    }
    
    return item.data;
  }
}
```

## Testing

### Unit Tests
```bash
npm run test:unit
```

### E2E Tests
```bash
npm run test:e2e
```

### Component Testing
```bash
npm run test:component
```

## Deployment

### Build for Production
```bash
npm run build
```

### Deploy to Netlify
```bash
npm install -g netlify-cli
netlify deploy --prod --dir=dist
```

### Deploy to Vercel
```bash
npm install -g vercel
vercel --prod
```

## Advanced Usage

### Custom Agent Integration
```typescript
// Register a custom agent
import { registerAgent } from '@/services/agentRegistry';

registerAgent({
  id: 'my-custom-agent',
  name: 'My Custom Agent',
  endpoint: '/api/v1/agents/custom',
  capabilities: ['text-generation', 'analysis'],
  defaultParameters: {
    temperature: 0.7,
    maxTokens: 1000
  }
});
```

### Workflow Automation
```typescript
// Create automated workflows
import { createWorkflow } from '@/services/workflowEngine';

const automatedWorkflow = createWorkflow({
  name: 'Daily Report Generation',
  schedule: '0 9 * * *', // Daily at 9 AM
  steps: [
    { agent: 'data-collector', input: 'yesterday' },
    { agent: 'analyzer', input: '${previous.output}' },
    { agent: 'report-generator', input: '${previous.output}' }
  ],
  notifications: {
    onComplete: ['admin@company.com'],
    onError: ['dev-team@company.com']
  }
});
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
