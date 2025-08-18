# Phase 0: Foundation Repair

## 🎯 Executive Summary

**Objective**: Fix critical blockers preventing the application from starting  
**Duration**: 1-2 weeks  
**Priority**: CRITICAL - Nothing else can proceed until this is complete  
**Success Criteria**: Application starts without errors and basic health endpoint responds

**Current Issues**:
- Application fails to start due to missing dependencies
- Import errors throughout the codebase
- Pydantic field_validator issues
- OpenTelemetry Jaeger exporter missing

---

## 📋 Prerequisites

- Python 3.11+ installed
- Git repository cloned locally
- Terminal/command prompt access
- Text editor or IDE

---

## 🔧 Task 1: Dependency Resolution (2-4 hours)

### **Step 1.1: Audit Current Dependencies**

```bash
# Navigate to project root
cd /path/to/GremlinsAI_backend

# Check current Python version
python --version

# Create backup of current requirements
cp requirements.txt requirements.txt.backup

# Check what's currently installed
pip list > current_installed_packages.txt

# Check for security vulnerabilities (optional but recommended)
pip install pip-audit
pip-audit
```

### **Step 1.2: Install Missing Critical Dependencies**

Create a new file `requirements-missing.txt`:

```txt
# Missing critical dependencies identified during analysis
opentelemetry-exporter-jaeger-thrift==1.21.0
opentelemetry-exporter-jaeger==1.21.0
locust==2.17.0
testcontainers[compose]==3.7.1
redis==5.0.1
pytest-asyncio==0.23.2
httpx==0.25.2
```

Install missing dependencies:

```bash
# Install missing dependencies
pip install -r requirements-missing.txt

# Update main requirements file
pip freeze > requirements-new.txt

# Compare with original
diff requirements.txt requirements-new.txt
```

### **Step 1.3: Create Development Requirements**

Create `requirements-dev.txt`:

```txt
# Development and testing dependencies
pytest==7.4.3
pytest-cov==4.1.0
pytest-asyncio==0.23.2
pytest-mock==3.12.0
black==23.11.0
flake8==6.1.0
mypy==1.7.1
pre-commit==3.5.0
locust==2.17.0
testcontainers[compose]==3.7.1
pip-audit==2.6.1
```

Install development dependencies:

```bash
pip install -r requirements-dev.txt
```

### **Validation Step 1**:
```bash
# Test basic imports
python -c "import opentelemetry.exporter.jaeger.thrift; print('✅ Jaeger exporter available')"
python -c "import locust; print('✅ Locust available')"
python -c "import testcontainers; print('✅ Testcontainers available')"
```

---

## 🔧 Task 2: Fix Import Errors (1-2 hours)

### **Step 2.1: Fix Pydantic field_validator Issues**

**File**: `app/api/v1/schemas/multi_agent.py`

Current broken code (around line 53):
```python
@field_validator('input')  # NameError: name 'field_validator' is not defined
```

**Fix**: Add proper import at the top of the file:

```python
# Find this line (around line 1-10):
from pydantic import BaseModel

# Replace with:
from pydantic import BaseModel, field_validator
```

Complete fixed file header should look like:

```python
"""
Multi-agent request and response schemas for GremlinsAI API
"""

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, field_validator, Field
from enum import Enum

# Rest of the file remains the same...
```

### **Step 2.2: Fix OpenTelemetry Import Issues**

**File**: `app/core/tracing_service.py` (line 27)

Current broken import:
```python
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
```

**Fix**: Update the import to use the correct package:

```python
# Replace the broken import with:
try:
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    JAEGER_AVAILABLE = True
except ImportError:
    # Fallback for development
    JAEGER_AVAILABLE = False
    class JaegerExporter:
        def __init__(self, *args, **kwargs):
            pass
```

### **Step 2.3: Identify and Fix Additional Import Issues**

Run this command to find all import issues:

```bash
# Find all Python files with potential import issues
python -c "
import ast
import os
import sys

def check_imports(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        ast.parse(content)
        return True
    except SyntaxError as e:
        print(f'❌ Syntax error in {file_path}: {e}')
        return False
    except Exception as e:
        print(f'⚠️  Issue in {file_path}: {e}')
        return False

for root, dirs, files in os.walk('app'):
    for file in files:
        if file.endswith('.py'):
            file_path = os.path.join(root, file)
            check_imports(file_path)
"
```

### **Validation Step 2**:
```bash
# Test that problematic files can now be imported
python -c "from app.api.v1.schemas.multi_agent import MultiAgentRequest; print('✅ Multi-agent schema imports')"
python -c "from app.core.tracing_service import tracing_service; print('✅ Tracing service imports')"
```

---

## 🔧 Task 3: Application Startup Validation (30 minutes)

### **Step 3.1: Test Basic Application Import**

```bash
# Test basic app module import
python -c "
try:
    import app
    print('✅ App module imports successfully')
except Exception as e:
    print(f'❌ App module import failed: {e}')
"
```

### **Step 3.2: Test FastAPI Application Import**

```bash
# Test FastAPI app import
python -c "
try:
    from app.main import app
    print('✅ FastAPI app imports successfully')
    print(f'App type: {type(app)}')
except Exception as e:
    print(f'❌ FastAPI app import failed: {e}')
"
```

### **Step 3.3: Test Application Startup**

```bash
# Test full application startup (run in background)
timeout 10s uvicorn app.main:app --host 0.0.0.0 --port 8000 &
APP_PID=$!

# Wait a moment for startup
sleep 3

# Test if app is responding
if curl -f http://localhost:8000/health 2>/dev/null; then
    echo "✅ Application started and health endpoint responds"
else
    echo "❌ Application startup failed or health endpoint not responding"
fi

# Clean up
kill $APP_PID 2>/dev/null || true
```

### **Validation Step 3**:
```bash
# Final validation script
python -c "
import sys
import subprocess
import time

def test_app_startup():
    try:
        # Test import
        from app.main import app
        print('✅ 1. App imports successfully')
        
        # Test app object
        if app is not None:
            print('✅ 2. App object created')
        else:
            print('❌ 2. App object is None')
            return False
            
        # Test startup (brief)
        proc = subprocess.Popen([
            sys.executable, '-m', 'uvicorn', 
            'app.main:app', '--host', '127.0.0.1', '--port', '8001'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        time.sleep(2)  # Give it time to start
        
        if proc.poll() is None:  # Still running
            print('✅ 3. App starts without immediate crash')
            proc.terminate()
            proc.wait()
            return True
        else:
            stdout, stderr = proc.communicate()
            print(f'❌ 3. App crashed on startup: {stderr.decode()}')
            return False
            
    except Exception as e:
        print(f'❌ Startup test failed: {e}')
        return False

if test_app_startup():
    print('\\n🎉 Phase 0 SUCCESS: Application foundation is repaired!')
else:
    print('\\n❌ Phase 0 FAILED: Issues remain to be fixed')
"
```

---

## 🔧 Task 4: Environment Setup (30 minutes)

### **Step 4.1: Create Environment Configuration**

Create `.env.example`:

```bash
# Database Configuration
DATABASE_URL=sqlite:///./data/gremlinsai.db
TEST_DATABASE_URL=sqlite:///./data/test_gremlinsai.db

# LLM Configuration
OLLAMA_BASE_URL=http://localhost:11434
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here

# Redis Configuration
REDIS_URL=redis://localhost:6379

# Application Configuration
ENV=development
DEBUG=true
LOG_LEVEL=INFO

# Security
SECRET_KEY=your_secret_key_here
```

### **Step 4.2: Create Local Environment File**

```bash
# Copy example to actual .env file
cp .env.example .env

# Generate a secret key
python -c "
import secrets
import string

# Generate a secure secret key
key = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(50))
print(f'Generated SECRET_KEY: {key}')

# Update .env file
with open('.env', 'r') as f:
    content = f.read()

content = content.replace('your_secret_key_here', key)

with open('.env', 'w') as f:
    f.write(content)

print('✅ .env file updated with secure secret key')
"
```

---

## ✅ Phase 0 Success Criteria

### **All of these must pass**:

1. **Dependencies Installed**:
   ```bash
   python -c "import opentelemetry.exporter.jaeger.thrift, locust, testcontainers; print('✅ All dependencies available')"
   ```

2. **Import Errors Fixed**:
   ```bash
   python -c "from app.api.v1.schemas.multi_agent import MultiAgentRequest; print('✅ Schema imports work')"
   ```

3. **Application Starts**:
   ```bash
   timeout 5s uvicorn app.main:app --port 8002 && echo "✅ App starts successfully"
   ```

4. **Environment Configured**:
   ```bash
   test -f .env && echo "✅ Environment file exists"
   ```

### **Final Validation Command**:
```bash
# Run this comprehensive test
python -c "
import subprocess
import sys
import time

def comprehensive_test():
    tests = []
    
    # Test 1: Dependencies
    try:
        import opentelemetry.exporter.jaeger.thrift
        import locust
        import testcontainers
        tests.append(('Dependencies', True, 'All critical dependencies available'))
    except ImportError as e:
        tests.append(('Dependencies', False, f'Missing dependency: {e}'))
    
    # Test 2: App Import
    try:
        from app.main import app
        tests.append(('App Import', True, 'FastAPI app imports successfully'))
    except Exception as e:
        tests.append(('App Import', False, f'Import failed: {e}'))
    
    # Test 3: Environment
    import os
    if os.path.exists('.env'):
        tests.append(('Environment', True, '.env file exists'))
    else:
        tests.append(('Environment', False, '.env file missing'))
    
    # Print results
    print('\\n' + '='*60)
    print('PHASE 0 VALIDATION RESULTS')
    print('='*60)
    
    all_passed = True
    for test_name, passed, message in tests:
        status = '✅ PASS' if passed else '❌ FAIL'
        print(f'{status} {test_name}: {message}')
        if not passed:
            all_passed = False
    
    print('='*60)
    if all_passed:
        print('🎉 PHASE 0 COMPLETE - Ready for Phase 1!')
    else:
        print('❌ PHASE 0 INCOMPLETE - Fix failing tests above')
    print('='*60)
    
    return all_passed

comprehensive_test()
"
```

---

## 🚨 Troubleshooting

### **Issue**: "ModuleNotFoundError: No module named 'opentelemetry.exporter.jaeger'"
**Solution**: 
```bash
pip install opentelemetry-exporter-jaeger-thrift==1.21.0
```

### **Issue**: "NameError: name 'field_validator' is not defined"
**Solution**: Add import to affected files:
```python
from pydantic import BaseModel, field_validator
```

### **Issue**: Application starts but crashes immediately
**Solution**: Check logs and fix configuration:
```bash
uvicorn app.main:app --log-level debug
```

### **Issue**: Permission errors on Windows
**Solution**: Run terminal as administrator or use virtual environment

---

## 📊 Time Estimates

- **Task 1** (Dependencies): 2-4 hours
- **Task 2** (Import Fixes): 1-2 hours  
- **Task 3** (Startup Validation): 30 minutes
- **Task 4** (Environment Setup): 30 minutes
- **Total Phase 0**: 4-7 hours

---

## ➡️ Next Phase

Once Phase 0 is complete, proceed to `phase_1_testing_infrastructure.md`

**Prerequisites for Phase 1**:
- ✅ Application starts without errors
- ✅ All dependencies installed
- ✅ Import errors resolved
- ✅ Environment configured
