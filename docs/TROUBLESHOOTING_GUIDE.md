# GremlinsAI Troubleshooting Guide v10.0.0

## Table of Contents

1. [Common Installation Issues](#common-installation-issues)
2. [API Connection Problems](#api-connection-problems)
3. [Database Issues](#database-issues)
4. [External Services Problems](#external-services-problems)
5. [Performance Issues](#performance-issues)
6. [WebSocket Connection Issues](#websocket-connection-issues)
7. [Multi-Modal Processing Problems](#multi-modal-processing-problems)
8. [Local LLM Issues](#local-llm-issues)
9. [Authentication Problems](#authentication-problems)
10. [Logging and Debugging](#logging-and-debugging)

## Common Installation Issues

### Python Version Compatibility
**Problem:** `ImportError` or syntax errors during startup
```bash
# Check Python version
python --version
# Should be 3.11 or higher
```

**Solution:**
```bash
# Install correct Python version
sudo apt-get install python3.11 python3.11-venv
# Or use pyenv
pyenv install 3.11.0
pyenv local 3.11.0
```

### Dependency Installation Failures
**Problem:** `pip install` fails with compilation errors

**Solution:**
```bash
# Install system dependencies (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install build-essential python3-dev libffi-dev libssl-dev

# For macOS
xcode-select --install
brew install openssl libffi

# Upgrade pip and setuptools
pip install --upgrade pip setuptools wheel

# Install with verbose output to debug
pip install -v -r requirements.txt
```

### Virtual Environment Issues
**Problem:** Commands not found or wrong Python version

**Solution:**
```bash
# Recreate virtual environment
rm -rf .venv
python3.11 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows

# Verify activation
which python
python --version
```

### Permission Errors
**Problem:** Permission denied when creating files or directories

**Solution:**
```bash
# Fix ownership
sudo chown -R $USER:$USER /path/to/gremlinsai

# Fix permissions
chmod -R 755 /path/to/gremlinsai
chmod +x start.sh

# Create data directory with correct permissions
mkdir -p data
chmod 755 data
```

## API Connection Problems

### Server Won't Start
**Problem:** `uvicorn` fails to start or crashes immediately

**Diagnostic Steps:**
```bash
# Check if port is already in use
lsof -i :8000
netstat -tulpn | grep :8000

# Start with verbose logging
uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level debug

# Check environment variables
env | grep -E "(DATABASE_URL|LOG_LEVEL|API_)"
```

**Common Solutions:**
```bash
# Kill process using port 8000
sudo kill -9 $(lsof -t -i:8000)

# Use different port
uvicorn app.main:app --host 127.0.0.1 --port 8001

# Check database connection
python -c "from app.database.database import engine; print('DB OK')"
```

### 500 Internal Server Error
**Problem:** API returns 500 errors for all requests

**Diagnostic Steps:**
```bash
# Check server logs
tail -f logs/gremlinsai.log

# Test with curl
curl -v http://localhost:8000/health

# Check database migrations
alembic current
alembic upgrade head
```

### CORS Issues
**Problem:** Browser blocks API requests with CORS errors

**Solution:**
```python
# In .env file
CORS_ORIGINS=["http://localhost:3000", "https://your-frontend.com"]

# Or allow all origins for development (NOT for production)
CORS_ORIGINS=["*"]
```

## Database Issues

### SQLite Database Locked
**Problem:** `database is locked` error

**Solution:**
```bash
# Check for zombie processes
ps aux | grep python
kill -9 <process_id>

# Remove lock file
rm -f data/gremlinsai.db-wal data/gremlinsai.db-shm

# Backup and recreate database
cp data/gremlinsai.db data/gremlinsai.db.backup
rm data/gremlinsai.db
alembic upgrade head
```

### Migration Failures
**Problem:** `alembic upgrade head` fails

**Diagnostic Steps:**
```bash
# Check current migration version
alembic current

# Show migration history
alembic history

# Check for conflicts
alembic show head
```

**Solutions:**
```bash
# Reset to base and re-run migrations
alembic downgrade base
alembic upgrade head

# Or create new database
rm data/gremlinsai.db
alembic upgrade head

# Force migration (use with caution)
alembic stamp head
```

### PostgreSQL Connection Issues
**Problem:** Can't connect to PostgreSQL database

**Diagnostic Steps:**
```bash
# Test connection
psql -h localhost -U gremlinsai_user -d gremlinsai

# Check PostgreSQL status
sudo systemctl status postgresql

# Check connection string
echo $DATABASE_URL
```

**Solutions:**
```bash
# Start PostgreSQL
sudo systemctl start postgresql

# Create database and user
sudo -u postgres createdb gremlinsai
sudo -u postgres createuser gremlinsai_user
sudo -u postgres psql -c "ALTER USER gremlinsai_user PASSWORD 'password';"

# Update pg_hba.conf for authentication
sudo nano /etc/postgresql/*/main/pg_hba.conf
# Add: local   all   gremlinsai_user   md5
sudo systemctl restart postgresql
```

## External Services Problems

### Qdrant Connection Issues
**Problem:** Vector search fails or Qdrant unreachable

**Diagnostic Steps:**
```bash
# Test Qdrant connection
curl http://localhost:6333/collections

# Check Qdrant logs
docker logs qdrant_container

# Test from Python
python -c "
import qdrant_client
client = qdrant_client.QdrantClient(host='localhost', port=6333)
print(client.get_collections())
"
```

**Solutions:**
```bash
# Start Qdrant with Docker
docker run -p 6333:6333 qdrant/qdrant

# Or with Docker Compose
docker-compose up qdrant

# Initialize collections
python scripts/setup_qdrant.py --init

# Check firewall
sudo ufw allow 6333
```

### Redis Connection Problems
**Problem:** Real-time features not working, Redis errors

**Diagnostic Steps:**
```bash
# Test Redis connection
redis-cli ping

# Check Redis status
sudo systemctl status redis

# Test from Python
python -c "
import redis
r = redis.Redis(host='localhost', port=6379)
print(r.ping())
"
```

**Solutions:**
```bash
# Start Redis
sudo systemctl start redis

# Or with Docker
docker run -p 6379:6379 redis:alpine

# Check Redis configuration
sudo nano /etc/redis/redis.conf
# Ensure: bind 127.0.0.1
sudo systemctl restart redis
```

### Ollama LLM Issues
**Problem:** Local LLM requests fail or timeout

**Diagnostic Steps:**
```bash
# Check Ollama status
ollama list

# Test Ollama API
curl http://localhost:11434/api/tags

# Check GPU availability (if using GPU)
nvidia-smi

# Test model loading
ollama run llama3.2:8b "Hello"
```

**Solutions:**
```bash
# Start Ollama service
ollama serve

# Pull required models
ollama pull llama3.2:3b
ollama pull llama3.2:8b

# Check model loading
python scripts/test_local_llm.py

# For GPU issues
export CUDA_VISIBLE_DEVICES=0
ollama serve
```

## Performance Issues

### Slow API Response Times
**Problem:** API requests take too long to complete

**Diagnostic Steps:**
```bash
# Monitor system resources
htop
iostat -x 1
free -h

# Check API response times
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/api/v1/agent/invoke

# Profile Python application
python -m cProfile -o profile.stats app/main.py
```

**Solutions:**
```bash
# Increase worker processes
uvicorn app.main:app --workers 4

# Optimize database queries
# Add indexes to frequently queried columns
# Use connection pooling

# Enable caching
REDIS_URL=redis://localhost:6379
ENABLE_CACHING=true

# Optimize Qdrant settings
# Increase memory limits
# Use SSD storage
```

### High Memory Usage
**Problem:** Application consumes too much memory

**Diagnostic Steps:**
```bash
# Monitor memory usage
ps aux | grep python
top -p $(pgrep -f "uvicorn")

# Python memory profiling
pip install memory-profiler
python -m memory_profiler app/main.py
```

**Solutions:**
```bash
# Reduce worker processes
uvicorn app.main:app --workers 2

# Optimize model loading
ENABLE_LOCAL_LLM=false  # If not needed

# Use memory-efficient settings
MAX_CONVERSATION_HISTORY=50
CHUNK_SIZE=500

# Enable garbage collection
import gc
gc.collect()
```

## WebSocket Connection Issues

### WebSocket Connection Fails
**Problem:** Real-time features don't work, WebSocket errors

**Diagnostic Steps:**
```bash
# Test WebSocket connection
wscat -c ws://localhost:8000/api/v1/ws/ws

# Check browser console for errors
# Check network tab in developer tools

# Test with curl
curl --include \
     --no-buffer \
     --header "Connection: Upgrade" \
     --header "Upgrade: websocket" \
     --header "Sec-WebSocket-Key: SGVsbG8sIHdvcmxkIQ==" \
     --header "Sec-WebSocket-Version: 13" \
     http://localhost:8000/api/v1/ws/ws
```

**Solutions:**
```bash
# Check proxy configuration (if using nginx)
# Ensure WebSocket headers are passed through

# For nginx:
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";

# Check firewall settings
sudo ufw allow 8000

# Verify WebSocket endpoint
curl http://localhost:8000/api/v1/realtime/info
```

### WebSocket Disconnections
**Problem:** Frequent WebSocket disconnections

**Solutions:**
```javascript
// Implement reconnection logic in frontend
const reconnectWebSocket = () => {
  setTimeout(() => {
    console.log('Attempting to reconnect...');
    connectWebSocket();
  }, 1000);
};

ws.onclose = () => {
  console.log('WebSocket disconnected');
  reconnectWebSocket();
};

// Send periodic ping messages
setInterval(() => {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'ping' }));
  }
}, 30000);
```

## Multi-Modal Processing Problems

### File Upload Failures
**Problem:** Multi-modal file uploads fail or timeout

**Diagnostic Steps:**
```bash
# Check file size limits
curl -F "file=@large_video.mp4" http://localhost:8000/api/v1/multimodal/process/video

# Check disk space
df -h

# Check temporary directory
ls -la /tmp/
```

**Solutions:**
```bash
# Increase file size limits
# In nginx.conf:
client_max_body_size 100M;

# In FastAPI app:
from fastapi import FastAPI, File, UploadFile
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    max_age=600,
)

# Clean up temporary files
find /tmp -name "*.tmp" -mtime +1 -delete
```

### Audio/Video Processing Errors
**Problem:** FFmpeg or audio processing libraries fail

**Solutions:**
```bash
# Install FFmpeg
sudo apt-get install ffmpeg

# For macOS
brew install ffmpeg

# Install audio processing libraries
pip install librosa soundfile

# Test FFmpeg installation
ffmpeg -version
python -c "import librosa; print('Audio processing OK')"
```

## Local LLM Issues

### Model Loading Failures
**Problem:** Ollama models fail to load or run out of memory

**Diagnostic Steps:**
```bash
# Check available memory
free -h
nvidia-smi  # For GPU memory

# Check model size
ollama show llama3.2:70b

# Monitor during model loading
watch -n 1 'nvidia-smi; free -h'
```

**Solutions:**
```bash
# Use smaller models
ollama pull llama3.2:3b  # Instead of 70b

# Increase swap space
sudo fallocate -l 32G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Configure model memory limits
OLLAMA_MAX_VRAM=20GB
OLLAMA_GPU_MEMORY_FRACTION=0.8
```

### Slow LLM Inference
**Problem:** Local LLM responses are very slow

**Solutions:**
```bash
# Use GPU acceleration
export CUDA_VISIBLE_DEVICES=0
ollama serve

# Optimize model settings
OLLAMA_NUM_PARALLEL=4
OLLAMA_FLASH_ATTENTION=1

# Use tiered routing
ENABLE_TIERED_ROUTING=true
FAST_MODEL=llama3.2:3b
POWERFUL_MODEL=llama3.2:70b
```

## Authentication Problems

### API Key Issues
**Problem:** API key authentication fails

**Diagnostic Steps:**
```bash
# Test API key generation
curl -X POST http://localhost:8000/api/v1/auth/api-keys \
  -H "Content-Type: application/json" \
  -d '{"name": "test", "permissions": ["read"]}'

# Test API key validation
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:8000/api/v1/auth/validate
```

### OAuth Issues
**Problem:** Google OAuth authentication fails

**Solutions:**
```bash
# Check OAuth configuration
echo $GOOGLE_CLIENT_ID
echo $GOOGLE_CLIENT_SECRET

# Verify redirect URI in Google Console
# Should match: http://localhost:8000/api/v1/oauth/google/callback

# Check OAuth flow
curl -X POST http://localhost:8000/api/v1/oauth/google/callback \
  -H "Content-Type: application/json" \
  -d '{"code": "oauth_code_from_google"}'
```

## Logging and Debugging

### Enable Debug Logging
```bash
# In .env file
LOG_LEVEL=DEBUG

# Or set environment variable
export LOG_LEVEL=DEBUG

# Start with debug logging
uvicorn app.main:app --log-level debug
```

### Structured Logging
```python
# Add to your code for debugging
import logging
logger = logging.getLogger(__name__)

logger.debug("Debug information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred", exc_info=True)
```

### Health Check Endpoints
```bash
# System health
curl http://localhost:8000/health

# Detailed system status
curl http://localhost:8000/api/v1/system/status

# Service-specific health checks
curl http://localhost:8000/api/v1/orchestrator/health-check
curl http://localhost:8000/api/analytics/status
```

### Performance Monitoring
```bash
# Install monitoring tools
pip install prometheus-client

# Enable metrics endpoint
curl http://localhost:8000/metrics

# Monitor with Grafana
docker run -d -p 3000:3000 grafana/grafana
```

## Getting Help

### Log Collection
```bash
# Collect system information
python scripts/collect_debug_info.py > debug_info.txt

# Include in bug reports:
# - Python version
# - OS version
# - Error messages
# - Steps to reproduce
# - Configuration (without secrets)
```

### Community Support
- **GitHub Issues**: Report bugs and feature requests
- **Documentation**: Check latest docs at `/docs`
- **Discord/Slack**: Join community channels
- **Stack Overflow**: Tag questions with `gremlinsai`
