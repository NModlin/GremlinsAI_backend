#!/usr/bin/env python3
"""
Test script for OAuth2 integration.
This script tests the OAuth2 endpoints without needing to start the full server.
"""

import asyncio
import json
from fastapi.testclient import TestClient
from app.main import app

def test_oauth2_endpoints():
    """Test OAuth2 endpoints using FastAPI TestClient."""
    print("🔧 Testing OAuth2 endpoints...")
    
    client = TestClient(app)
    
    # Test 1: OAuth2 Configuration Endpoint
    print("\n1️⃣ Testing OAuth2 configuration endpoint...")
    try:
        response = client.get("/api/v1/auth/config")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            config = response.json()
            print(f"✅ OAuth2 Config: {json.dumps(config, indent=2)}")
        else:
            print(f"❌ Error: {response.text}")
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    # Test 2: Health Check (should work without auth)
    print("\n2️⃣ Testing health endpoint...")
    try:
        response = client.get("/api/v1/health/health")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            health = response.json()
            print(f"✅ Health: {json.dumps(health, indent=2)}")
        else:
            print(f"❌ Error: {response.text}")
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    # Test 3: Document Upload (should require auth now)
    print("\n3️⃣ Testing document upload without auth (should fail)...")
    try:
        files = {"file": ("test.txt", "This is a test document", "text/plain")}
        response = client.post("/api/v1/documents/upload", files=files)
        print(f"Status: {response.status_code}")
        if response.status_code == 401:
            print("✅ Correctly requires authentication!")
            print(f"Error message: {response.json()}")
        else:
            print(f"❌ Unexpected response: {response.text}")
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    # Test 4: Token verification endpoint
    print("\n4️⃣ Testing token verification without token...")
    try:
        response = client.get("/api/v1/auth/verify")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Verify result: {json.dumps(result, indent=2)}")
        else:
            print(f"❌ Error: {response.text}")
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    print("\n🎉 OAuth2 endpoint testing completed!")
    print("\n📋 Next Steps:")
    print("1. Start the server: uvicorn app.main:app --reload --port 8000")
    print("2. Visit: http://localhost:8000/docs")
    print("3. Test the /api/v1/auth/config endpoint")
    print("4. Use Google OAuth2 to get a token")
    print("5. Test authenticated endpoints with the token")

def test_google_oauth2_flow():
    """Test Google OAuth2 flow simulation."""
    print("\n🔐 Google OAuth2 Flow Test:")
    print("1. Go to: https://accounts.google.com/o/oauth2/v2/auth")
    print("2. Parameters:")
    print(f"   - client_id: 818968828866-b9svspa4m2mb68931tgb2r37trjjfet8.apps.googleusercontent.com")
    print(f"   - redirect_uri: http://localhost:3000/auth/callback")
    print(f"   - response_type: code")
    print(f"   - scope: openid email profile")
    print("3. After authorization, you'll get a code")
    print("4. Exchange the code for an ID token")
    print("5. Use the ID token with /api/v1/auth/token endpoint")

if __name__ == "__main__":
    test_oauth2_endpoints()
    test_google_oauth2_flow()
