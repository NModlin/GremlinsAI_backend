# Local LLM Setup Guide for GremlinsAI

This guide will help you configure GremlinsAI to use local Large Language Models (LLMs) instead of cloud-based APIs like OpenAI. This enables completely offline operation without requiring API keys or internet connectivity.

## 🎯 Overview

GremlinsAI now supports multiple local LLM providers:

- **Ollama** (Recommended) - Easy setup, great performance
- **Hugging Face Transformers** - Direct model loading
- **LlamaCpp** - GGUF model support
- **Mock LLM** - Development/testing fallback

## 🚀 Quick Start with Ollama (Recommended)

### 1. Install Ollama

**Windows:**
```bash
# Download and install from https://ollama.ai/download
# Or use winget
winget install Ollama.Ollama
```

**macOS:**
```bash
# Download from https://ollama.ai/download
# Or use Homebrew
brew install ollama
```

**Linux:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

### 2. Start Ollama Service

```bash
# Start Ollama (runs on http://localhost:11434 by default)
ollama serve
```

### 3. Download a Model

```bash
# Recommended models for GremlinsAI:

# Small, fast model (3B parameters) - Good for development
ollama pull llama3.2:3b

# Medium model (8B parameters) - Better quality
ollama pull llama3.2:8b

# Code-focused model
ollama pull codellama:7b

# Mistral model (good alternative)
ollama pull mistral:7b
```

### 4. Configure GremlinsAI

Update your `.env` file:
```bash
# Ollama Configuration
OLLAMA_BASE_URL="http://localhost:11434"
OLLAMA_MODEL="llama3.2:3b"
```

### 5. Install Dependencies

```bash
pip install langchain-ollama
```

## 🤗 Hugging Face Transformers Setup

### 1. Install Dependencies

```bash
pip install transformers accelerate torch
```

### 2. Configure Environment

```bash
# Enable Hugging Face
USE_HUGGINGFACE="true"
HF_MODEL="microsoft/DialoGPT-medium"

# For larger models, you might want:
# HF_MODEL="microsoft/DialoGPT-large"
# HF_MODEL="facebook/blenderbot-400M-distill"
```

### 3. GPU Support (Optional)

For better performance with GPU:
```bash
# Install CUDA version of PyTorch
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

## 🦙 LlamaCpp Setup (GGUF Models)

### 1. Install Dependencies

```bash
pip install llama-cpp-python
```

### 2. Download GGUF Models

```bash
# Create models directory
mkdir -p ./models

# Download models from Hugging Face (example)
# You can find GGUF models at: https://huggingface.co/models?search=gguf
```

### 3. Configure Environment

```bash
LLAMACPP_MODEL_PATH="./models/llama-2-7b-chat.gguf"
```

## 📋 Model Recommendations

### For Development/Testing:
- **Ollama: llama3.2:3b** - Fast, lightweight
- **HF: microsoft/DialoGPT-medium** - Good for chat

### For Production:
- **Ollama: llama3.2:8b** - Better quality responses
- **Ollama: mistral:7b** - Excellent reasoning
- **Ollama: codellama:7b** - Code-focused tasks

### For Document Analysis:
- **Ollama: llama3.2:8b** - Good comprehension
- **Ollama: mistral:7b** - Strong analytical capabilities

## 🔧 Configuration Options

### Environment Variables

```bash
# LLM Provider Selection (auto-detected)
# Priority: OpenAI > Ollama > Hugging Face > Mock

# Ollama Settings
OLLAMA_BASE_URL="http://localhost:11434"
OLLAMA_MODEL="llama3.2:3b"

# Hugging Face Settings
USE_HUGGINGFACE="false"
HF_MODEL="microsoft/DialoGPT-medium"

# LlamaCpp Settings
LLAMACPP_MODEL_PATH="./models/model.gguf"

# General LLM Settings
LLM_TEMPERATURE="0.1"        # Creativity (0.0-1.0)
LLM_MAX_TOKENS="2048"        # Response length
```

## 🧪 Testing Your Setup

### 1. Check LLM Status

```python
from app.core.llm_config import get_llm_info

info = get_llm_info()
print(f"Provider: {info['provider']}")
print(f"Model: {info['model_name']}")
print(f"Available: {info['available']}")
```

### 2. Test Basic Chat

```bash
# Start the backend
uvicorn app.main:app --reload

# Test via API
curl -X POST "http://localhost:8000/api/v1/agent/invoke" \
     -H "Content-Type: application/json" \
     -d '{"input": "Hello, how are you?"}'
```

## 🚨 Troubleshooting

### Ollama Issues

**Service not running:**
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama service
ollama serve
```

**Model not found:**
```bash
# List available models
ollama list

# Pull the model
ollama pull llama3.2:3b
```

### Memory Issues

**For large models:**
- Use smaller models (3B instead of 8B)
- Enable GPU acceleration
- Increase system RAM/swap

### Performance Optimization

**Ollama:**
- Use GPU acceleration if available
- Adjust `OLLAMA_NUM_PARALLEL` for concurrent requests
- Use SSD storage for models

**Hugging Face:**
- Enable GPU with CUDA
- Use model quantization
- Implement model caching

## 📊 Performance Comparison

| Provider | Setup Difficulty | Performance | Memory Usage | Best For |
|----------|------------------|-------------|--------------|----------|
| Ollama | Easy | Excellent | Medium | General use |
| Hugging Face | Medium | Good | High | Customization |
| LlamaCpp | Hard | Excellent | Low | Resource-constrained |

## 🔄 Switching Between Providers

GremlinsAI automatically detects the best available provider:

1. **OpenAI** (if API key is set)
2. **Ollama** (if service is running)
3. **Hugging Face** (if enabled)
4. **Mock** (fallback for development)

To force a specific provider, set the appropriate environment variables.

## 🎯 Next Steps

1. Choose your preferred LLM provider
2. Install and configure the provider
3. Update your `.env` file
4. Restart GremlinsAI backend
5. Test the integration
6. Optimize for your use case

For more advanced configurations and custom model integration, see the [Advanced LLM Configuration Guide](./ADVANCED_LLM_CONFIG.md).
