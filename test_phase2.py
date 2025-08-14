#!/usr/bin/env python3
"""
Test script for Phase 2 implementation.
This script tests the chat history functionality and database operations.
"""

import sys
import os
import asyncio
import json

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

async def test_imports():
    """Test that all Phase 2 modules can be imported successfully."""
    try:
        from app.database.database import get_db, AsyncSessionLocal, ensure_data_directory
        from app.database.models import Conversation, Message
        from app.services.chat_history import ChatHistoryService
        from app.api.v1.schemas.chat_history import ConversationCreate, MessageCreate
        print("✅ All Phase 2 imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

async def test_database_setup():
    """Test database setup and basic operations."""
    try:
        from app.database.database import AsyncSessionLocal, ensure_data_directory
        from app.services.chat_history import ChatHistoryService
        
        # Ensure data directory exists
        ensure_data_directory()
        
        # Test database connection
        async with AsyncSessionLocal() as db:
            # Test creating a conversation
            conversation = await ChatHistoryService.create_conversation(
                db=db,
                title="Test Conversation",
                initial_message="Hello, this is a test!"
            )
            
            print(f"✅ Created test conversation: {conversation.id}")
            
            # Test adding a message
            message = await ChatHistoryService.add_message(
                db=db,
                conversation_id=conversation.id,
                role="assistant",
                content="Hello! How can I help you today?"
            )
            
            print(f"✅ Added test message: {message.id}")
            
            # Test retrieving conversation with messages
            retrieved_conv = await ChatHistoryService.get_conversation(
                db=db,
                conversation_id=conversation.id,
                include_messages=True
            )
            
            if retrieved_conv and len(retrieved_conv.messages) >= 2:
                print("✅ Successfully retrieved conversation with messages")
            else:
                print("❌ Failed to retrieve conversation with messages")
                return False
            
            # Test conversation context
            context = await ChatHistoryService.get_conversation_context(
                db=db,
                conversation_id=conversation.id
            )
            
            if context and len(context) >= 2:
                print("✅ Successfully retrieved conversation context")
            else:
                print("❌ Failed to retrieve conversation context")
                return False
            
            return True
            
    except Exception as e:
        print(f"❌ Database test error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_chat_history_service():
    """Test the ChatHistoryService functionality."""
    try:
        from app.database.database import AsyncSessionLocal
        from app.services.chat_history import ChatHistoryService
        
        async with AsyncSessionLocal() as db:
            # Test conversation CRUD operations
            print("🧪 Testing conversation CRUD operations...")
            
            # Create
            conv = await ChatHistoryService.create_conversation(
                db=db,
                title="CRUD Test Conversation"
            )
            print(f"✅ Created conversation: {conv.id}")
            
            # Read
            retrieved = await ChatHistoryService.get_conversation(db=db, conversation_id=conv.id)
            if retrieved:
                print("✅ Retrieved conversation successfully")
            else:
                print("❌ Failed to retrieve conversation")
                return False
            
            # Update
            updated = await ChatHistoryService.update_conversation(
                db=db,
                conversation_id=conv.id,
                title="Updated CRUD Test"
            )
            if updated and updated.title == "Updated CRUD Test":
                print("✅ Updated conversation successfully")
            else:
                print("❌ Failed to update conversation")
                return False
            
            # Test message operations
            print("🧪 Testing message operations...")
            
            msg1 = await ChatHistoryService.add_message(
                db=db,
                conversation_id=conv.id,
                role="user",
                content="First message"
            )
            
            msg2 = await ChatHistoryService.add_message(
                db=db,
                conversation_id=conv.id,
                role="assistant",
                content="Second message",
                tool_calls={"search": "test query"},
                extra_data={"confidence": 0.95}
            )
            
            if msg1 and msg2:
                print("✅ Added messages successfully")
            else:
                print("❌ Failed to add messages")
                return False
            
            # Test message retrieval
            messages = await ChatHistoryService.get_messages(db=db, conversation_id=conv.id)
            if len(messages) >= 2:
                print("✅ Retrieved messages successfully")
            else:
                print("❌ Failed to retrieve messages")
                return False
            
            # Delete (soft delete)
            deleted = await ChatHistoryService.delete_conversation(
                db=db,
                conversation_id=conv.id,
                soft_delete=True
            )
            if deleted:
                print("✅ Soft deleted conversation successfully")
            else:
                print("❌ Failed to soft delete conversation")
                return False
            
            return True
            
    except Exception as e:
        print(f"❌ Chat history service test error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all Phase 2 tests."""
    print("🚀 Starting Phase 2 Tests")
    print("=" * 50)
    
    # Test imports
    if not await test_imports():
        print("❌ Import tests failed")
        return False
    
    print()
    
    # Test database setup
    print("🗄️ Testing database setup...")
    if not await test_database_setup():
        print("❌ Database tests failed")
        return False
    
    print()
    
    # Test chat history service
    print("💬 Testing chat history service...")
    if not await test_chat_history_service():
        print("❌ Chat history service tests failed")
        return False
    
    print()
    print("🎉 All Phase 2 tests passed!")
    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
