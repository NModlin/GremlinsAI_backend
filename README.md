# GremlinsAI Backend v9.0.0

A sophisticated, headless, multi-modal AI system built with FastAPI, CrewAI, and Qdrant, featuring specialized multi-agent capabilities, semantic search, and RAG (Retrieval-Augmented Generation) that can reason across text, collaborate on complex tasks, and maintain conversation context through persistent chat history and document knowledge.

**Current Version:** 9.0.0 | **Status:** ✅ Production Ready | **API Endpoints:** 103

## 🚀 Features

### Core Agent Engine
- **LangGraph-based Agent**: Advanced agent workflow with tool integration
- **DuckDuckGo Search**: Web search capabilities for real-time information
- **FastAPI Framework**: Modern, fast API with automatic documentation
- **Tool Integration**: Extensible architecture for adding new tools

### Robust API Layer
- **Chat History**: Persistent conversation storage with SQLite database
- **Context Awareness**: Multi-turn conversations with memory
- **CRUD Operations**: Complete conversation and message management
- **Database Migrations**: Alembic-powered schema management

### Advanced Multi-Agent Architecture
- **CrewAI Integration**: Sophisticated multi-agent orchestration
- **Specialized Agent Roles**: Researcher, Analyst, Writer, Coordinator
- **Complex Workflows**: Multi-step reasoning and task coordination
- **Agent Memory System**: Persistent context sharing between agents
- **Enhanced API Endpoints**: Multi-agent workflow capabilities
- **Backward Compatibility**: All existing functionality preserved

### Data Infrastructure
- **Qdrant Vector Store**: High-performance semantic search capabilities
- **Document Management**: Intelligent chunking and storage system
- **RAG System**: Retrieval-Augmented Generation for enhanced responses
- **Semantic Search**: Vector similarity search with metadata filtering
- **Document APIs**: Complete CRUD operations for knowledge management
- **Analytics & Monitoring**: Search analytics and system health monitoring

### Agent Orchestration & Scalability
- **Enhanced Orchestrator**: Central coordination system for all components
- **Asynchronous Task Execution**: Celery-based distributed task processing
- **Advanced Task Management**: 9 task types with priority and timeout handling
- **Scalable Architecture**: Horizontal scaling with multiple worker processes
- **Production Infrastructure**: Worker scripts, monitoring, and deployment tools
- **Comprehensive APIs**: Complete orchestration and task management endpoints

### API Modernization & Real-time Communication
- **GraphQL Integration**: Complete GraphQL API with queries, mutations, and subscriptions
- **Real-time Communication**: WebSocket infrastructure for live updates
- **Modern API Architecture**: Dual REST/GraphQL support with enhanced capabilities
- **Live Broadcasting**: Real-time message, task, and system event broadcasting
- **Enhanced Developer Experience**: GraphQL playground and comprehensive tooling
- **Backward Compatibility**: All existing APIs preserved and enhanced

### Multi-Modal Processing
- **Audio Processing**: Speech-to-text transcription, audio analysis, and text-to-speech conversion
- **Video Processing**: Frame extraction, video analysis, and audio transcription from video
- **Image Processing**: Computer vision analysis, object detection, and OCR capabilities
- **Multi-Modal Fusion**: Unified processing pipeline for combining multiple media types
- **Intelligent Storage**: Efficient content management with deduplication and metadata
- **Graceful Fallbacks**: System operates with partial capabilities when dependencies unavailable

### Developer Enablement & Documentation
- **Comprehensive Documentation**: Interactive API docs with live testing capabilities
- **Developer SDKs**: Full-featured Python SDK with async support and type safety
- **CLI Tools**: Rich command-line interface with interactive features and rich output
- **Interactive Documentation**: Live API testing, GraphQL playground, and WebSocket tester
- **Developer Portal**: Real-time monitoring dashboard with system metrics
- **Code Examples**: Extensive tutorials and best practices in multiple languages

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

**✅ PRODUCTION READY** - All features implemented and validated

The GremlinsAI system has completed comprehensive end-to-end testing with **100% test pass rate** (64/64 tests). The system is ready for production deployment with all implemented features working harmoniously:

- **Core Agent Engine**: LangGraph-based agent with tool integration ✅
- **Persistent Conversations**: Chat history and context management ✅
- **Multi-Agent Architecture**: CrewAI-based collaborative workflows ✅
- **Document Management**: RAG capabilities with Qdrant vector store ✅
- **Advanced Orchestration**: Celery-based scalable task processing ✅
- **Modern APIs**: REST and GraphQL with real-time WebSocket support ✅
- **Multi-Modal Processing**: Audio, video, and image processing capabilities ✅
- **Developer Tools**: Comprehensive documentation, SDKs, and CLI tools ✅

See [VERIFICATION_CLEANUP_REPORT.md](VERIFICATION_CLEANUP_REPORT.md) for the latest production setup and verification results.

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

### Simple Agent Query
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/agent/invoke" \
  -H "Content-Type: application/json" \
  -d '{"input": "What is artificial intelligence?"}'
```

### Context-Aware Chat
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

### Modern API & Real-time Communication
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

### Developer Tools & Documentation
```bash
# Interactive documentation and developer portal
# Visit: http://127.0.0.1:8000/docs (Developer Portal)
# Visit: http://127.0.0.1:8000/graphql (GraphQL Playground)

# Python SDK usage
pip install gremlins-ai  # (when published)
python -c "
import asyncio
from gremlins_ai import GremlinsAIClient

async def main():
    async with GremlinsAIClient() as client:
        response = await client.invoke_agent('Hello, AI!')
        print(response['output'])

asyncio.run(main())
"

# CLI tool usage
python cli/gremlins_cli.py agent chat "What is machine learning?"
python cli/gremlins_cli.py interactive  # Interactive chat mode
python cli/gremlins_cli.py system health  # System status

# Developer portal endpoints
curl -X GET "http://127.0.0.1:8000/developer-portal/"  # Dashboard
curl -X GET "http://127.0.0.1:8000/developer-portal/metrics"  # Metrics
curl -X GET "http://127.0.0.1:8000/docs/system-status"  # System status
```

### Multi-Modal Processing
```bash
# Multi-modal processing endpoints
# Visit: http://127.0.0.1:8000/api/v1/multimodal/capabilities (Check capabilities)

# Process audio file
curl -X POST "http://127.0.0.1:8000/api/v1/multimodal/process/audio" \
  -F "file=@audio.wav" \
  -F "transcribe=true" \
  -F "analyze=true"

# Process video file
curl -X POST "http://127.0.0.1:8000/api/v1/multimodal/process/video" \
  -F "file=@video.mp4" \
  -F "extract_frames=true" \
  -F "transcribe_audio=true" \
  -F "frame_count=15"

# Process image file
curl -X POST "http://127.0.0.1:8000/api/v1/multimodal/process/image" \
  -F "file=@image.jpg" \
  -F "detect_objects=true" \
  -F "extract_text=true" \
  -F "analyze=true"

# Multi-modal batch processing
curl -X POST "http://127.0.0.1:8000/api/v1/multimodal/process/multimodal" \
  -F "files=@audio.wav" \
  -F "files=@video.mp4" \
  -F "files=@image.jpg" \
  -F "fusion_strategy=concatenate"

# Text-to-speech conversion
curl -X POST "http://127.0.0.1:8000/api/v1/multimodal/text-to-speech" \
  -F "text=Hello, this is a test of text-to-speech conversion" \
  -F "output_format=wav"
```

### Advanced Orchestration
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

### Document Management & RAG
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

## 🔮 Future Enhancements

All core phases have been completed. Future development focuses on:

- **Advanced AI Capabilities**: Temporal AI agents for dynamic knowledge optimization
- **Enhanced Containerization**: Full Docker ecosystem with local LLM support
- **Performance Optimization**: Advanced caching and distributed processing
- **Enterprise Features**: Advanced security, monitoring, and compliance tools
- **Extended Multi-Modal**: Real-time video processing and advanced computer vision
- **AI Model Management**: Dynamic model switching and fine-tuning capabilities

See `docs/future/` directory for detailed future architecture plans.

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
