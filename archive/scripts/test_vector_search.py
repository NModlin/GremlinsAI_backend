#!/usr/bin/env python3
"""
Test Vector Search Functionality

Debug why our vector search isn't finding documents.
"""

import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_vector_search():
    """Test vector search step by step."""
    print("=" * 50)
    print("🔍 Vector Search Debug Test")
    print("=" * 50)
    
    try:
        from app.core.vector_store import vector_store
        
        print(f"\n📊 Vector Store Status:")
        print(f"Connected: {vector_store.is_connected}")
        print(f"Class name: {vector_store.class_name}")
        
        if not vector_store.is_connected:
            print("❌ Vector store not connected")
            return False
        
        # Test 1: Check if documents exist in collection
        print(f"\n🔍 Testing collection info...")
        info = vector_store.get_collection_info()
        print(f"Collection info: {info}")
        
        # Test 2: Try to list all objects in collection
        print(f"\n📄 Testing direct collection access...")
        try:
            collection = vector_store.client.collections.get(vector_store.class_name)
            
            # Get all objects
            all_objects = collection.query.fetch_objects(limit=10)
            print(f"Found {len(all_objects.objects)} objects in collection")
            
            for i, obj in enumerate(all_objects.objects):
                print(f"  Object {i+1}:")
                print(f"    UUID: {obj.uuid}")
                print(f"    Content: {obj.properties.get('content', '')[:100]}...")
                print(f"    Title: {obj.properties.get('title', '')}")
                
        except Exception as e:
            print(f"❌ Error accessing collection: {e}")
            return False
        
        # Test 3: Test embedding generation
        print(f"\n🧮 Testing embedding generation...")
        test_query = "artificial intelligence"
        embedding = vector_store.embed_text(test_query)
        
        if embedding:
            print(f"✅ Generated embedding of size: {len(embedding)}")
        else:
            print(f"❌ Failed to generate embedding")
            return False
        
        # Test 4: Test direct vector search
        print(f"\n🔍 Testing direct vector search...")
        try:
            search_results = collection.query.near_vector(
                near_vector=embedding,
                limit=3,
                distance=0.8,  # More permissive distance
                return_metadata=['distance']
            )
            
            print(f"Found {len(search_results.objects)} results")
            for i, obj in enumerate(search_results.objects):
                distance = obj.metadata.distance if obj.metadata else "unknown"
                print(f"  Result {i+1}:")
                print(f"    Distance: {distance}")
                print(f"    Content: {obj.properties.get('content', '')[:100]}...")
                
        except Exception as e:
            print(f"❌ Direct vector search failed: {e}")
            return False
        
        # Test 5: Test our vector store search method
        print(f"\n🔍 Testing vector store search method...")
        try:
            results = vector_store.search_similar(
                query=test_query,
                limit=3,
                score_threshold=0.1  # Very low threshold
            )
            
            print(f"Vector store search found {len(results)} results")
            for i, result in enumerate(results):
                print(f"  Result {i+1}:")
                print(f"    Score: {result['score']}")
                print(f"    Content: {result['content'][:100]}...")
                
        except Exception as e:
            print(f"❌ Vector store search failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        print(f"\n✅ Vector search test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Vector search test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_vector_search()
    sys.exit(0 if success else 1)
