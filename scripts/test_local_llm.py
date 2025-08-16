#!/usr/bin/env python3
"""
Test script for local LLM configuration in GremlinsAI.

This script tests the local LLM setup and provides diagnostic information.
"""

import sys
import os
import requests
import json
from pathlib import Path

def test_environment():
    """Test environment configuration."""
    print("🔧 Testing Environment Configuration...")
    
    # Check if .env file exists
    if os.path.exists('.env'):
        print("✅ .env file found")
        
        # Read and display relevant settings
        with open('.env', 'r') as f:
            content = f.read()
            
        for line in content.split('\n'):
            if line.startswith(('OLLAMA_', 'LLM_', 'USE_HUGGINGFACE')):
                print(f"   {line}")
    else:
        print("❌ .env file not found - run setup_local_llm.py first")
        return False
    
    return True

def test_ollama_service():
    """Test Ollama service connectivity."""
    print("\n🔧 Testing Ollama Service...")
    
    try:
        response = requests.get('http://localhost:11434/api/tags', timeout=5)
        if response.status_code == 200:
            print("✅ Ollama service is running")
            
            data = response.json()
            models = data.get('models', [])
            
            if models:
                print("✅ Available models:")
                for model in models:
                    print(f"   - {model['name']}")
            else:
                print("⚠️  No models installed")
                print("   Run: ollama pull llama3.2:3b")
            
            return True
        else:
            print(f"❌ Ollama service returned status {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Ollama service")
        print("   Make sure Ollama is running: ollama serve")
        return False
    except Exception as e:
        print(f"❌ Error testing Ollama: {e}")
        return False

def test_llm_config():
    """Test LLM configuration module."""
    print("\n🔧 Testing LLM Configuration Module...")
    
    try:
        # Add current directory to path
        sys.path.insert(0, '.')
        
        from app.core.llm_config import get_llm_info, get_llm, LLMProvider
        
        # Get LLM info
        info = get_llm_info()
        print("✅ LLM configuration loaded successfully")
        print(f"   Provider: {info['provider']}")
        print(f"   Model: {info['model_name']}")
        print(f"   Temperature: {info['temperature']}")
        print(f"   Max Tokens: {info['max_tokens']}")
        print(f"   Available: {info['available']}")
        
        if info['provider'] == 'ollama' and info['base_url']:
            print(f"   Base URL: {info['base_url']}")
        
        # Try to create LLM instance
        try:
            llm = get_llm()
            print("✅ LLM instance created successfully")
            
            if info['provider'] != 'mock':
                print("✅ Real LLM provider configured")
            else:
                print("⚠️  Using mock LLM provider")
                
        except Exception as e:
            print(f"❌ Failed to create LLM instance: {e}")
            return False
            
        return True
        
    except ImportError as e:
        print(f"❌ Failed to import LLM configuration: {e}")
        print("   Make sure you're in the GremlinsAI backend directory")
        return False
    except Exception as e:
        print(f"❌ Error testing LLM configuration: {e}")
        return False

def test_api_endpoint():
    """Test the GremlinsAI API endpoint."""
    print("\n🔧 Testing GremlinsAI API...")
    
    try:
        # Test if server is running
        response = requests.get('http://localhost:8000/', timeout=5)
        if response.status_code == 200:
            print("✅ GremlinsAI server is running")
            
            # Test agent endpoint
            test_payload = {"input": "Hello, this is a test message"}
            response = requests.post(
                'http://localhost:8000/api/v1/agent/invoke',
                json=test_payload,
                timeout=30
            )
            
            if response.status_code == 200:
                print("✅ Agent endpoint is working")
                result = response.json()
                print(f"   Response: {result.get('output', {}).get('agent_outcome', {}).get('return_values', {}).get('output', 'No output')[:100]}...")
            else:
                print(f"❌ Agent endpoint returned status {response.status_code}")
                print(f"   Error: {response.text}")
                
        else:
            print(f"❌ Server returned status {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to GremlinsAI server")
        print("   Make sure the server is running: uvicorn app.main:app --host 127.0.0.1 --port 8000")
    except Exception as e:
        print(f"❌ Error testing API: {e}")

def main():
    """Main test function."""
    print("="*60)
    print(" GremlinsAI Local LLM Configuration Test")
    print("="*60)
    
    # Test environment
    if not test_environment():
        print("\n❌ Environment test failed. Run setup_local_llm.py first.")
        return
    
    # Test Ollama service
    ollama_ok = test_ollama_service()
    
    # Test LLM configuration
    config_ok = test_llm_config()
    
    # Test API endpoint
    test_api_endpoint()
    
    # Summary
    print("\n" + "="*60)
    print(" Test Summary")
    print("="*60)
    
    if config_ok:
        print("✅ LLM configuration is working")
        if ollama_ok:
            print("✅ Ollama service is available")
            print("🎯 Your GremlinsAI is ready for local LLM usage!")
        else:
            print("⚠️  Ollama service needs setup")
            print("🎯 GremlinsAI will use mock responses until Ollama is configured")
    else:
        print("❌ LLM configuration needs attention")
    
    print("\n📚 For setup help, see: docs/LOCAL_LLM_SETUP.md")

if __name__ == "__main__":
    main()
