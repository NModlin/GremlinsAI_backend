#!/usr/bin/env python3
"""
Test script to verify the API endpoints work correctly.
"""

import requests
import json
import time
import subprocess
import sys
import os

def start_server():
    """Start the FastAPI server in the background."""
    try:
        # Start the server
        process = subprocess.Popen([
            sys.executable, "-m", "uvicorn", 
            "app.main:app", 
            "--host", "127.0.0.1", 
            "--port", "8000"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait a bit for the server to start
        time.sleep(3)
        
        return process
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        return None

def test_root_endpoint():
    """Test the root endpoint."""
    try:
        response = requests.get("http://127.0.0.1:8000/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Root endpoint: {data}")
            return True
        else:
            print(f"❌ Root endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Root endpoint error: {e}")
        return False

def test_agent_endpoint():
    """Test the agent endpoint."""
    try:
        payload = {"input": "What is machine learning?"}
        response = requests.post(
            "http://127.0.0.1:8000/api/v1/agent/invoke",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Agent endpoint: Response received")
            print(f"📋 Response keys: {list(data.keys())}")
            return True
        else:
            print(f"❌ Agent endpoint failed: {response.status_code}")
            print(f"📋 Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Agent endpoint error: {e}")
        return False

def main():
    """Run all API tests."""
    print("🚀 Starting API Tests")
    print("=" * 50)
    
    # Start the server
    print("🔧 Starting FastAPI server...")
    server_process = start_server()
    
    if not server_process:
        print("❌ Failed to start server")
        return False
    
    try:
        # Test endpoints
        success = True
        
        print("\n📡 Testing root endpoint...")
        if not test_root_endpoint():
            success = False
        
        print("\n🤖 Testing agent endpoint...")
        if not test_agent_endpoint():
            success = False
        
        if success:
            print("\n🎉 All API tests passed!")
        else:
            print("\n❌ Some API tests failed!")
        
        return success
        
    finally:
        # Clean up
        print("\n🧹 Cleaning up...")
        server_process.terminate()
        server_process.wait()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
