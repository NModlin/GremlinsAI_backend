# Phase 3: Production Hardening

## 🎯 Executive Summary

**Objective**: Implement production-grade configuration, monitoring, and security  
**Duration**: 3-4 weeks  
**Priority**: HIGH - Required for safe production deployment  
**Success Criteria**: Environment-specific configs work, basic monitoring operational, security fundamentals implemented, error handling robust

**Focus Areas**:
- Configuration management for multiple environments
- Basic monitoring and observability
- Security fundamentals (authentication, input validation)
- Error handling and logging
- Performance basics

---

## 📋 Prerequisites

**From Phase 2**:
- ✅ Agent system executes basic queries
- ✅ LLM integration works with fallback
- ✅ Database operations are reliable
- ✅ API endpoints respond without crashes

**Additional Requirements**:
- Core functionality validated and working
- Test infrastructure operational

---

## 🔧 Task 1: Configuration Management (1 week)

### **Step 1.1: Create Environment-Specific Configuration**

**File**: `app/core/config.py`

```python
"""
Production-grade configuration management
"""
import os
from typing import Optional, List
from pydantic import BaseSettings, Field
from enum import Enum

class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"

class DatabaseConfig(BaseSettings):
    """Database configuration"""
    url: str = Field(default="sqlite:///./data/gremlinsai.db", env="DATABASE_URL")
    echo: bool = Field(default=False, env="DATABASE_ECHO")
    pool_size: int = Field(default=5, env="DATABASE_POOL_SIZE")
    max_overflow: int = Field(default=10, env="DATABASE_MAX_OVERFLOW")

class LLMConfig(BaseSettings):
    """LLM configuration"""
    ollama_base_url: str = Field(default="http://localhost:11434", env="OLLAMA_BASE_URL")
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    default_model: str = Field(default="llama2", env="LLM_DEFAULT_MODEL")
    timeout: int = Field(default=30, env="LLM_TIMEOUT")
    max_retries: int = Field(default=3, env="LLM_MAX_RETRIES")

class RedisConfig(BaseSettings):
    """Redis configuration"""
    url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    max_connections: int = Field(default=10, env="REDIS_MAX_CONNECTIONS")
    socket_timeout: int = Field(default=5, env="REDIS_SOCKET_TIMEOUT")

class SecurityConfig(BaseSettings):
    """Security configuration"""
    secret_key: str = Field(..., env="SECRET_KEY")
    algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    allowed_hosts: List[str] = Field(default=["*"], env="ALLOWED_HOSTS")

class MonitoringConfig(BaseSettings):
    """Monitoring configuration"""
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=8001, env="METRICS_PORT")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    enable_tracing: bool = Field(default=False, env="ENABLE_TRACING")

class Settings(BaseSettings):
    """Main application settings"""
    
    # Environment
    environment: Environment = Field(default=Environment.DEVELOPMENT, env="ENV")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Application
    app_name: str = Field(default="GremlinsAI", env="APP_NAME")
    version: str = Field(default="1.0.0", env="APP_VERSION")
    api_prefix: str = Field(default="/api/v1", env="API_PREFIX")
    
    # Sub-configurations
    database: DatabaseConfig = DatabaseConfig()
    llm: LLMConfig = LLMConfig()
    redis: RedisConfig = RedisConfig()
    security: SecurityConfig = SecurityConfig()
    monitoring: MonitoringConfig = MonitoringConfig()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

# Global settings instance
settings = Settings()

def get_settings() -> Settings:
    """Get application settings"""
    return settings
```

### **Step 1.2: Create Environment Files**

**File**: `.env.development`

```bash
# Development Environment Configuration
ENV=development
DEBUG=true

# Database
DATABASE_URL=sqlite:///./data/gremlinsai_dev.db
DATABASE_ECHO=true

# LLM Configuration
OLLAMA_BASE_URL=http://localhost:11434
LLM_DEFAULT_MODEL=llama2
LLM_TIMEOUT=60

# Redis
REDIS_URL=redis://localhost:6379/0

# Security (development only - not secure)
SECRET_KEY=dev-secret-key-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Monitoring
LOG_LEVEL=DEBUG
ENABLE_METRICS=true
ENABLE_TRACING=false
```

**File**: `.env.staging`

```bash
# Staging Environment Configuration
ENV=staging
DEBUG=false

# Database
DATABASE_URL=sqlite:///./data/gremlinsai_staging.db
DATABASE_ECHO=false
DATABASE_POOL_SIZE=10

# LLM Configuration
OLLAMA_BASE_URL=http://ollama-staging:11434
LLM_TIMEOUT=30
LLM_MAX_RETRIES=3

# Redis
REDIS_URL=redis://redis-staging:6379/0
REDIS_MAX_CONNECTIONS=20

# Security
SECRET_KEY=${STAGING_SECRET_KEY}
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Monitoring
LOG_LEVEL=INFO
ENABLE_METRICS=true
ENABLE_TRACING=true
```

**File**: `.env.production`

```bash
# Production Environment Configuration
ENV=production
DEBUG=false

# Database
DATABASE_URL=${PRODUCTION_DATABASE_URL}
DATABASE_ECHO=false
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30

# LLM Configuration
OLLAMA_BASE_URL=${OLLAMA_PRODUCTION_URL}
OPENAI_API_KEY=${OPENAI_API_KEY}
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
LLM_TIMEOUT=30
LLM_MAX_RETRIES=2

# Redis
REDIS_URL=${REDIS_PRODUCTION_URL}
REDIS_MAX_CONNECTIONS=50

# Security
SECRET_KEY=${PRODUCTION_SECRET_KEY}
ACCESS_TOKEN_EXPIRE_MINUTES=15
ALLOWED_HOSTS=["yourdomain.com","api.yourdomain.com"]

# Monitoring
LOG_LEVEL=WARNING
ENABLE_METRICS=true
ENABLE_TRACING=true
```

### **Step 1.3: Update Application to Use Configuration**

**File**: `app/main.py` (modify to use config)

```python
# Add these imports at the top
from app.core.config import get_settings

# Add this after app creation
settings = get_settings()

# Configure app based on settings
app.title = settings.app_name
app.version = settings.version
app.debug = settings.debug

# Add configuration endpoint
@app.get("/config/info")
async def config_info():
    """Get non-sensitive configuration info"""
    return {
        "app_name": settings.app_name,
        "version": settings.version,
        "environment": settings.environment,
        "debug": settings.debug
    }
```

### **Step 1.4: Create Configuration Tests**

**File**: `tests/unit/test_configuration.py`

```python
"""
Configuration management tests
"""
import pytest
import os
from unittest.mock import patch

class TestConfiguration:
    """Test configuration management"""
    
    def test_settings_import(self):
        """Test settings can be imported"""
        from app.core.config import get_settings, Settings
        settings = get_settings()
        assert isinstance(settings, Settings)
    
    def test_default_configuration(self):
        """Test default configuration values"""
        from app.core.config import Settings
        settings = Settings()
        
        assert settings.app_name == "GremlinsAI"
        assert settings.version == "1.0.0"
        assert settings.database.url.startswith("sqlite:")
    
    @patch.dict(os.environ, {
        'ENV': 'testing',
        'DEBUG': 'true',
        'SECRET_KEY': 'test-secret-key',
        'DATABASE_URL': 'sqlite:///test.db'
    })
    def test_environment_override(self):
        """Test environment variable override"""
        from app.core.config import Settings
        settings = Settings()
        
        assert settings.environment == "testing"
        assert settings.debug == True
        assert settings.security.secret_key == "test-secret-key"
        assert settings.database.url == "sqlite:///test.db"
    
    def test_configuration_validation(self):
        """Test configuration validation"""
        from app.core.config import Settings
        
        # Test missing required field
        with pytest.raises(Exception):
            Settings(security={"secret_key": None})

class TestEnvironmentSpecificConfig:
    """Test environment-specific configurations"""
    
    @patch.dict(os.environ, {'ENV': 'development'})
    def test_development_config(self):
        """Test development configuration"""
        from app.core.config import get_settings
        settings = get_settings()
        
        assert settings.environment == "development"
        # Development should have debug enabled by default
    
    @patch.dict(os.environ, {'ENV': 'production'})
    def test_production_config(self):
        """Test production configuration"""
        from app.core.config import get_settings
        settings = get_settings()
        
        assert settings.environment == "production"
        # Production should have debug disabled
```

### **Validation Step 1**:
```bash
# Test configuration
python -m pytest tests/unit/test_configuration.py -v

# Test configuration loading
python -c "
from app.core.config import get_settings
settings = get_settings()
print(f'Environment: {settings.environment}')
print(f'Database URL: {settings.database.url}')
print(f'Debug: {settings.debug}')
print('✅ Configuration loaded successfully')
"
```

---

## 🔧 Task 2: Logging and Error Handling (1 week)

### **Step 2.1: Implement Structured Logging**

**File**: `app/core/logging_config.py`

```python
"""
Structured logging configuration
"""
import logging
import logging.config
import sys
import json
from datetime import datetime
from typing import Dict, Any
import uuid
from contextvars import ContextVar

# Context variable for correlation ID
correlation_id: ContextVar[str] = ContextVar('correlation_id', default='')

class CorrelationIdFilter(logging.Filter):
    """Add correlation ID to log records"""
    
    def filter(self, record):
        record.correlation_id = correlation_id.get('')
        return True

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'correlation_id': getattr(record, 'correlation_id', ''),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process', 'getMessage', 'exc_info', 
                          'exc_text', 'stack_info', 'correlation_id']:
                log_entry[key] = value
        
        return json.dumps(log_entry)

def setup_logging(log_level: str = "INFO", enable_json: bool = False):
    """Setup application logging"""
    
    # Clear existing handlers
    logging.getLogger().handlers.clear()
    
    # Create formatter
    if enable_json:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(correlation_id)s - %(message)s'
        )
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(CorrelationIdFilter())
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        handlers=[console_handler]
    )
    
    # Set specific logger levels
    logging.getLogger('uvicorn').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

def get_correlation_id() -> str:
    """Get current correlation ID"""
    return correlation_id.get('')

def set_correlation_id(cid: str = None) -> str:
    """Set correlation ID for current context"""
    if cid is None:
        cid = str(uuid.uuid4())
    correlation_id.set(cid)
    return cid

def get_logger(name: str) -> logging.Logger:
    """Get logger with correlation ID support"""
    return logging.getLogger(name)
```

### **Step 2.2: Implement Error Handling Middleware**

**File**: `app/middleware/error_handling.py`

```python
"""
Error handling middleware
"""
import logging
import traceback
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logging_config import get_logger, set_correlation_id

logger = get_logger(__name__)

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Global error handling middleware"""
    
    async def dispatch(self, request: Request, call_next):
        # Set correlation ID for request
        correlation_id = set_correlation_id()
        
        try:
            # Add correlation ID to request state
            request.state.correlation_id = correlation_id
            
            # Process request
            response = await call_next(request)
            
            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id
            
            return response
            
        except HTTPException as e:
            # Handle HTTP exceptions
            logger.warning(
                f"HTTP exception: {e.status_code} - {e.detail}",
                extra={
                    "status_code": e.status_code,
                    "detail": e.detail,
                    "path": request.url.path,
                    "method": request.method
                }
            )
            
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": e.detail,
                    "status_code": e.status_code,
                    "correlation_id": correlation_id
                },
                headers={"X-Correlation-ID": correlation_id}
            )
            
        except Exception as e:
            # Handle unexpected exceptions
            logger.error(
                f"Unhandled exception: {str(e)}",
                extra={
                    "exception_type": type(e).__name__,
                    "traceback": traceback.format_exc(),
                    "path": request.url.path,
                    "method": request.method
                }
            )
            
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "status_code": 500,
                    "correlation_id": correlation_id
                },
                headers={"X-Correlation-ID": correlation_id}
            )

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Request/response logging middleware"""
    
    async def dispatch(self, request: Request, call_next):
        # Log request
        logger.info(
            f"Request: {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_ip": request.client.host if request.client else None
            }
        )
        
        # Process request
        response = await call_next(request)
        
        # Log response
        logger.info(
            f"Response: {response.status_code}",
            extra={
                "status_code": response.status_code,
                "path": request.url.path,
                "method": request.method
            }
        )
        
        return response
```

### **Step 2.3: Update Main Application**

**File**: `app/main.py` (add middleware)

```python
# Add these imports
from app.middleware.error_handling import ErrorHandlingMiddleware, RequestLoggingMiddleware
from app.core.logging_config import setup_logging
from app.core.config import get_settings

# Setup logging
settings = get_settings()
setup_logging(
    log_level=settings.monitoring.log_level,
    enable_json=(settings.environment == "production")
)

# Add middleware
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(RequestLoggingMiddleware)
```

### **Validation Step 2**:
```bash
# Test logging and error handling
python -c "
from app.core.logging_config import get_logger, set_correlation_id
logger = get_logger('test')

# Test correlation ID
cid = set_correlation_id()
logger.info('Test log message')
print(f'✅ Logging configured with correlation ID: {cid}')
"

# Test error handling
python -m pytest tests/unit/test_error_handling.py -v
```

---

## 🔧 Task 3: Basic Security Implementation (1 week)

### **Step 3.1: Input Validation and Sanitization**

**File**: `app/core/security.py`

```python
"""
Security utilities and validation
"""
import re
import html
import logging
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

class SecurityValidator:
    """Security validation utilities"""
    
    # Dangerous patterns
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
        r"(--|#|/\*|\*/)",
        r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
        r"(\bOR\s+\d+\s*=\s*\d+)",
    ]
    
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>.*?</iframe>",
    ]
    
    COMMAND_INJECTION_PATTERNS = [
        r"[;&|`$(){}[\]\\]",
        r"\b(rm|del|format|shutdown|reboot)\b",
    ]
    
    @classmethod
    def validate_input(cls, value: str, field_name: str = "input") -> str:
        """Validate and sanitize input"""
        if not isinstance(value, str):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Field '{field_name}' must be a string"
            )
        
        # Length validation
        if len(value) > 10000:  # 10KB limit
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Field '{field_name}' exceeds maximum length"
            )
        
        # Check for SQL injection
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                logger.warning(f"SQL injection attempt detected in {field_name}: {value[:100]}")
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Invalid input detected"
                )
        
        # Check for XSS
        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                logger.warning(f"XSS attempt detected in {field_name}: {value[:100]}")
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Invalid input detected"
                )
        
        # Check for command injection
        for pattern in cls.COMMAND_INJECTION_PATTERNS:
            if re.search(pattern, value):
                logger.warning(f"Command injection attempt detected in {field_name}: {value[:100]}")
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Invalid input detected"
                )
        
        # Sanitize HTML
        sanitized = html.escape(value)
        
        return sanitized
    
    @classmethod
    def validate_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate dictionary input"""
        validated = {}
        
        for key, value in data.items():
            # Validate key
            safe_key = cls.validate_input(str(key), f"key_{key}")
            
            # Validate value
            if isinstance(value, str):
                validated[safe_key] = cls.validate_input(value, key)
            elif isinstance(value, dict):
                validated[safe_key] = cls.validate_dict(value)
            elif isinstance(value, list):
                validated[safe_key] = [
                    cls.validate_input(str(item), f"{key}[{i}]") if isinstance(item, str) else item
                    for i, item in enumerate(value)
                ]
            else:
                validated[safe_key] = value
        
        return validated

def sanitize_input(value: str) -> str:
    """Sanitize input string"""
    return SecurityValidator.validate_input(value)

def validate_request_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate request data"""
    return SecurityValidator.validate_dict(data)
```

### **Step 3.2: Rate Limiting**

**File**: `app/middleware/rate_limiting.py`

```python
"""
Rate limiting middleware
"""
import time
from collections import defaultdict, deque
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting middleware"""
    
    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls  # Number of calls allowed
        self.period = period  # Time period in seconds
        self.clients = defaultdict(deque)  # Client IP -> timestamps
    
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        
        # Clean old entries
        client_calls = self.clients[client_ip]
        while client_calls and client_calls[0] < current_time - self.period:
            client_calls.popleft()
        
        # Check rate limit
        if len(client_calls) >= self.calls:
            logger.warning(f"Rate limit exceeded for client {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded"
            )
        
        # Add current request
        client_calls.append(current_time)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.calls)
        response.headers["X-RateLimit-Remaining"] = str(self.calls - len(client_calls))
        response.headers["X-RateLimit-Reset"] = str(int(current_time + self.period))
        
        return response
```

### **Step 3.3: Security Headers Middleware**

**File**: `app/middleware/security_headers.py`

```python
"""
Security headers middleware
"""
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to responses"""
    
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response
```

### **Validation Step 3**:
```bash
# Test security features
python -c "
from app.core.security import sanitize_input, validate_request_data

# Test input sanitization
safe_input = sanitize_input('Hello <script>alert(\"xss\")</script> World')
print(f'Sanitized input: {safe_input}')

# Test data validation
safe_data = validate_request_data({'query': 'SELECT * FROM users', 'name': 'test'})
print('✅ Security validation working')
"
```

---

## ✅ Phase 3 Success Criteria

### **All of these must pass**:

1. **Configuration Management**:
   ```bash
   python -m pytest tests/unit/test_configuration.py -v
   ```

2. **Logging and Error Handling**:
   ```bash
   python -c "from app.core.logging_config import get_logger; logger = get_logger('test'); logger.info('Test'); print('✅ Logging works')"
   ```

3. **Security Features**:
   ```bash
   python -c "from app.core.security import sanitize_input; print('✅ Security validation works')"
   ```

4. **Application Starts with All Middleware**:
   ```bash
   timeout 5s uvicorn app.main:app --port 8003 && echo "✅ App starts with middleware"
   ```

### **Final Validation Command**:
```bash
# Comprehensive Phase 3 validation
python -c "
import subprocess
import sys
import time

def validate_production_hardening():
    tests = []
    
    # Test 1: Configuration
    try:
        from app.core.config import get_settings
        settings = get_settings()
        tests.append(('Configuration', True, f'Environment: {settings.environment}'))
    except Exception as e:
        tests.append(('Configuration', False, f'Config error: {e}'))
    
    # Test 2: Logging
    try:
        from app.core.logging_config import get_logger, set_correlation_id
        logger = get_logger('test')
        cid = set_correlation_id()
        logger.info('Test message')
        tests.append(('Logging', True, f'Correlation ID: {cid[:8]}...'))
    except Exception as e:
        tests.append(('Logging', False, f'Logging error: {e}'))
    
    # Test 3: Security
    try:
        from app.core.security import sanitize_input
        result = sanitize_input('test<script>alert(1)</script>')
        tests.append(('Security', True, 'Input sanitization works'))
    except Exception as e:
        tests.append(('Security', False, f'Security error: {e}'))
    
    # Test 4: Application startup
    try:
        proc = subprocess.Popen([
            sys.executable, '-m', 'uvicorn', 
            'app.main:app', '--host', '127.0.0.1', '--port', '8004'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        time.sleep(3)
        
        if proc.poll() is None:
            tests.append(('App Startup', True, 'App starts with middleware'))
            proc.terminate()
            proc.wait()
        else:
            stdout, stderr = proc.communicate()
            tests.append(('App Startup', False, f'Startup failed: {stderr.decode()[:100]}'))
    except Exception as e:
        tests.append(('App Startup', False, f'Startup test error: {e}'))
    
    # Print results
    print('\\n' + '='*70)
    print('PHASE 3 PRODUCTION HARDENING VALIDATION')
    print('='*70)
    
    all_passed = True
    for test_name, passed, message in tests:
        status = '✅ PASS' if passed else '❌ FAIL'
        print(f'{status} {test_name}: {message}')
        if not passed:
            all_passed = False
    
    print('='*70)
    if all_passed:
        print('🎉 PHASE 3 COMPLETE - Production hardening implemented!')
        print('Ready for Phase 4: Deployment Preparation')
    else:
        print('❌ PHASE 3 INCOMPLETE - Fix failing components above')
    print('='*70)
    
    return all_passed

validate_production_hardening()
"
```

---

## 🚨 Troubleshooting

### **Issue**: "Configuration validation errors"
**Solution**: Check environment variables and .env files

### **Issue**: "Logging not working"
**Solution**: Check log level and permissions

### **Issue**: "Security validation too strict"
**Solution**: Adjust patterns in security.py

### **Issue**: "Rate limiting blocking legitimate requests"
**Solution**: Increase limits or implement IP whitelist

---

## 📊 Time Estimates

- **Task 1** (Configuration): 1 week
- **Task 2** (Logging/Error Handling): 1 week
- **Task 3** (Security): 1 week
- **Total Phase 3**: 3-4 weeks

---

## ➡️ Next Phase

Once Phase 3 is complete, proceed to `phase_4_deployment_preparation.md`

**Prerequisites for Phase 4**:
- ✅ Environment-specific configuration working
- ✅ Structured logging and error handling operational
- ✅ Basic security measures implemented
- ✅ Application runs with all middleware
