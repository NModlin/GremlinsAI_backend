#!/usr/bin/env python3
"""
API test script for Phase 2 implementation.
This script tests the chat history API endpoints.
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
        time.sleep(5)
        
        return process
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        return None

def test_conversation_crud():
    """Test conversation CRUD operations."""
    base_url = "http://127.0.0.1:8000/api/v1/history"
    
    try:
        # Create conversation
        print("🧪 Testing conversation creation...")
        create_payload = {
            "title": "API Test Conversation",
            "initial_message": "Hello from API test!"
        }
        
        response = requests.post(f"{base_url}/conversations", json=create_payload)
        if response.status_code != 201:
            print(f"❌ Failed to create conversation: {response.status_code}")
            print(response.text)
            return False
        
        conversation = response.json()
        conversation_id = conversation["id"]
        print(f"✅ Created conversation: {conversation_id}")
        
        # Get conversation
        print("🧪 Testing conversation retrieval...")
        response = requests.get(f"{base_url}/conversations/{conversation_id}")
        if response.status_code != 200:
            print(f"❌ Failed to get conversation: {response.status_code}")
            return False
        
        retrieved_conv = response.json()
        print(f"✅ Retrieved conversation: {retrieved_conv['title']}")
        
        # Update conversation
        print("🧪 Testing conversation update...")
        update_payload = {"title": "Updated API Test Conversation"}
        response = requests.put(f"{base_url}/conversations/{conversation_id}", json=update_payload)
        if response.status_code != 200:
            print(f"❌ Failed to update conversation: {response.status_code}")
            return False
        
        updated_conv = response.json()
        print(f"✅ Updated conversation: {updated_conv['title']}")
        
        # List conversations
        print("🧪 Testing conversation listing...")
        response = requests.get(f"{base_url}/conversations")
        if response.status_code != 200:
            print(f"❌ Failed to list conversations: {response.status_code}")
            return False
        
        conv_list = response.json()
        print(f"✅ Listed {len(conv_list['conversations'])} conversations")
        
        return conversation_id
        
    except Exception as e:
        print(f"❌ Conversation CRUD test error: {e}")
        return False

def test_message_operations(conversation_id):
    """Test message operations."""
    base_url = "http://127.0.0.1:8000/api/v1/history"
    
    try:
        # Add message
        print("🧪 Testing message creation...")
        message_payload = {
            "conversation_id": conversation_id,
            "role": "user",
            "content": "This is a test message from API",
            "extra_data": {"test": True}
        }
        
        response = requests.post(f"{base_url}/messages", json=message_payload)
        if response.status_code != 201:
            print(f"❌ Failed to create message: {response.status_code}")
            print(response.text)
            return False
        
        message = response.json()
        print(f"✅ Created message: {message['id']}")
        
        # Get messages
        print("🧪 Testing message retrieval...")
        response = requests.get(f"{base_url}/conversations/{conversation_id}/messages")
        if response.status_code != 200:
            print(f"❌ Failed to get messages: {response.status_code}")
            return False
        
        messages = response.json()
        print(f"✅ Retrieved {len(messages['messages'])} messages")
        
        # Get conversation context
        print("🧪 Testing conversation context...")
        response = requests.get(f"{base_url}/conversations/{conversation_id}/context")
        if response.status_code != 200:
            print(f"❌ Failed to get context: {response.status_code}")
            return False
        
        context = response.json()
        print(f"✅ Retrieved context with {context['message_count']} messages")
        
        return True
        
    except Exception as e:
        print(f"❌ Message operations test error: {e}")
        return False

def test_agent_integration():
    """Test agent integration with chat history."""
    try:
        # Test new chat endpoint
        print("🧪 Testing agent chat integration...")
        chat_payload = {
            "input": "What is artificial intelligence?",
            "save_conversation": True
        }
        
        response = requests.post("http://127.0.0.1:8000/api/v1/agent/chat", json=chat_payload)
        if response.status_code != 200:
            print(f"❌ Failed agent chat: {response.status_code}")
            print(response.text)
            return False
        
        chat_response = response.json()
        conversation_id = chat_response["conversation_id"]
        print(f"✅ Agent chat created conversation: {conversation_id}")
        
        # Test follow-up message with context
        print("🧪 Testing follow-up with context...")
        followup_payload = {
            "input": "Can you elaborate on that?",
            "conversation_id": conversation_id,
            "save_conversation": True
        }
        
        response = requests.post("http://127.0.0.1:8000/api/v1/agent/chat", json=followup_payload)
        if response.status_code != 200:
            print(f"❌ Failed follow-up chat: {response.status_code}")
            return False
        
        followup_response = response.json()
        print(f"✅ Follow-up chat used context: {followup_response['context_used']}")
        
        # Test backward compatibility
        print("🧪 Testing backward compatibility...")
        simple_payload = {"input": "Simple test"}
        response = requests.post("http://127.0.0.1:8000/api/v1/agent/invoke", json=simple_payload)
        if response.status_code != 200:
            print(f"❌ Failed simple agent invoke: {response.status_code}")
            return False
        
        print("✅ Backward compatibility maintained")
        
        return True
        
    except Exception as e:
        print(f"❌ Agent integration test error: {e}")
        return False

def main():
    """Run all Phase 2 API tests."""
    print("🚀 Starting Phase 2 API Tests")
    print("=" * 50)
    
    # Start the server
    print("🔧 Starting FastAPI server...")
    server_process = start_server()
    
    if not server_process:
        print("❌ Failed to start server")
        return False
    
    try:
        # Test conversation CRUD
        print("\n💬 Testing conversation CRUD operations...")
        conversation_id = test_conversation_crud()
        if not conversation_id:
            print("❌ Conversation CRUD tests failed")
            return False
        
        # Test message operations
        print("\n📝 Testing message operations...")
        if not test_message_operations(conversation_id):
            print("❌ Message operation tests failed")
            return False
        
        # Test agent integration
        print("\n🤖 Testing agent integration...")
        if not test_agent_integration():
            print("❌ Agent integration tests failed")
            return False
        
        print("\n🎉 All Phase 2 API tests passed!")
        return True
        
    finally:
        # Clean up
        print("\n🧹 Cleaning up...")
        server_process.terminate()
        server_process.wait()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
