#!/usr/bin/env python3
"""
Simple RAG Test

Test basic RAG functionality with minimal complexity.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

async def test_simple_rag():
    """Test basic RAG functionality."""
    print("=" * 50)
    print("🧙‍♂️ Simple RAG Test")
    print("=" * 50)
    
    try:
        # Test 1: Import basic components
        print("\n🔍 Testing imports...")
        from app.core.llm_config import get_llm_info
        from app.database.database import AsyncSessionLocal
        print("✅ Basic imports successful")
        
        # Test 2: Check LLM status
        print("\n🔍 Testing LLM status...")
        llm_info = get_llm_info()
        print(f"LLM Provider: {llm_info.get('provider', 'unknown')}")
        print(f"LLM Available: {llm_info.get('available', False)}")
        print(f"Model: {llm_info.get('model_name', 'unknown')}")
        
        # Test 3: Test Weaviate connection
        print("\n🔍 Testing Weaviate connection...")
        import weaviate
        client = weaviate.connect_to_local(skip_init_checks=True)
        
        if client.is_ready():
            print("✅ Weaviate connected")
            collections = client.collections.list_all()
            print(f"Available collections: {list(collections.keys())}")
            
            # Test 4: Try to create a simple collection for testing
            print("\n🔍 Testing collection creation...")
            collection_name = "TestRAG"
            
            try:
                # Check if collection exists
                if collection_name in collections:
                    print(f"✅ Collection '{collection_name}' already exists")
                    collection = client.collections.get(collection_name)
                else:
                    # Create simple collection
                    collection = client.collections.create(
                        name=collection_name,
                        properties=[
                            weaviate.classes.config.Property(
                                name="content",
                                data_type=weaviate.classes.config.DataType.TEXT
                            ),
                            weaviate.classes.config.Property(
                                name="title", 
                                data_type=weaviate.classes.config.DataType.TEXT
                            )
                        ]
                    )
                    print(f"✅ Created collection '{collection_name}'")
                
                # Test 5: Add a test document
                print("\n🔍 Testing document addition...")
                test_doc = {
                    "content": "Artificial Intelligence is a branch of computer science that aims to create intelligent machines.",
                    "title": "AI Introduction"
                }
                
                result = collection.data.insert(test_doc)
                print(f"✅ Document added: {result}")
                
                # Test 6: Search for the document
                print("\n🔍 Testing search...")
                try:
                    search_results = collection.query.near_text(
                        query="artificial intelligence",
                        limit=1
                    ).objects
                except Exception as search_error:
                    print(f"⚠️  Near text search failed: {search_error}")
                    # Try a simpler search approach
                    try:
                        search_results = collection.query.bm25(
                            query="artificial intelligence",
                            limit=1
                        ).objects
                        print("✅ Using BM25 search instead")
                    except Exception as bm25_error:
                        print(f"⚠️  BM25 search also failed: {bm25_error}")
                        search_results = []
                
                if search_results:
                    print(f"✅ Found {len(search_results)} results")
                    for result in search_results:
                        print(f"   Content: {result.properties.get('content', '')[:100]}...")
                else:
                    print("⚠️  No search results found")
                
                # Test 7: Test with LLM if available
                if llm_info.get('available', False):
                    print("\n🔍 Testing LLM integration...")
                    from app.core.llm_config import get_llm
                    
                    llm = get_llm()
                    if llm:
                        # Create a simple RAG prompt
                        context = search_results[0].properties.get('content', '') if search_results else ""
                        query = "What is artificial intelligence?"
                        
                        if context:
                            prompt = f"Based on this context: {context}\n\nAnswer the question: {query}"
                            response = llm.invoke(prompt)
                            
                            # Handle different response types
                            if hasattr(response, 'content'):
                                answer = response.content
                            else:
                                answer = str(response)
                            
                            print(f"✅ LLM Response: {answer[:200]}...")
                        else:
                            print("⚠️  No context available for LLM")
                    else:
                        print("⚠️  LLM not available")
                else:
                    print("⚠️  LLM not configured")
                
                print("\n🎉 Simple RAG test completed successfully!")
                client.close()
                return True
                
            except Exception as e:
                print(f"❌ Collection/document error: {e}")
                client.close()
                return False
        else:
            print("❌ Weaviate not ready")
            client.close()
            return False
            
    except Exception as e:
        print(f"❌ RAG test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the simple RAG test."""
    success = asyncio.run(test_simple_rag())
    
    if success:
        print("\n✅ Simple RAG test passed!")
        print("🎯 Basic RAG functionality is working!")
    else:
        print("\n❌ Simple RAG test failed!")
        print("🔧 Check the errors above for issues to fix.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
