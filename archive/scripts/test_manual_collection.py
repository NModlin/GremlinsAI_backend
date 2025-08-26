#!/usr/bin/env python3
"""
Test Manual Collection Creation

Create a simple collection manually and test vector storage.
"""

import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_manual_collection():
    """Create and test a collection manually."""
    print("=" * 50)
    print("🧪 Manual Collection Test")
    print("=" * 50)
    
    try:
        import weaviate
        import weaviate.classes.config as wvc
        from sentence_transformers import SentenceTransformer
        
        # Connect to Weaviate
        client = weaviate.connect_to_local(skip_init_checks=True)
        
        if not client.is_ready():
            print("❌ Weaviate not ready")
            return False
        
        print("✅ Connected to Weaviate")
        
        # Delete existing test collection if it exists
        test_collection_name = "TestVectorCollection"
        try:
            client.collections.delete(test_collection_name)
            print(f"🗑️  Deleted existing '{test_collection_name}'")
        except:
            pass
        
        # Create a simple collection for testing
        print(f"\n🏗️  Creating test collection...")
        
        collection = client.collections.create(
            name=test_collection_name,
            properties=[
                wvc.Property(name="content", data_type=wvc.DataType.TEXT),
                wvc.Property(name="title", data_type=wvc.DataType.TEXT)
            ]
            # Let Weaviate handle vectors automatically for now
        )
        
        print(f"✅ Created collection '{test_collection_name}'")
        
        # Test adding a document
        print(f"\n📄 Adding test document...")
        
        test_doc = {
            "content": "Artificial intelligence is transforming the world through machine learning.",
            "title": "AI Test Document"
        }
        
        # Load embedding model
        model = SentenceTransformer('all-MiniLM-L6-v2')
        embedding = model.encode(test_doc["content"]).tolist()
        
        print(f"Generated embedding size: {len(embedding)}")
        
        # Insert with manual vector
        result_uuid = collection.data.insert(
            properties=test_doc,
            vector=embedding
        )
        
        print(f"✅ Inserted document: {result_uuid}")
        
        # Test vector search
        print(f"\n🔍 Testing vector search...")
        
        query = "machine learning artificial intelligence"
        query_embedding = model.encode(query).tolist()
        
        search_results = collection.query.near_vector(
            near_vector=query_embedding,
            limit=1,
            return_metadata=['distance']
        )
        
        if search_results.objects:
            result = search_results.objects[0]
            distance = result.metadata.distance if result.metadata else "unknown"
            content = result.properties.get('content', '')
            
            print(f"✅ Found result!")
            print(f"   Distance: {distance}")
            print(f"   Content: {content}")
            
            client.close()
            return True
        else:
            print(f"❌ No search results found")
            client.close()
            return False
        
    except Exception as e:
        print(f"❌ Manual collection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_manual_collection()
    
    if success:
        print(f"\n🎉 Manual collection test successful!")
        print(f"✅ Vector storage and search working!")
    else:
        print(f"\n❌ Manual collection test failed!")
    
    sys.exit(0 if success else 1)
