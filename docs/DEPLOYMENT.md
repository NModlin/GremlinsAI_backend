# gremlinsAI Deployment Guide

## Overview

This guide covers deploying the gremlinsAI backend in various environments, from development to production.

## Prerequisites

- Python 3.11 or higher
- Git
- Internet connection (for DuckDuckGo search functionality)

## Development Deployment

### Local Development Setup

1. **Clone and Setup**
   ```bash
   git clone <repository-url>
   cd GremlinsAI_backend
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Environment Configuration**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

3. **Database Setup**
   ```bash
   alembic upgrade head
   ```

4. **Start Development Server**
   ```bash
   ./start.sh
   # Or: uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

## Production Deployment

### Environment Variables

Create a production `.env` file:

```bash
# Production Configuration
LOG_LEVEL=INFO
DATABASE_URL=sqlite:///./data/gremlinsai.db

# Optional: External API Keys
# OPENAI_API_KEY=your-key-here

# External Service Configurations
OLLAMA_BASE_URL=http://localhost:11434
QDRANT_HOST=localhost
QDRANT_PORT=6333
REDIS_URL=redis://localhost:6379
```

### Using Gunicorn (Recommended)

1. **Install Gunicorn**
   ```bash
   pip install gunicorn
   ```

2. **Create Gunicorn Configuration**
   ```python
   # gunicorn.conf.py
   bind = "0.0.0.0:8000"
   workers = 4
   worker_class = "uvicorn.workers.UvicornWorker"
   max_requests = 1000
   max_requests_jitter = 100
   timeout = 30
   keepalive = 2
   preload_app = True
   ```

3. **Start Production Server**
   ```bash
   gunicorn app.main:app -c gunicorn.conf.py
   ```

### Using Docker

1. **Create Dockerfile**
   ```dockerfile
   FROM python:3.11-slim

   WORKDIR /app

   # Install system dependencies
   RUN apt-get update && apt-get install -y \
       gcc \
       && rm -rf /var/lib/apt/lists/*

   # Copy requirements and install Python dependencies
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt

   # Copy application code
   COPY . .

   # Create data directory
   RUN mkdir -p data

   # Run database migrations
   RUN alembic upgrade head

   # Expose port
   EXPOSE 8000

   # Start server
   CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
   ```

2. **Build and Run**
   ```bash
   docker build -t gremlinsai-backend .
   docker run -p 8000:8000 -v $(pwd)/data:/app/data gremlinsai-backend
   ```

### Using Docker Compose

1. **Create docker-compose.yml**
   ```yaml
   version: '3.8'
   
   services:
     gremlinsai:
       build: .
       ports:
         - "8000:8000"
       volumes:
         - ./data:/app/data
         - ./.env:/app/.env
       environment:
         - DATABASE_URL=sqlite:///./data/gremlinsai.db
       restart: unless-stopped
   ```

2. **Deploy**
   ```bash
   docker-compose up -d
   ```

## Cloud Deployment

### AWS EC2

1. **Launch EC2 Instance**
   - Choose Ubuntu 22.04 LTS
   - t3.medium or larger recommended
   - Configure security group to allow port 8000

2. **Setup on EC2**
   ```bash
   # Update system
   sudo apt update && sudo apt upgrade -y
   
   # Install Python 3.11
   sudo apt install python3.11 python3.11-venv python3-pip git -y
   
   # Clone and setup application
   git clone <repository-url>
   cd GremlinsAI_backend
   python3.11 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   
   # Setup environment
   cp .env.example .env
   # Edit .env for production
   
   # Initialize database
   alembic upgrade head
   
   # Install and configure systemd service
   sudo cp deployment/gremlinsai.service /etc/systemd/system/
   sudo systemctl enable gremlinsai
   sudo systemctl start gremlinsai
   ```

3. **Create Systemd Service**
   ```ini
   # /etc/systemd/system/gremlinsai.service
   [Unit]
   Description=gremlinsAI Backend
   After=network.target
   
   [Service]
   Type=exec
   User=ubuntu
   WorkingDirectory=/home/ubuntu/GremlinsAI_backend
   Environment=PATH=/home/ubuntu/GremlinsAI_backend/.venv/bin
   ExecStart=/home/ubuntu/GremlinsAI_backend/.venv/bin/gunicorn app.main:app -c gunicorn.conf.py
   Restart=always
   
   [Install]
   WantedBy=multi-user.target
   ```

### Heroku

1. **Create Procfile**
   ```
   web: gunicorn app.main:app -c gunicorn.conf.py
   release: alembic upgrade head
   ```

2. **Deploy**
   ```bash
   heroku create your-app-name
   heroku config:set DATABASE_URL=sqlite:///./data/gremlinsai.db
   git push heroku main
   ```

### DigitalOcean App Platform

1. **Create app.yaml**
   ```yaml
   name: gremlinsai-backend
   services:
   - name: api
     source_dir: /
     github:
       repo: your-username/GremlinsAI_backend
       branch: main
     run_command: gunicorn app.main:app -c gunicorn.conf.py
     environment_slug: python
     instance_count: 1
     instance_size_slug: basic-xxs
     routes:
     - path: /
   ```

## Database Considerations

### SQLite (Default)
- Suitable for development and small-scale production
- Data stored in `./data/gremlinsai.db`
- Automatic backups recommended

### PostgreSQL (Alternative)
```bash
# Environment variable for PostgreSQL
DATABASE_URL=postgresql://user:password@localhost/gremlinsai
```

## Monitoring and Logging

### Application Logs
```python
# Configure logging in production
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
```

### Health Checks
- Endpoint: `GET /`
- Expected response: `{"message": "Welcome to the gremlinsAI API!"}`

### Metrics
- Response times
- Request counts
- Error rates
- Database query performance

## Security Considerations

### Production Checklist
- [ ] Use HTTPS in production
- [ ] Set secure environment variables
- [ ] Configure CORS appropriately
- [ ] Implement rate limiting
- [ ] Regular security updates
- [ ] Database backups
- [ ] Monitor logs for suspicious activity

### Reverse Proxy (Nginx)
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Backup and Recovery

### Database Backup
```bash
# SQLite backup
cp data/gremlinsai.db data/gremlinsai_backup_$(date +%Y%m%d_%H%M%S).db

# Automated backup script
#!/bin/bash
BACKUP_DIR="/path/to/backups"
DATE=$(date +%Y%m%d_%H%M%S)
cp data/gremlinsai.db "$BACKUP_DIR/gremlinsai_$DATE.db"
find "$BACKUP_DIR" -name "gremlinsai_*.db" -mtime +7 -delete
```

### Application Backup
```bash
# Full application backup
tar -czf gremlinsai_backup_$(date +%Y%m%d).tar.gz \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='.git' \
    .
```

## Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   # Find process using port 8000
   lsof -i :8000
   # Kill process
   kill -9 <PID>
   ```

2. **Database Migration Issues**
   ```bash
   # Reset database (development only)
   rm data/gremlinsai.db
   alembic upgrade head
   ```

3. **Permission Issues**
   ```bash
   # Fix file permissions
   chmod +x start.sh
   chown -R $USER:$USER data/
   ```

### Log Analysis
```bash
# View application logs
tail -f app.log

# Search for errors
grep -i error app.log

# Monitor real-time requests
tail -f app.log | grep -i "POST\|GET"
```

## Performance Optimization

### Production Settings
- Use multiple Gunicorn workers
- Enable gzip compression
- Configure appropriate timeouts
- Monitor memory usage
- Implement caching where appropriate

### Database Optimization
- Regular VACUUM for SQLite
- Monitor query performance
- Consider connection pooling for high load

This deployment guide covers all current deployment options and configurations for the GremlinsAI backend system.
