# GremlinsAI Setup & Installation Guide v10.0.0

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Quick Start Installation](#quick-start-installation)
3. [Development Environment Setup](#development-environment-setup)
4. [External Services Configuration](#external-services-configuration)
5. [Production Deployment](#production-deployment)
6. [Docker Setup](#docker-setup)
7. [Kubernetes Deployment](#kubernetes-deployment)
8. [Troubleshooting](#troubleshooting)
9. [Performance Optimization](#performance-optimization)

## System Requirements

### Minimum Requirements
- **Python**: 3.11 or higher
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 10GB free space
- **Network**: Internet connection for external services

### Recommended for Production
- **Python**: 3.11+
- **RAM**: 32GB or higher
- **CPU**: 8+ cores
- **GPU**: NVIDIA GPU with 24GB+ VRAM (for local LLM optimization)
- **Storage**: SSD with 100GB+ free space
- **Network**: High-speed internet connection

### External Services
- **Qdrant**: Vector database (can be local or cloud)
- **Redis**: For caching and real-time features
- **Ollama**: For local LLM inference (optional)
- **PostgreSQL**: For production database (optional, SQLite default)

## Quick Start Installation

### 1. Clone Repository
```bash
git clone https://github.com/your-org/GremlinsAI_backend.git
cd GremlinsAI_backend
```

### 2. Create Virtual Environment
```bash
# Using venv
python -m venv .venv

# Activate on Linux/Mac
source .venv/bin/activate

# Activate on Windows
.venv\Scripts\activate
```

### 3. Install Dependencies
```bash
# Install core dependencies
pip install -r requirements.txt

# Install development dependencies (optional)
pip install -r requirements-dev.txt
```

### 4. Environment Configuration
```bash
# Copy example environment file
cp .env.example .env

# Edit configuration
nano .env  # or your preferred editor
```

**Basic .env Configuration:**
```bash
# Core Application
LOG_LEVEL=INFO
DATABASE_URL=sqlite:///./data/gremlinsai.db
SECRET_KEY=your-secret-key-here

# API Configuration
API_HOST=127.0.0.1
API_PORT=8000
API_WORKERS=1

# External Services (optional)
QDRANT_HOST=localhost
QDRANT_PORT=6333
REDIS_URL=redis://localhost:6379
OLLAMA_BASE_URL=http://localhost:11434

# Authentication (optional)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Features
ENABLE_MULTIMODAL=true
ENABLE_COLLABORATION=true
ENABLE_ANALYTICS=true
ENABLE_LOCAL_LLM=true
```

### 5. Initialize Database
```bash
# Run database migrations
alembic upgrade head

# Verify database setup
python -c "from app.database.database import engine; print('Database connected successfully')"
```

### 6. Start the Server
```bash
# Using the provided script
./start.sh

# Or directly with uvicorn
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 7. Verify Installation
```bash
# Check API health
curl http://localhost:8000/health

# Check system status
curl http://localhost:8000/api/v1/system/status

# Access interactive documentation
open http://localhost:8000/docs
```

## Development Environment Setup

### 1. Install Development Tools
```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Install testing tools
pip install pytest pytest-asyncio pytest-cov

# Install code quality tools
pip install black flake8 mypy
```

### 2. Configure IDE (VS Code)
```json
// .vscode/settings.json
{
  "python.defaultInterpreterPath": "./.venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests/"],
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true
  }
}
```

### 3. Run Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/
```

### 4. Code Quality Checks
```bash
# Format code
black app/ tests/

# Check linting
flake8 app/ tests/

# Type checking
mypy app/

# Run all quality checks
./scripts/quality-check.sh
```

## External Services Configuration

### Qdrant Vector Database

#### Local Installation
```bash
# Using Docker
docker run -p 6333:6333 qdrant/qdrant

# Using Docker Compose
docker-compose up qdrant
```

#### Cloud Setup (Qdrant Cloud)
```bash
# Update .env file
QDRANT_HOST=your-cluster-url.qdrant.io
QDRANT_PORT=6333
QDRANT_API_KEY=your-api-key
QDRANT_USE_HTTPS=true
```

#### Verify Qdrant Connection
```bash
# Test connection
python scripts/setup_qdrant.py --test

# Initialize collections
python scripts/setup_qdrant.py --init
```

### Redis Setup

#### Local Installation
```bash
# Using package manager (Ubuntu/Debian)
sudo apt-get install redis-server

# Using Docker
docker run -p 6379:6379 redis:alpine

# Using Homebrew (macOS)
brew install redis
brew services start redis
```

#### Configuration
```bash
# Update .env file
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=your-password  # if authentication enabled
```

### Ollama Local LLM Setup

#### Installation
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull recommended models
ollama pull llama3.2:3b   # Fast model
ollama pull llama3.2:8b   # Balanced model
ollama pull llama3.2:70b  # Powerful model (requires 40GB+ VRAM)
```

#### Configuration
```bash
# Update .env file
OLLAMA_BASE_URL=http://localhost:11434
ENABLE_LOCAL_LLM=true
LLM_PROVIDER=ollama
LLM_MODEL=llama3.2:8b
```

#### Verify Ollama Setup
```bash
# Test Ollama connection
python scripts/test_local_llm.py

# Check available models
curl http://localhost:11434/api/tags
```

### PostgreSQL Setup (Production)

#### Installation
```bash
# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# Create database and user
sudo -u postgres createdb gremlinsai
sudo -u postgres createuser gremlinsai_user
sudo -u postgres psql -c "ALTER USER gremlinsai_user PASSWORD 'your-password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE gremlinsai TO gremlinsai_user;"
```

#### Configuration
```bash
# Update .env file
DATABASE_URL=postgresql://gremlinsai_user:your-password@localhost/gremlinsai
```

## Production Deployment

### 1. Production Environment Setup
```bash
# Create production environment file
cp .env.example .env.production

# Update production settings
nano .env.production
```

**Production .env Configuration:**
```bash
# Production settings
LOG_LEVEL=WARNING
DEBUG=false
DATABASE_URL=postgresql://user:pass@localhost/gremlinsai
SECRET_KEY=your-very-secure-secret-key

# Performance settings
API_WORKERS=4
WORKER_CONNECTIONS=1000
KEEPALIVE_TIMEOUT=65

# Security settings
ALLOWED_HOSTS=["your-domain.com", "api.your-domain.com"]
CORS_ORIGINS=["https://your-frontend.com"]
ENABLE_HTTPS=true

# External services
QDRANT_HOST=your-qdrant-cluster.com
REDIS_URL=redis://your-redis-cluster:6379
```

### 2. Production Server Setup
```bash
# Install production WSGI server
pip install gunicorn uvloop httptools

# Create systemd service
sudo nano /etc/systemd/system/gremlinsai.service
```

**Systemd Service Configuration:**
```ini
[Unit]
Description=GremlinsAI API Server
After=network.target

[Service]
Type=exec
User=gremlinsai
Group=gremlinsai
WorkingDirectory=/opt/gremlinsai
Environment=PATH=/opt/gremlinsai/.venv/bin
EnvironmentFile=/opt/gremlinsai/.env.production
ExecStart=/opt/gremlinsai/.venv/bin/gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

### 3. Nginx Configuration
```nginx
# /etc/nginx/sites-available/gremlinsai
server {
    listen 80;
    server_name api.your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.your-domain.com;

    ssl_certificate /path/to/your/certificate.crt;
    ssl_certificate_key /path/to/your/private.key;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Static files (if any)
    location /static/ {
        alias /opt/gremlinsai/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### 4. SSL Certificate Setup
```bash
# Using Let's Encrypt
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d api.your-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### 5. Monitoring Setup
```bash
# Install monitoring tools
pip install prometheus-client grafana-api

# Setup Prometheus monitoring
python scripts/setup_monitoring.py

# Configure log rotation
sudo nano /etc/logrotate.d/gremlinsai
```

## Docker Setup

### 1. Docker Compose Configuration
```yaml
# docker-compose.yml
version: '3.8'

services:
  gremlinsai:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/gremlinsai
      - QDRANT_HOST=qdrant
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - qdrant
      - redis
    volumes:
      - ./data:/app/data

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: gremlinsai
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  qdrant:
    image: qdrant/qdrant
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

volumes:
  postgres_data:
  qdrant_data:
  redis_data:
  ollama_data:
```

### 2. Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p /app/data

# Run database migrations
RUN alembic upgrade head

# Expose port
EXPOSE 8000

# Start server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 3. Docker Commands
```bash
# Build and start services
docker-compose up --build

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f gremlinsai

# Stop services
docker-compose down

# Clean up
docker-compose down -v --remove-orphans
```
