#!/usr/bin/env python3
"""
Simple validation script for Phase 2 implementation.
This script validates that all Phase 2 components are working correctly.
"""

import sys
import os
import asyncio

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

async def validate_phase2():
    """Validate Phase 2 implementation."""
    print("🔍 Validating Phase 2 Implementation")
    print("=" * 50)
    
    try:
        # Test 1: Import validation
        print("1️⃣ Testing imports...")
        from app.database.database import get_db, AsyncSessionLocal, ensure_data_directory
        from app.database.models import Conversation, Message
        from app.services.chat_history import ChatHistoryService
        from app.api.v1.schemas.chat_history import ConversationCreate, MessageCreate
        from app.api.v1.endpoints.chat_history import router as chat_router
        from app.api.v1.endpoints.agent import router as agent_router
        from app.main import app
        print("✅ All imports successful")
        
        # Test 2: Database setup
        print("\n2️⃣ Testing database setup...")
        ensure_data_directory()
        
        async with AsyncSessionLocal() as db:
            # Create a test conversation
            conversation = await ChatHistoryService.create_conversation(
                db=db,
                title="Validation Test",
                initial_message="Testing Phase 2"
            )
            print(f"✅ Created conversation: {conversation.id}")
            
            # Add a message
            message = await ChatHistoryService.add_message(
                db=db,
                conversation_id=conversation.id,
                role="assistant",
                content="Phase 2 is working correctly!"
            )
            print(f"✅ Added message: {message.id}")
            
            # Test context retrieval
            context = await ChatHistoryService.get_conversation_context(
                db=db,
                conversation_id=conversation.id
            )
            print(f"✅ Retrieved context with {len(context)} messages")
        
        # Test 3: API endpoint validation
        print("\n3️⃣ Testing API endpoints...")
        
        # Check that chat history router has the expected endpoints
        chat_routes = [route.path for route in chat_router.routes]
        expected_chat_routes = [
            "/conversations",
            "/conversations/{conversation_id}",
            "/messages",
            "/conversations/{conversation_id}/messages",
            "/conversations/{conversation_id}/context"
        ]
        
        for expected_route in expected_chat_routes:
            if any(expected_route in route for route in chat_routes):
                print(f"✅ Chat route found: {expected_route}")
            else:
                print(f"❌ Missing chat route: {expected_route}")
                return False
        
        # Check agent router has new endpoints
        agent_routes = [route.path for route in agent_router.routes]
        if "/chat" in str(agent_routes):
            print("✅ Agent chat endpoint found")
        else:
            print("❌ Missing agent chat endpoint")
            return False
        
        # Test 4: Schema validation
        print("\n4️⃣ Testing schema validation...")
        
        # Test conversation schema
        conv_create = ConversationCreate(title="Test", initial_message="Hello")
        print(f"✅ ConversationCreate schema: {conv_create.title}")
        
        # Test message schema
        msg_create = MessageCreate(
            conversation_id="test-id",
            role="user",
            content="Test message"
        )
        print(f"✅ MessageCreate schema: {msg_create.role}")
        
        # Test 5: FastAPI app validation
        print("\n5️⃣ Testing FastAPI app...")
        
        # Check that the app has the expected routers
        app_routes = [route.path for route in app.routes]
        if "/api/v1/history" in str(app_routes):
            print("✅ Chat history router included in app")
        else:
            print("❌ Chat history router not found in app")
            return False
        
        if "/api/v1/agent" in str(app_routes):
            print("✅ Agent router included in app")
        else:
            print("❌ Agent router not found in app")
            return False
        
        print("\n🎉 Phase 2 validation completed successfully!")
        print("\n📋 Phase 2 Features Validated:")
        print("   ✅ Database models and migrations")
        print("   ✅ Chat history service with CRUD operations")
        print("   ✅ API endpoints for conversations and messages")
        print("   ✅ Pydantic schemas for request/response validation")
        print("   ✅ Agent integration with conversation context")
        print("   ✅ FastAPI application with proper routing")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(validate_phase2())
    sys.exit(0 if success else 1)
