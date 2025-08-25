#!/usr/bin/env python3
"""
Test RAG System with Weaviate Integration

This script tests the RAG system to ensure it properly integrates with
Weaviate and can perform document storage and retrieval.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

async def test_rag_system():
    """Test the RAG system functionality."""
    print("=" * 60)
    print("🧙‍♂️ GremlinsAI RAG System Test")
    print("=" * 60)
    
    try:
        from app.core.rag_system import RAGSystem
        from app.core.vector_store import vector_store
        from app.core.llm_config import get_llm_info
        from app.database.database import AsyncSessionLocal
        
        # Initialize RAG system
        rag_system = RAGSystem()
        
        # Test 1: Check system status
        print("\n🔍 Testing RAG System Status...")
        async with AsyncSessionLocal() as db:
            status = await rag_system.get_system_status(db)
            
            print(f"Status: {status['status']}")
            print(f"Vector Store Connected: {status['vector_store']['connected']}")
            print(f"LLM Available: {status['llm_status']['available']}")
            print(f"Features:")
            for feature, available in status['features'].items():
                print(f"  {'✅' if available else '❌'} {feature}")
        
        # Test 2: Check Weaviate connection
        print("\n🔍 Testing Weaviate Connection...")
        if vector_store.is_connected:
            print("✅ Weaviate is connected")
            capabilities = vector_store.get_capabilities()
            print("Capabilities:")
            for cap, available in capabilities.items():
                print(f"  {'✅' if available else '❌'} {cap}")
        else:
            print("❌ Weaviate is not connected")
            print("💡 Run: python scripts/setup_weaviate.py")
            return False
        
        # Test 3: Add a test document
        print("\n📄 Testing Document Addition...")
        test_content = """
        Artificial Intelligence (AI) is a branch of computer science that aims to create 
        intelligent machines that work and react like humans. Some of the activities 
        computers with artificial intelligence are designed for include:
        
        - Speech recognition
        - Learning
        - Planning
        - Problem solving
        
        AI research has been highly successful in developing effective techniques for 
        solving a wide range of problems, from game playing to medical diagnosis.
        """
        
        async with AsyncSessionLocal() as db:
            doc_id = await rag_system.add_document_from_text(
                db=db,
                title="Introduction to Artificial Intelligence",
                content=test_content,
                content_type="text/plain",
                doc_metadata={"category": "AI", "test": True}
            )
            
            if doc_id:
                print(f"✅ Document added successfully: {doc_id}")
            else:
                print("❌ Failed to add document")
                return False
        
        # Test 4: Test RAG query
        print("\n🤖 Testing RAG Query...")
        test_queries = [
            "What is artificial intelligence?",
            "What activities are AI computers designed for?",
            "Tell me about AI research"
        ]
        
        for query in test_queries:
            print(f"\nQuery: {query}")
            
            async with AsyncSessionLocal() as db:
                result = await rag_system.retrieve_and_generate(
                    db=db,
                    query=query,
                    search_limit=3,
                    score_threshold=0.5
                )
                
                print(f"Response: {result['response'][:200]}...")
                print(f"Documents found: {result['search_metadata']['documents_found']}")
                print(f"Context used: {result['context_used']}")
        
        # Test 5: Test multimodal capabilities (if available)
        print("\n🎨 Testing Multimodal Capabilities...")
        capabilities = vector_store.get_capabilities()
        if capabilities.get("multimodal_embeddings", False):
            print("✅ Multimodal embeddings available")
            # Could add image test here if we had test images
        else:
            print("⚪ Multimodal embeddings not available (CLIP not installed)")
        
        print("\n🎉 RAG System Test Complete!")
        return True
        
    except Exception as e:
        print(f"❌ RAG system test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_vector_search():
    """Test direct vector search functionality."""
    print("\n🔍 Testing Direct Vector Search...")
    
    try:
        from app.core.vector_store import vector_store
        
        if not vector_store.is_connected:
            print("❌ Vector store not connected")
            return False
        
        # Test search
        results = vector_store.search_similar(
            query="artificial intelligence machine learning",
            limit=3,
            score_threshold=0.3
        )
        
        print(f"Found {len(results)} results:")
        for i, result in enumerate(results):
            print(f"  {i+1}. Score: {result['score']:.3f}")
            print(f"     Content: {result['content'][:100]}...")
            print(f"     Metadata: {result['metadata']}")
        
        return len(results) > 0
        
    except Exception as e:
        print(f"❌ Vector search test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Starting RAG system tests...")
    
    # Run async tests
    success = asyncio.run(test_rag_system())
    
    if success:
        # Run vector search test
        vector_success = asyncio.run(test_vector_search())
        success = success and vector_success
    
    if success:
        print("\n✅ All tests passed! RAG system is working correctly.")
        return True
    else:
        print("\n❌ Some tests failed. Check the output above for details.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
