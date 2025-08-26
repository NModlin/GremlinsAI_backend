#!/usr/bin/env python3
"""
Recreate Weaviate Collection

Delete and recreate the collection with proper vector configuration.
"""

import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

def recreate_collection():
    """Delete and recreate the collection with proper configuration."""
    print("=" * 50)
    print("🔄 Recreating Weaviate Collection")
    print("=" * 50)
    
    try:
        from app.core.vector_store import vector_store
        
        if not vector_store.is_connected:
            print("❌ Vector store not connected")
            return False
        
        collection_name = vector_store.class_name
        
        # Step 1: Delete existing collection
        print(f"\n🗑️  Deleting existing collection '{collection_name}'...")
        try:
            vector_store.client.collections.delete(collection_name)
            print(f"✅ Deleted collection '{collection_name}'")
        except Exception as e:
            if "not found" in str(e).lower():
                print(f"⚠️  Collection '{collection_name}' doesn't exist, skipping deletion")
            else:
                print(f"❌ Error deleting collection: {e}")
                return False
        
        # Step 2: Create new collection with proper configuration
        print(f"\n🏗️  Creating new collection '{collection_name}'...")
        try:
            new_collection = vector_store._create_simple_collection()
            print(f"✅ Created collection '{collection_name}'")
        except Exception as e:
            print(f"❌ Error creating collection: {e}")
            return False
        
        # Step 3: Verify the collection
        print(f"\n🔍 Verifying collection...")
        try:
            collections = vector_store.client.collections.list_all()
            if collection_name in collections:
                print(f"✅ Collection '{collection_name}' exists")
                
                # Get collection info
                collection = vector_store.client.collections.get(collection_name)
                print(f"✅ Collection accessible")
                
                return True
            else:
                print(f"❌ Collection '{collection_name}' not found after creation")
                return False
                
        except Exception as e:
            print(f"❌ Error verifying collection: {e}")
            return False
        
    except Exception as e:
        print(f"❌ Collection recreation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_new_collection():
    """Test the new collection with a document."""
    print(f"\n🧪 Testing new collection...")
    
    try:
        from app.core.vector_store import vector_store
        
        # Add a test document
        test_content = "This is a test document for the new collection configuration."
        doc_id = vector_store.add_document(
            content=test_content,
            metadata={
                "title": "Test Document",
                "content_type": "text/plain"
            }
        )
        
        print(f"✅ Added test document: {doc_id}")
        
        # Test search
        results = vector_store.search_similar(
            query="test document",
            limit=1,
            score_threshold=0.1
        )
        
        if results:
            print(f"✅ Search found {len(results)} results")
            print(f"   Score: {results[0]['score']}")
            print(f"   Content: {results[0]['content'][:50]}...")
            return True
        else:
            print(f"❌ Search found no results")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    print("Starting collection recreation...")
    
    # Step 1: Recreate collection
    success = recreate_collection()
    
    if success:
        # Step 2: Test the new collection
        test_success = test_new_collection()
        
        if test_success:
            print(f"\n🎉 Collection recreation successful!")
            print(f"✅ Vector search is now working!")
        else:
            print(f"\n⚠️  Collection created but search test failed")
            success = False
    
    sys.exit(0 if success else 1)
