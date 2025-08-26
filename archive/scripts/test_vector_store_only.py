#!/usr/bin/env python3
"""
Test Vector Store Only

Test just the vector store functionality without the full RAG system.
"""

import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_vector_store_only():
    """Test just the vector store."""
    print("=" * 50)
    print("🔧 Vector Store Only Test")
    print("=" * 50)
    
    try:
        from app.core.vector_store import vector_store
        
        print(f"Vector Store Connected: {vector_store.is_connected}")
        
        if not vector_store.is_connected:
            print("❌ Vector store not connected")
            return False
        
        # Test 1: Add a document directly to vector store
        print(f"\n📄 Adding document to vector store...")
        
        doc_id = vector_store.add_document(
            content="Machine learning is a powerful tool for data analysis and pattern recognition.",
            metadata={
                "title": "ML Introduction",
                "document_id": "test-doc-1",
                "content_type": "text/plain"
            }
        )
        
        if doc_id:
            print(f"✅ Document added: {doc_id}")
        else:
            print("❌ Failed to add document")
            return False
        
        # Test 2: Search for the document
        print(f"\n🔍 Searching for document...")
        
        results = vector_store.search_similar(
            query="machine learning data analysis",
            limit=3,
            score_threshold=0.1
        )
        
        print(f"Found {len(results)} results")
        
        if results:
            for i, result in enumerate(results):
                print(f"  Result {i+1}:")
                print(f"    Score: {result['score']}")
                print(f"    Title: {result.get('document_title', 'No title')}")
                print(f"    Content: {result['content'][:80]}...")
            
            print(f"✅ Vector store search is working!")
            return True
        else:
            print(f"❌ No search results found")
            return False
        
    except Exception as e:
        print(f"❌ Vector store test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_vector_store_only()
    
    if success:
        print(f"\n🎉 Vector store test successful!")
        print(f"✅ Vector store is working correctly!")
    else:
        print(f"\n❌ Vector store test failed!")
    
    sys.exit(0 if success else 1)
