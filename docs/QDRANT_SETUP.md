# Qdrant Vector Database Setup for GremlinsAI

Qdrant is an optional but powerful addition to GremlinsAI that provides enhanced semantic search and RAG (Retrieval-Augmented Generation) capabilities.

## Overview

**Without Qdrant**: GremlinsAI works perfectly fine with basic document search and LLM responses.

**With Qdrant**: You get enhanced capabilities:
- Semantic document search
- Better context retrieval for RAG
- Document similarity matching
- Vector-based knowledge base

## Quick Setup (Recommended)

### Option 1: Automated Setup Script

```bash
# Run the setup script
python scripts/setup_qdrant.py
```

This script will:
1. Check if Docker is installed and running
2. Start Qdrant container automatically
3. Test the connection
4. Provide usage instructions

### Option 2: Manual Docker Setup

```bash
# Start Qdrant using Docker
docker run -d \
  --name qdrant \
  -p 6333:6333 \
  -p 6334:6334 \
  -v qdrant_storage:/qdrant/storage \
  qdrant/qdrant:latest

# Verify it's running
docker ps | grep qdrant
```

## Prerequisites

1. **Docker Desktop** installed and running
   - Download from: https://www.docker.com/products/docker-desktop/
   - Make sure Docker daemon is running

2. **Python dependencies** (already included in requirements.txt):
   - `qdrant-client>=1.7.0`
   - `sentence-transformers>=2.2.0`

## Configuration

Your `.env` file is already configured with the correct Qdrant settings:

```env
# Qdrant Configuration
QDRANT_HOST="localhost"
QDRANT_PORT="6333"
QDRANT_COLLECTION="gremlins_documents"
EMBEDDING_MODEL="all-MiniLM-L6-v2"
```

## Verification

### 1. Check Qdrant Status

```bash
# Check if container is running
docker ps | grep qdrant

# Check Qdrant health
curl http://localhost:6333/health
```

### 2. Access Qdrant Web UI

Open in your browser: http://localhost:6333/dashboard

### 3. Test with GremlinsAI

1. Restart your GremlinsAI backend
2. Check the logs for: "Connected to Qdrant at localhost:6333"
3. Upload a document via the API
4. Try semantic search queries

## Usage Examples

### Upload Documents for Semantic Search

```bash
# Upload a document
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your-document.pdf"
```

### Semantic Search Query

```bash
# Search documents semantically
curl -X POST "http://localhost:8000/api/v1/documents/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "machine learning algorithms",
    "limit": 5,
    "score_threshold": 0.1
  }'
```

### RAG-Enhanced Chat

```bash
# Chat with document context
curl -X POST "http://localhost:8000/api/v1/agent/invoke" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Explain the key concepts from the uploaded documents",
    "use_rag": true
  }'
```

## Management Commands

### Start/Stop Qdrant

```bash
# Start Qdrant
docker start qdrant

# Stop Qdrant
docker stop qdrant

# Restart Qdrant
docker restart qdrant
```

### View Logs

```bash
# View Qdrant logs
docker logs qdrant

# Follow logs in real-time
docker logs -f qdrant
```

### Backup and Restore

```bash
# Backup Qdrant data
docker run --rm -v qdrant_storage:/data -v $(pwd):/backup alpine tar czf /backup/qdrant-backup.tar.gz -C /data .

# Restore Qdrant data
docker run --rm -v qdrant_storage:/data -v $(pwd):/backup alpine tar xzf /backup/qdrant-backup.tar.gz -C /data
```

## Troubleshooting

### Common Issues

1. **"Docker daemon not running"**
   - Start Docker Desktop
   - Wait for it to fully initialize

2. **"Port 6333 already in use"**
   - Check if Qdrant is already running: `docker ps`
   - Stop existing container: `docker stop qdrant`

3. **"Connection refused"**
   - Wait a few seconds for Qdrant to start
   - Check container status: `docker ps`
   - Check logs: `docker logs qdrant`

4. **"Collection not found"**
   - GremlinsAI automatically creates collections
   - Restart the backend to trigger collection creation

### Reset Qdrant

```bash
# Complete reset (removes all data)
docker stop qdrant
docker rm qdrant
docker volume rm qdrant_storage

# Then run setup again
python scripts/setup_qdrant.py
```

## Performance Tips

1. **Memory**: Qdrant uses ~200MB RAM by default
2. **Storage**: Vector data is stored in Docker volume `qdrant_storage`
3. **Embedding Model**: `all-MiniLM-L6-v2` is fast and efficient for most use cases

## Without Qdrant

If you prefer not to use Qdrant, GremlinsAI will automatically:
- Use basic text search for documents
- Fall back to simple LLM responses
- Log info messages (not warnings) about Qdrant being unavailable

The system is designed to work seamlessly with or without Qdrant.
