# 🚀 GremlinsAI Local LLM Quick Start Guide

This guide will help you set up GremlinsAI with a working local LLM in under 10 minutes.

## 🎯 The Problem

By default, GremlinsAI uses **mock responses** instead of real AI. You'll see responses like:
```
🚨 GREMLINS AI - NO REAL LLM CONFIGURED 🚨
Mock response: Please configure a real LLM provider to get actual AI responses.
```

## ✅ Quick Fix (Recommended): Ollama Setup

### Step 1: Install Ollama
```bash
# On Linux/Mac
curl -fsSL https://ollama.ai/install.sh | sh

# On Windows
# Download from: https://ollama.ai/download
```

### Step 2: Pull a Model
```bash
# Pull a lightweight model (3GB)
ollama pull llama3.2:3b

# Or a more capable model (4.7GB)
ollama pull llama3.2:7b
```

### Step 3: Start Ollama Service
```bash
ollama serve
```

### Step 4: Set Up Weaviate Vector Database
```bash
# Set up Weaviate for RAG capabilities
python scripts/setup_weaviate.py
```

### Step 5: Configure GremlinsAI
Create a `.env` file in the project root:
```env
# LLM Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=2048

# Weaviate Vector Database
WEAVIATE_URL=http://localhost:8080
WEAVIATE_CLASS_NAME=GremlinsDocument
EMBEDDING_MODEL=all-MiniLM-L6-v2
USE_CLIP=true
```

### Step 6: Verify Setup
```bash
# Run validation script
python scripts/validate_setup.py

# Or start the server and check health
uvicorn app.main:app --reload
# Visit: http://localhost:8000/api/v1/health/health
```

## 🔧 Alternative Options

### Option 2: OpenAI (Cloud-based)
```env
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-3.5-turbo
```

### Option 3: HuggingFace (Local)
```bash
pip install transformers torch accelerate
```
```env
USE_HUGGINGFACE=true
HF_MODEL=microsoft/DialoGPT-medium
```

## 🚨 Troubleshooting

### "Ollama service not responding"
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not, start it
ollama serve
```

### "No models installed"
```bash
# List installed models
ollama list

# Pull a model if none exist
ollama pull llama3.2:3b
```

### "Mock responses still appearing"
1. Check your `.env` file exists and has correct values
2. Restart the GremlinsAI server
3. Run the validation script: `python scripts/validate_setup.py`

## 🧪 Testing Your Setup

### Test 1: Health Check
```bash
curl http://localhost:8000/api/v1/health/health
```

### Test 2: Agent Query
```bash
curl -X POST http://localhost:8000/api/v1/agent/invoke \
  -H "Content-Type: application/json" \
  -d '{"input": "What is artificial intelligence?"}'
```

### Test 3: Multi-Agent Query
```bash
curl -X POST "http://localhost:8000/api/v1/agent/chat?use_multi_agent=true" \
  -H "Content-Type: application/json" \
  -d '{"input": "Explain renewable energy", "save_conversation": false}'
```

## 📊 Expected Results

### ❌ Before (Mock Response)
```json
{
  "output": "🚨 GREMLINS AI - NO REAL LLM CONFIGURED 🚨\n\nTo enable real AI capabilities..."
}
```

### ✅ After (Real LLM Response)
```json
{
  "output": "Artificial intelligence (AI) refers to the simulation of human intelligence in machines that are programmed to think and learn like humans..."
}
```

## 🎉 Success Indicators

- ✅ Server logs show: `LLM Available: True`
- ✅ Health endpoint shows: `"status": "healthy"`
- ✅ Agent responses are contextual and intelligent
- ✅ No more "mock response" messages

## 🆘 Need Help?

1. **Run the automated setup**: `python scripts/setup_local_llm.py`
2. **Check validation**: `python scripts/validate_setup.py`
3. **View health status**: Visit `http://localhost:8000/api/v1/health/health`
4. **Check server logs** for detailed error messages

## 📈 Performance Tips

- **llama3.2:3b**: Fast, good for development (3GB RAM)
- **llama3.2:7b**: Better quality, slower (8GB RAM)
- **Adjust temperature**: Lower = more focused, Higher = more creative
- **Increase max_tokens**: For longer responses

---

**🎯 Goal**: Transform GremlinsAI from a search wrapper into a real AI assistant in under 10 minutes!
