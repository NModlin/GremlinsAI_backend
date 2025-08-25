#!/usr/bin/env python3
"""
Test Vector Storage

Check if vectors are actually being stored in Weaviate.
"""

import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_vector_storage():
    """Test if vectors are being stored properly."""
    print("=" * 50)
    print("🧮 Vector Storage Test")
    print("=" * 50)
    
    try:
        from app.core.vector_store import vector_store
        
        if not vector_store.is_connected:
            print("❌ Vector store not connected")
            return False
        
        # Test 1: Add a document with explicit vector check
        print(f"\n📄 Testing document addition with vector...")
        
        test_content = "This is a test document about machine learning and neural networks."
        test_embedding = vector_store.embed_text(test_content)
        
        print(f"Generated embedding size: {len(test_embedding) if test_embedding else 'None'}")
        
        if not test_embedding:
            print("❌ Failed to generate embedding")
            return False
        
        # Add document
        doc_id = vector_store.add_document(
            content=test_content,
            metadata={
                "title": "Test ML Document",
                "content_type": "text/plain"
            }
        )
        
        print(f"Added document: {doc_id}")
        
        # Test 2: Check if the document has a vector
        print(f"\n🔍 Checking if document has vector...")
        
        collection = vector_store.client.collections.get(vector_store.class_name)
        
        # Get the specific document (v4 API)
        obj = collection.query.fetch_objects(
            limit=1,
            include_vector=True
        )
        
        if obj.objects:
            document = obj.objects[0]
            has_vector = hasattr(document, 'vector') and document.vector is not None
            print(f"Document has vector: {has_vector}")
            
            if has_vector:
                print(f"Vector size: {len(document.vector)}")
            else:
                print("❌ Document has no vector!")
                return False
        else:
            print("❌ Document not found!")
            return False
        
        # Test 3: Try vector search with very low threshold
        print(f"\n🔍 Testing vector search with low threshold...")
        
        search_results = collection.query.near_vector(
            near_vector=test_embedding,
            limit=5,
            distance=2.0,  # Very permissive
            return_metadata=['distance']
        )
        
        print(f"Found {len(search_results.objects)} results with distance <= 2.0")
        
        for i, result in enumerate(search_results.objects):
            distance = result.metadata.distance if result.metadata else "unknown"
            content = result.properties.get('content', '')[:50]
            print(f"  Result {i+1}: distance={distance}, content='{content}...'")
        
        # Test 4: Try with even more permissive search
        print(f"\n🔍 Testing with maximum permissive search...")
        
        all_results = collection.query.near_vector(
            near_vector=test_embedding,
            limit=10,
            # No distance limit - get everything
            return_metadata=['distance']
        )
        
        print(f"Found {len(all_results.objects)} total results")
        
        if len(all_results.objects) > 0:
            print("✅ Vector search is working!")
            return True
        else:
            print("❌ No results even with maximum permissive search")
            return False
        
    except Exception as e:
        print(f"❌ Vector storage test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_vector_storage()
    sys.exit(0 if success else 1)
