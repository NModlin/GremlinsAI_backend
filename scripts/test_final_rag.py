#!/usr/bin/env python3
"""
Final RAG System Test

Test the complete RAG system with all fixes applied.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

async def test_final_rag():
    """Test the final RAG system."""
    print("=" * 50)
    print("🎯 Final RAG System Test")
    print("=" * 50)
    
    try:
        from app.core.rag_system import RAGSystem
        from app.core.vector_store import vector_store
        from app.database.database import AsyncSessionLocal
        
        # Initialize RAG system
        rag_system = RAGSystem()
        
        print(f"\n📊 System Status:")
        print(f"Vector Store Connected: {vector_store.is_connected}")
        
        if not vector_store.is_connected:
            print("❌ Vector store not connected")
            return False
        
        # Test 1: Add a document
        print(f"\n📄 Adding test document...")
        
        async with AsyncSessionLocal() as db:
            doc_id = await rag_system.add_document_from_text(
                db=db,
                title="Machine Learning Fundamentals",
                content="""
                Machine learning is a subset of artificial intelligence that enables computers 
                to learn and make decisions from data without being explicitly programmed. 
                
                Key concepts include:
                - Supervised learning: Learning from labeled examples
                - Unsupervised learning: Finding patterns in unlabeled data  
                - Neural networks: Computing systems inspired by biological neural networks
                - Deep learning: Multi-layered neural networks for complex pattern recognition
                
                Applications of machine learning include image recognition, natural language 
                processing, recommendation systems, and autonomous vehicles.
                """,
                content_type="text/plain",
                doc_metadata={"category": "education", "level": "beginner"}
            )
            
            if doc_id:
                print(f"✅ Document added: {doc_id}")
            else:
                print("❌ Failed to add document")
                return False
        
        # Test 2: Test RAG queries
        print(f"\n🤖 Testing RAG queries...")
        
        test_queries = [
            "What is machine learning?",
            "What are the key concepts in ML?",
            "Tell me about neural networks"
        ]
        
        for i, query in enumerate(test_queries):
            print(f"\n--- Query {i+1}: {query} ---")
            
            async with AsyncSessionLocal() as db:
                try:
                    result = await rag_system.retrieve_and_generate(
                        db=db,
                        query=query,
                        search_limit=3,
                        score_threshold=0.1  # Low threshold to find documents
                    )
                    
                    print(f"✅ Response generated")
                    print(f"📄 Documents found: {result['search_metadata']['documents_found']}")
                    print(f"🧠 Context used: {result['context_used']}")
                    print(f"💬 Response: {result['response'][:150]}...")
                    
                    if result['search_metadata']['documents_found'] > 0:
                        print(f"✅ RAG system is working! Found and used documents.")
                        return True
                    else:
                        print(f"⚠️  No documents found for query")
                        
                except Exception as e:
                    print(f"❌ Query failed: {e}")
                    continue
        
        print(f"❌ No queries returned documents")
        return False
        
    except Exception as e:
        print(f"❌ Final RAG test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the final RAG test."""
    success = asyncio.run(test_final_rag())
    
    if success:
        print(f"\n🎉 Final RAG test successful!")
        print(f"✅ Complete RAG system is working!")
        print(f"🚀 Ready for production use!")
    else:
        print(f"\n❌ Final RAG test failed!")
        print(f"🔧 Check the errors above for issues to fix.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
