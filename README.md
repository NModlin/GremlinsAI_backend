# gremlinsAI Backend

A sophisticated, headless, multi-modal AI system built with FastAPI, CrewAI, and Qdrant, featuring specialized multi-agent capabilities, semantic search, and RAG (Retrieval-Augmented Generation) that can reason across text, collaborate on complex tasks, and maintain conversation context through persistent chat history and document knowledge.

## 🚀 Features

### Phase 1: Core Agent Engine
- **LangGraph-based Agent**: Advanced agent workflow with tool integration
- **DuckDuckGo Search**: Web search capabilities for real-time information
- **FastAPI Framework**: Modern, fast API with automatic documentation
- **Tool Integration**: Extensible architecture for adding new tools

### Phase 2: Robust API Layer
- **Chat History**: Persistent conversation storage with SQLite database
- **Context Awareness**: Multi-turn conversations with memory
- **CRUD Operations**: Complete conversation and message management
- **Database Migrations**: Alembic-powered schema management

### Phase 3: Advanced Multi-Agent Architecture
- **CrewAI Integration**: Sophisticated multi-agent orchestration
- **Specialized Agent Roles**: Researcher, Analyst, Writer, Coordinator
- **Complex Workflows**: Multi-step reasoning and task coordination
- **Agent Memory System**: Persistent context sharing between agents
- **Enhanced API Endpoints**: New multi-agent workflow capabilities
- **100% Backward Compatibility**: All existing functionality preserved

### Phase 4: Data Infrastructure Overhaul ✅ COMPLETE
- **Qdrant Vector Store**: High-performance semantic search capabilities
- **Document Management**: Intelligent chunking and storage system
- **RAG System**: Retrieval-Augmented Generation for enhanced responses
- **Semantic Search**: Vector similarity search with metadata filtering
- **Document APIs**: Complete CRUD operations for knowledge management
- **Analytics & Monitoring**: Search analytics and system health monitoring

### Phase 5: Agent Orchestration & Scalability ✅ COMPLETE
- **Enhanced Orchestrator**: Central coordination system for all components
- **Asynchronous Task Execution**: Celery-based distributed task processing
- **Advanced Task Management**: 9 task types with priority and timeout handling
- **Scalable Architecture**: Horizontal scaling with multiple worker processes
- **Production Infrastructure**: Worker scripts, monitoring, and deployment tools
- **Comprehensive APIs**: Complete orchestration and task management endpoints

### Phase 6: API Modernization & Real-time Communication ✅ COMPLETE
- **GraphQL Integration**: Complete GraphQL API with queries, mutations, and subscriptions
- **Real-time Communication**: WebSocket infrastructure for live updates
- **Modern API Architecture**: Dual REST/GraphQL support with enhanced capabilities
- **Live Broadcasting**: Real-time message, task, and system event broadcasting
- **Enhanced Developer Experience**: GraphQL playground and comprehensive tooling
- **100% Backward Compatibility**: All existing APIs preserved and enhanced

## 📋 Requirements

- Python 3.11+
- SQLite (included with Python)
- Internet connection (for DuckDuckGo search)

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd GremlinsAI_backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Initialize database**
   ```bash
   alembic upgrade head
   ```

## 🎯 Production Status

**✅ PRODUCTION READY** - All phases implemented and validated

The gremlinsAI system has completed comprehensive end-to-end testing with **100% test pass rate** (34/34 tests). The system is ready for production deployment with all six phases working harmoniously:

- **Phase 1**: Core agent engine with LangGraph ✅
- **Phase 2**: Persistent conversation management ✅
- **Phase 3**: Multi-agent architecture with CrewAI ✅
- **Phase 4**: Document management and RAG capabilities ✅
- **Phase 5**: Advanced orchestration and scalability ✅
- **Phase 6**: API modernization and real-time communication ✅

See [PHASE6_COMPLETE.md](PHASE6_COMPLETE.md) for detailed Phase 6 implementation and validation results.

## 🚀 Quick Start

### Start the Server
```bash
# Using the provided script
./start.sh

# Or directly with uvicorn
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Access API Documentation
- **Interactive Docs**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc

## 📚 API Usage

### Simple Agent Query (Phase 1)
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/agent/invoke" \
  -H "Content-Type: application/json" \
  -d '{"input": "What is artificial intelligence?"}'
```

### Context-Aware Chat (Phase 2)
```bash
# Start a conversation
curl -X POST "http://127.0.0.1:8000/api/v1/agent/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "What is machine learning?",
    "save_conversation": true
  }'

# Continue the conversation with context
curl -X POST "http://127.0.0.1:8000/api/v1/agent/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Can you explain that in simpler terms?",
    "conversation_id": "your-conversation-id",
    "save_conversation": true
  }'
```

### Modern API & Real-time Communication (Phase 6) ✅ COMPLETE
```bash
# GraphQL API - Flexible queries
curl -X POST "http://127.0.0.1:8000/graphql" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query { conversations(limit: 5) { id title messages { role content } } }"
  }'

# GraphQL Mutations with real-time updates
curl -X POST "http://127.0.0.1:8000/graphql" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mutation { create_conversation(input: {title: \"New Chat\"}) { id title } }"
  }'

# WebSocket connection for real-time updates
# Connect to: ws://127.0.0.1:8000/api/v1/ws/ws
# Send: {"type": "subscribe", "subscription_type": "conversation", "conversation_id": "123"}

# Real-time API information
curl -X GET "http://127.0.0.1:8000/api/v1/realtime/info"

# System status with real-time metrics
curl -X GET "http://127.0.0.1:8000/api/v1/realtime/system/status"
```

### Advanced Orchestration (Phase 5) ✅ COMPLETE
```bash
# Execute task through orchestrator
curl -X POST "http://127.0.0.1:8000/api/v1/orchestrator/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "rag_query",
    "payload": {
      "query": "What are the latest AI developments?",
      "search_limit": 5,
      "use_multi_agent": true
    },
    "execution_mode": "async",
    "priority": 1
  }'

# Enhanced agent chat with orchestration
curl -X POST "http://127.0.0.1:8000/api/v1/orchestrator/agent/enhanced-chat" \
  -d "input=Analyze renewable energy trends" \
  -d "use_multi_agent=true" \
  -d "use_rag=true" \
  -d "async_mode=true"

# Check task status
curl -X GET "http://127.0.0.1:8000/api/v1/orchestrator/task/{task_id}"

# System health check
curl -X POST "http://127.0.0.1:8000/api/v1/orchestrator/health-check?async_mode=false"
```

### Document Management & RAG (Phase 4) ✅ COMPLETE
```bash
# Create a document with automatic chunking
curl -X POST "http://127.0.0.1:8000/api/v1/documents/" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "AI Research Paper",
    "content": "Artificial intelligence research shows...",
    "tags": ["ai", "research"],
    "chunk_size": 1000
  }'

# Semantic search across documents
curl -X POST "http://127.0.0.1:8000/api/v1/documents/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "machine learning algorithms",
    "limit": 5,
    "search_type": "chunks"
  }'

# RAG query with document context
curl -X POST "http://127.0.0.1:8000/api/v1/documents/rag" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Explain neural networks based on available documents",
    "use_multi_agent": true,
    "search_limit": 3
  }'
```

### Multi-Agent Workflows (Phase 3)
```bash
# Execute multi-agent workflow
curl -X POST "http://127.0.0.1:8000/api/v1/multi-agent/workflow" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Analyze the impact of renewable energy on the economy",
    "workflow_type": "research_analyze_write",
    "save_conversation": true
  }'

# Get agent capabilities
curl "http://127.0.0.1:8000/api/v1/multi-agent/capabilities"

# Enhanced chat with multi-agent support
curl -X POST "http://127.0.0.1:8000/api/v1/agent/chat?use_multi_agent=true" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Explain quantum computing in simple terms",
    "save_conversation": true
  }'
```

### Chat History Management
```bash
# List conversations
curl "http://127.0.0.1:8000/api/v1/history/conversations"

# Get conversation details
curl "http://127.0.0.1:8000/api/v1/history/conversations/{conversation_id}"

# Get conversation messages
curl "http://127.0.0.1:8000/api/v1/history/conversations/{conversation_id}/messages"

# Get conversation summary with agent interactions
curl "http://127.0.0.1:8000/api/v1/multi-agent/conversations/{conversation_id}/summary"
```

## 🏗️ Architecture

```
gremlinsAI_backend/
├── app/
│   ├── api/v1/
│   │   ├── endpoints/          # API route handlers
│   │   └── schemas/            # Pydantic models
│   ├── core/
│   │   ├── agent.py           # LangGraph agent implementation
│   │   └── tools.py           # Agent tools (search, etc.)
│   ├── database/
│   │   ├── database.py        # Database configuration
│   │   └── models.py          # SQLAlchemy models
│   ├── services/
│   │   └── chat_history.py    # Business logic layer
│   └── main.py                # FastAPI application
├── alembic/                   # Database migrations
├── data/                      # SQLite database storage
└── requirements.txt           # Python dependencies
```

## 🔧 Configuration

### Environment Variables (.env)
```bash
# Core Application Settings
LOG_LEVEL="INFO"
DATABASE_URL="sqlite:///./data/gremlinsai.db"

# Future Phase Configurations
OLLAMA_BASE_URL="http://localhost:11434"
QDRANT_HOST="localhost"
QDRANT_PORT="6333"
REDIS_URL="redis://localhost:6379"
```

## 🗄️ Database Management

### Run Migrations
```bash
# Upgrade to latest schema
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "Description"

# Check current version
alembic current
```

## 🔌 API Endpoints

### Agent Endpoints
- `POST /api/v1/agent/invoke` - Simple agent invocation
- `POST /api/v1/agent/chat` - Context-aware chat with history

### Chat History Endpoints
- `POST /api/v1/history/conversations` - Create conversation
- `GET /api/v1/history/conversations` - List conversations
- `GET /api/v1/history/conversations/{id}` - Get conversation
- `PUT /api/v1/history/conversations/{id}` - Update conversation
- `DELETE /api/v1/history/conversations/{id}` - Delete conversation
- `POST /api/v1/history/messages` - Add message
- `GET /api/v1/history/conversations/{id}/messages` - Get messages
- `GET /api/v1/history/conversations/{id}/context` - Get AI context

## 🧪 Development

### Code Quality
- Follow PEP 8 style guidelines
- Use type hints throughout the codebase
- Maintain comprehensive docstrings

### Adding New Tools
1. Implement tool function in `app/core/tools.py`
2. Add tool to the agent's tool list in `app/core/agent.py`
3. Update API documentation

### Database Changes
1. Modify models in `app/database/models.py`
2. Generate migration: `alembic revision --autogenerate -m "Description"`
3. Apply migration: `alembic upgrade head`

## 🚦 Deployment

### Production Considerations
- Use a production WSGI server (e.g., Gunicorn)
- Configure proper logging levels
- Set up database backups
- Use environment-specific configuration
- Enable HTTPS in production

### Docker Deployment (Future)
```dockerfile
# Dockerfile example for future use
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 🔮 Future Phases

- **Phase 3**: Advanced Agent Architecture with CrewAI
- **Phase 4**: Data Infrastructure with Vector Stores
- **Phase 5**: Agent Orchestration & Scalability
- **Phase 6**: API Modernization with GraphQL
- **Phase 7**: Multi-Modal Revolution (Audio/Video)
- **Phase 8**: Developer Enablement & Documentation

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📞 Support

For questions and support, please open an issue in the repository or contact the development team.
