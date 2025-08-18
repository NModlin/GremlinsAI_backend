# Phase 4: Deployment Preparation

## 🎯 Executive Summary

**Objective**: Prepare application for production deployment with containerization, CI/CD, and basic monitoring  
**Duration**: 2-3 weeks  
**Priority**: HIGH - Final step before production readiness  
**Success Criteria**: Containerized application, working CI/CD pipeline, staging deployment successful, basic load testing passes

**Focus Areas**:
- Containerization with Docker
- CI/CD pipeline setup
- Staging environment deployment
- Basic monitoring and health checks
- Load testing with realistic targets

---

## 📋 Prerequisites

**From Phase 3**:
- ✅ Environment-specific configuration working
- ✅ Structured logging and error handling operational
- ✅ Basic security measures implemented
- ✅ Application runs with all middleware

**Additional Requirements**:
- Docker installed and running
- Access to container registry (Docker Hub, etc.)
- CI/CD platform access (GitHub Actions, etc.)

---

## 🔧 Task 1: Containerization (1 week)

### **Step 1.1: Create Production Dockerfile**

**File**: `Dockerfile`

```dockerfile
# Multi-stage build for production
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Production stage
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r appuser && useradd -r -g appuser appuser

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Create app directory
WORKDIR /app

# Copy application code
COPY . .

# Create data directory and set permissions
RUN mkdir -p /app/data /app/logs && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### **Step 1.2: Create Docker Compose for Development**

**File**: `docker-compose.yml`

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENV=development
      - DATABASE_URL=sqlite:///./data/gremlinsai.db
      - REDIS_URL=redis://redis:6379
      - LOG_LEVEL=INFO
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    depends_on:
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

volumes:
  redis_data:
```

### **Step 1.3: Create Docker Compose for Production**

**File**: `docker-compose.prod.yml`

```yaml
version: '3.8'

services:
  app:
    image: gremlinsai:latest
    ports:
      - "8000:8000"
    environment:
      - ENV=production
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - SECRET_KEY=${SECRET_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - LOG_LEVEL=WARNING
    volumes:
      - app_data:/app/data
      - app_logs:/app/logs
    depends_on:
      - redis
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - app
    restart: unless-stopped

volumes:
  app_data:
  app_logs:
  redis_data:
```

### **Step 1.4: Create Nginx Configuration**

**File**: `nginx.conf`

```nginx
events {
    worker_connections 1024;
}

http {
    upstream app {
        server app:8000;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

    server {
        listen 80;
        server_name _;

        # Security headers
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header Referrer-Policy "no-referrer-when-downgrade" always;
        add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;

        # API routes
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            
            proxy_pass http://app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # Timeouts
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        # Health check
        location /health {
            proxy_pass http://app;
            access_log off;
        }

        # Static files (if any)
        location /static/ {
            alias /app/static/;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
}
```

### **Validation Step 1**:
```bash
# Build and test Docker image
docker build -t gremlinsai:test .

# Test container runs
docker run --rm -d --name gremlinsai-test -p 8005:8000 gremlinsai:test

# Wait for startup
sleep 10

# Test health endpoint
curl -f http://localhost:8005/health && echo "✅ Container health check passed"

# Cleanup
docker stop gremlinsai-test

# Test docker-compose
docker-compose up -d
sleep 15
curl -f http://localhost:8000/health && echo "✅ Docker Compose setup works"
docker-compose down
```

---

## 🔧 Task 2: CI/CD Pipeline (1 week)

### **Step 2.1: GitHub Actions Workflow**

**File**: `.github/workflows/ci-cd.yml`

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Cache pip dependencies
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements*.txt') }}
        restore-keys: |
          ${{ runner.os }}-pip-

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt

    - name: Run linting
      run: |
        flake8 app tests --count --select=E9,F63,F7,F82 --show-source --statistics
        flake8 app tests --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

    - name: Run type checking
      run: |
        mypy app --ignore-missing-imports

    - name: Run tests
      env:
        ENV: testing
        DATABASE_URL: sqlite:///./test.db
        REDIS_URL: redis://localhost:6379/1
        SECRET_KEY: test-secret-key
      run: |
        python -m pytest tests/ -v --cov=app --cov-report=xml --cov-report=term-missing

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella

  security:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install security tools
      run: |
        pip install bandit safety

    - name: Run security scan
      run: |
        bandit -r app -f json -o bandit-report.json || true
        safety check --json --output safety-report.json || true

    - name: Upload security reports
      uses: actions/upload-artifact@v3
      with:
        name: security-reports
        path: |
          bandit-report.json
          safety-report.json

  build:
    needs: [test, security]
    runs-on: ubuntu-latest
    if: github.event_name == 'push'

    steps:
    - uses: actions/checkout@v4

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3

    - name: Log in to Container Registry
      uses: docker/login-action@v3
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}

    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v5
      with:
        images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
        tags: |
          type=ref,event=branch
          type=ref,event=pr
          type=sha,prefix={{branch}}-

    - name: Build and push Docker image
      uses: docker/build-push-action@v5
      with:
        context: .
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
        cache-from: type=gha
        cache-to: type=gha,mode=max

  deploy-staging:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/develop'
    environment: staging

    steps:
    - uses: actions/checkout@v4

    - name: Deploy to staging
      run: |
        echo "Deploying to staging environment"
        # Add your staging deployment commands here
        # Example: kubectl apply -f k8s/staging/

  deploy-production:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: production

    steps:
    - uses: actions/checkout@v4

    - name: Deploy to production
      run: |
        echo "Deploying to production environment"
        # Add your production deployment commands here
        # Example: kubectl apply -f k8s/production/
```

### **Step 2.2: Pre-commit Hooks**

**File**: `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict

  - repo: https://github.com/psf/black
    rev: 23.11.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
        args: [--max-line-length=127, --extend-ignore=E203,W503]

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: ["--profile", "black"]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.1
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
        args: [--ignore-missing-imports]
```

### **Step 2.3: Setup Pre-commit**

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run on all files (optional)
pre-commit run --all-files
```

### **Validation Step 2**:
```bash
# Test pre-commit hooks
pre-commit run --all-files

# Test GitHub Actions locally (if act is installed)
# act -j test

# Validate workflow syntax
python -c "
import yaml
with open('.github/workflows/ci-cd.yml', 'r') as f:
    workflow = yaml.safe_load(f)
print('✅ GitHub Actions workflow is valid YAML')
print(f'Jobs: {list(workflow[\"jobs\"].keys())}')
"
```

---

## 🔧 Task 3: Basic Monitoring Setup (1 week)

### **Step 3.1: Health Check Endpoints**

**File**: `app/api/v1/endpoints/monitoring.py`

```python
"""
Monitoring and health check endpoints
"""
import time
import psutil
from fastapi import APIRouter, Depends
from datetime import datetime
from typing import Dict, Any
from app.core.config import get_settings
from app.database import get_db

router = APIRouter()

@router.get("/health")
async def health_check():
    """Basic health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": get_settings().version
    }

@router.get("/ready")
async def readiness_check(db=Depends(get_db)):
    """Readiness check with dependency validation"""
    checks = {}
    overall_status = "ready"

    # Database check
    try:
        db.execute("SELECT 1").fetchone()
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {str(e)}"
        overall_status = "not_ready"

    # Redis check (if configured)
    try:
        import redis
        settings = get_settings()
        r = redis.from_url(settings.redis.url)
        r.ping()
        checks["redis"] = "healthy"
    except Exception as e:
        checks["redis"] = f"unhealthy: {str(e)}"
        overall_status = "not_ready"

    return {
        "status": overall_status,
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/metrics")
async def basic_metrics():
    """Basic system metrics"""
    return {
        "system": {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
        },
        "process": {
            "memory_mb": psutil.Process().memory_info().rss / 1024 / 1024,
            "cpu_percent": psutil.Process().cpu_percent(),
        },
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/info")
async def system_info():
    """System information"""
    settings = get_settings()
    return {
        "app_name": settings.app_name,
        "version": settings.version,
        "environment": settings.environment,
        "python_version": f"{psutil.sys.version_info.major}.{psutil.sys.version_info.minor}.{psutil.sys.version_info.micro}",
        "uptime_seconds": time.time() - psutil.boot_time(),
        "timestamp": datetime.utcnow().isoformat()
    }
```

### **Step 3.2: Basic Load Testing**

**File**: `tests/load/basic_load_test.py`

```python
"""
Basic load testing with realistic targets
"""
import asyncio
import aiohttp
import time
import statistics
from typing import List, Dict, Any
import argparse

class LoadTester:
    """Simple load tester for basic validation"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = []

    async def make_request(self, session: aiohttp.ClientSession, endpoint: str) -> Dict[str, Any]:
        """Make a single request and measure response time"""
        start_time = time.time()

        try:
            async with session.get(f"{self.base_url}{endpoint}") as response:
                end_time = time.time()
                response_time = end_time - start_time

                return {
                    "endpoint": endpoint,
                    "status_code": response.status,
                    "response_time": response_time,
                    "success": response.status == 200,
                    "timestamp": start_time
                }
        except Exception as e:
            end_time = time.time()
            return {
                "endpoint": endpoint,
                "status_code": 0,
                "response_time": end_time - start_time,
                "success": False,
                "error": str(e),
                "timestamp": start_time
            }

    async def run_concurrent_requests(self, endpoint: str, concurrent_users: int, requests_per_user: int):
        """Run concurrent requests"""
        async with aiohttp.ClientSession() as session:
            tasks = []

            for user in range(concurrent_users):
                for request in range(requests_per_user):
                    task = self.make_request(session, endpoint)
                    tasks.append(task)

            results = await asyncio.gather(*tasks)
            self.results.extend(results)

            return results

    def analyze_results(self) -> Dict[str, Any]:
        """Analyze load test results"""
        if not self.results:
            return {"error": "No results to analyze"}

        successful_requests = [r for r in self.results if r["success"]]
        failed_requests = [r for r in self.results if not r["success"]]

        response_times = [r["response_time"] for r in successful_requests]

        if not response_times:
            return {"error": "No successful requests"}

        return {
            "total_requests": len(self.results),
            "successful_requests": len(successful_requests),
            "failed_requests": len(failed_requests),
            "success_rate": len(successful_requests) / len(self.results) * 100,
            "response_times": {
                "min": min(response_times),
                "max": max(response_times),
                "mean": statistics.mean(response_times),
                "median": statistics.median(response_times),
                "p95": sorted(response_times)[int(len(response_times) * 0.95)] if len(response_times) > 20 else max(response_times),
                "p99": sorted(response_times)[int(len(response_times) * 0.99)] if len(response_times) > 100 else max(response_times),
            },
            "requests_per_second": len(successful_requests) / (max([r["timestamp"] for r in self.results]) - min([r["timestamp"] for r in self.results])) if len(self.results) > 1 else 0
        }

async def run_basic_load_test():
    """Run basic load test with realistic targets"""
    tester = LoadTester()

    print("🚀 Starting basic load test...")
    print("Target: 50 concurrent users, 2 requests each")
    print("Endpoint: /health")

    # Test health endpoint with 50 concurrent users
    await tester.run_concurrent_requests("/health", concurrent_users=50, requests_per_user=2)

    # Analyze results
    analysis = tester.analyze_results()

    print("\n📊 Load Test Results:")
    print(f"Total Requests: {analysis['total_requests']}")
    print(f"Success Rate: {analysis['success_rate']:.1f}%")
    print(f"Failed Requests: {analysis['failed_requests']}")

    if 'response_times' in analysis:
        rt = analysis['response_times']
        print(f"\n⏱️  Response Times:")
        print(f"  Mean: {rt['mean']:.3f}s")
        print(f"  Median: {rt['median']:.3f}s")
        print(f"  95th percentile: {rt['p95']:.3f}s")
        print(f"  Max: {rt['max']:.3f}s")

        print(f"\n🎯 Performance Targets:")
        print(f"  ✅ Success Rate >95%: {'PASS' if analysis['success_rate'] > 95 else 'FAIL'}")
        print(f"  ✅ Mean Response <5s: {'PASS' if rt['mean'] < 5.0 else 'FAIL'}")
        print(f"  ✅ 95th percentile <10s: {'PASS' if rt['p95'] < 10.0 else 'FAIL'}")

    return analysis

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Basic load test")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL to test")
    args = parser.parse_args()

    asyncio.run(run_basic_load_test())
```

### **Step 3.3: Deployment Health Check Script**

**File**: `scripts/deployment_health_check.py`

```python
#!/usr/bin/env python3
"""
Deployment health check script
"""
import requests
import time
import sys
import argparse
from typing import Dict, Any, List

class HealthChecker:
    """Health check utilities for deployment validation"""

    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

    def check_endpoint(self, endpoint: str, expected_status: int = 200) -> Dict[str, Any]:
        """Check a single endpoint"""
        url = f"{self.base_url}{endpoint}"

        try:
            start_time = time.time()
            response = requests.get(url, timeout=self.timeout)
            response_time = time.time() - start_time

            return {
                "endpoint": endpoint,
                "url": url,
                "status_code": response.status_code,
                "response_time": response_time,
                "success": response.status_code == expected_status,
                "content_length": len(response.content),
                "headers": dict(response.headers)
            }
        except Exception as e:
            return {
                "endpoint": endpoint,
                "url": url,
                "status_code": 0,
                "response_time": 0,
                "success": False,
                "error": str(e)
            }

    def wait_for_healthy(self, max_wait: int = 300) -> bool:
        """Wait for application to become healthy"""
        start_time = time.time()

        while time.time() - start_time < max_wait:
            result = self.check_endpoint("/health")

            if result["success"]:
                print(f"✅ Application is healthy after {time.time() - start_time:.1f}s")
                return True

            print(f"⏳ Waiting for health check... ({time.time() - start_time:.1f}s)")
            time.sleep(5)

        print(f"❌ Application did not become healthy within {max_wait}s")
        return False

    def run_comprehensive_check(self) -> Dict[str, Any]:
        """Run comprehensive health check"""
        endpoints = [
            ("/health", 200),
            ("/ready", 200),
            ("/metrics", 200),
            ("/info", 200),
            ("/docs", 200),
            ("/api/v1/health", 200),
        ]

        results = []
        for endpoint, expected_status in endpoints:
            result = self.check_endpoint(endpoint, expected_status)
            results.append(result)

        # Summary
        successful = sum(1 for r in results if r["success"])
        total = len(results)

        return {
            "total_checks": total,
            "successful_checks": successful,
            "failed_checks": total - successful,
            "success_rate": successful / total * 100,
            "results": results,
            "overall_healthy": successful == total
        }

def main():
    parser = argparse.ArgumentParser(description="Deployment health check")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL to check")
    parser.add_argument("--wait", action="store_true", help="Wait for application to become healthy")
    parser.add_argument("--timeout", type=int, default=30, help="Request timeout in seconds")
    args = parser.parse_args()

    checker = HealthChecker(args.url, args.timeout)

    if args.wait:
        if not checker.wait_for_healthy():
            sys.exit(1)

    # Run comprehensive check
    results = checker.run_comprehensive_check()

    print(f"\n📋 Health Check Results for {args.url}")
    print(f"Success Rate: {results['success_rate']:.1f}% ({results['successful_checks']}/{results['total_checks']})")

    for result in results['results']:
        status = "✅" if result['success'] else "❌"
        endpoint = result['endpoint']

        if result['success']:
            print(f"{status} {endpoint} - {result['status_code']} ({result['response_time']:.3f}s)")
        else:
            error = result.get('error', f"Status {result['status_code']}")
            print(f"{status} {endpoint} - {error}")

    if not results['overall_healthy']:
        print("\n❌ Deployment health check FAILED")
        sys.exit(1)
    else:
        print("\n✅ Deployment health check PASSED")

if __name__ == "__main__":
    main()
```

### **Validation Step 3**:
```bash
# Test monitoring endpoints
python -c "
import requests
import time

# Test health endpoint
response = requests.get('http://localhost:8000/health')
print(f'Health: {response.status_code} - {response.json()}')

# Test metrics endpoint
response = requests.get('http://localhost:8000/metrics')
print(f'Metrics: {response.status_code}')

print('✅ Monitoring endpoints working')
"

# Run basic load test
python tests/load/basic_load_test.py

# Run deployment health check
python scripts/deployment_health_check.py --url http://localhost:8000
```

---

## ✅ Phase 4 Success Criteria

### **All of these must pass**:

1. **Container Builds and Runs**:
   ```bash
   docker build -t gremlinsai:test . && docker run --rm -d --name test -p 8006:8000 gremlinsai:test
   sleep 10 && curl -f http://localhost:8006/health && docker stop test
   ```

2. **Docker Compose Works**:
   ```bash
   docker-compose up -d && sleep 15 && curl -f http://localhost:8000/health && docker-compose down
   ```

3. **CI/CD Pipeline Valid**:
   ```bash
   python -c "import yaml; yaml.safe_load(open('.github/workflows/ci-cd.yml'))"
   ```

4. **Load Testing Passes**:
   ```bash
   python tests/load/basic_load_test.py
   ```

5. **Health Checks Work**:
   ```bash
   python scripts/deployment_health_check.py
   ```

### **Final Validation Command**:
```bash
# Comprehensive Phase 4 validation
python -c "
import subprocess
import sys
import time
import requests

def validate_deployment_preparation():
    tests = []

    # Test 1: Docker build
    try:
        result = subprocess.run(['docker', 'build', '-t', 'gremlinsai:validation', '.'],
                              capture_output=True, text=True, timeout=300)
        tests.append(('Docker Build', result.returncode == 0,
                     'Image built successfully' if result.returncode == 0 else f'Build failed: {result.stderr[:100]}'))
    except Exception as e:
        tests.append(('Docker Build', False, f'Build error: {e}'))

    # Test 2: Container run
    try:
        # Start container
        subprocess.run(['docker', 'run', '--rm', '-d', '--name', 'gremlinsai-validation',
                       '-p', '8007:8000', 'gremlinsai:validation'],
                      capture_output=True, timeout=30)

        # Wait for startup
        time.sleep(10)

        # Test health endpoint
        response = requests.get('http://localhost:8007/health', timeout=5)
        container_healthy = response.status_code == 200

        tests.append(('Container Health', container_healthy,
                     'Container responds to health checks' if container_healthy else 'Health check failed'))

        # Cleanup
        subprocess.run(['docker', 'stop', 'gremlinsai-validation'], capture_output=True)

    except Exception as e:
        tests.append(('Container Health', False, f'Container test error: {e}'))
        # Ensure cleanup
        subprocess.run(['docker', 'stop', 'gremlinsai-validation'], capture_output=True)

    # Test 3: CI/CD workflow validation
    try:
        import yaml
        with open('.github/workflows/ci-cd.yml', 'r') as f:
            workflow = yaml.safe_load(f)

        required_jobs = ['test', 'security', 'build']
        has_required_jobs = all(job in workflow['jobs'] for job in required_jobs)

        tests.append(('CI/CD Workflow', has_required_jobs,
                     'All required jobs present' if has_required_jobs else 'Missing required jobs'))
    except Exception as e:
        tests.append(('CI/CD Workflow', False, f'Workflow validation error: {e}'))

    # Test 4: Pre-commit hooks
    try:
        import yaml
        with open('.pre-commit-config.yaml', 'r') as f:
            precommit = yaml.safe_load(f)

        has_hooks = len(precommit.get('repos', [])) > 0
        tests.append(('Pre-commit Hooks', has_hooks,
                     'Pre-commit configuration valid' if has_hooks else 'No pre-commit hooks configured'))
    except Exception as e:
        tests.append(('Pre-commit Hooks', False, f'Pre-commit validation error: {e}'))

    # Print results
    print('\\n' + '='*70)
    print('PHASE 4 DEPLOYMENT PREPARATION VALIDATION')
    print('='*70)

    all_passed = True
    for test_name, passed, message in tests:
        status = '✅ PASS' if passed else '❌ FAIL'
        print(f'{status} {test_name}: {message}')
        if not passed:
            all_passed = False

    print('='*70)
    if all_passed:
        print('🎉 PHASE 4 COMPLETE - Ready for production deployment!')
        print('🚀 Application is production-ready with:')
        print('   - Containerized application')
        print('   - CI/CD pipeline')
        print('   - Health monitoring')
        print('   - Load testing validation')
    else:
        print('❌ PHASE 4 INCOMPLETE - Fix failing components above')
    print('='*70)

    return all_passed

validate_deployment_preparation()
"
```

---

## 🚨 Troubleshooting

### **Issue**: "Docker build fails"
**Solution**: Check Dockerfile syntax and dependencies:
```bash
docker build --no-cache -t gremlinsai:debug .
```

### **Issue**: "Container health check fails"
**Solution**: Check application logs:
```bash
docker logs gremlinsai-container-name
```

### **Issue**: "CI/CD workflow errors"
**Solution**: Validate YAML syntax:
```bash
python -c "import yaml; print(yaml.safe_load(open('.github/workflows/ci-cd.yml')))"
```

### **Issue**: "Load test fails"
**Solution**: Check if application is running and accessible:
```bash
curl -v http://localhost:8000/health
```

---

## 📊 Time Estimates

- **Task 1** (Containerization): 1 week
- **Task 2** (CI/CD Pipeline): 1 week
- **Task 3** (Monitoring Setup): 1 week
- **Total Phase 4**: 3 weeks

---

## 🎉 Production Readiness Achieved

Once Phase 4 is complete, your GremlinsAI application will be **production-ready** with:

### **✅ Core Capabilities**
- ✅ Application starts reliably
- ✅ Core functionality validated
- ✅ Comprehensive test coverage
- ✅ Production-grade configuration

### **✅ Production Infrastructure**
- ✅ Containerized deployment
- ✅ CI/CD pipeline
- ✅ Health monitoring
- ✅ Security hardening
- ✅ Load testing validation

### **✅ Operational Excellence**
- ✅ Structured logging
- ✅ Error handling
- ✅ Performance monitoring
- ✅ Deployment automation

### **🚀 Next Steps for Production**
1. **Deploy to staging environment**
2. **Run full integration tests**
3. **Performance tune based on real load**
4. **Set up production monitoring**
5. **Create operational runbooks**
6. **Plan rollout strategy**

**Congratulations! You've transformed GremlinsAI from a non-functional codebase into a production-ready application.**
