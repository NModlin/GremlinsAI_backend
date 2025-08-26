#!/usr/bin/env python3
"""
Test Simple Manual Vectors

Create the simplest possible collection and test manual vectors.
"""

import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_simple_vectors():
    """Test the simplest manual vector approach."""
    print("=" * 50)
    print("🔧 Simple Manual Vectors Test")
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
        test_collection_name = "SimpleVectorTest"
        try:
            client.collections.delete(test_collection_name)
            print(f"🗑️  Deleted existing '{test_collection_name}'")
        except:
            pass
        
        # Create the simplest possible collection
        print(f"\n🏗️  Creating simple collection...")
        
        collection = client.collections.create(
            name=test_collection_name,
            properties=[
                wvc.Property(name="content", data_type=wvc.DataType.TEXT),
                wvc.Property(name="title", data_type=wvc.DataType.TEXT)
            ]
            # No vector configuration - let Weaviate handle it
        )
        
        print(f"✅ Created simple collection")
        
        # Load embedding model
        print(f"\n🧮 Loading embedding model...")
        model = SentenceTransformer('all-MiniLM-L6-v2')
        print(f"✅ Loaded embedding model")
        
        # Test adding a document with manual vector
        print(f"\n📄 Adding document with manual vector...")
        
        test_doc = {
            "content": "Machine learning algorithms are transforming artificial intelligence applications.",
            "title": "ML AI Transformation"
        }
        
        # Generate embedding
        embedding = model.encode(test_doc["content"]).tolist()
        print(f"Generated embedding size: {len(embedding)}")
        
        # Try to insert with manual vector
        try:
            result_uuid = collection.data.insert(
                properties=test_doc,
                vector=embedding
            )
            print(f"✅ Inserted document with manual vector: {result_uuid}")
        except Exception as e:
            print(f"❌ Failed to insert with manual vector: {e}")
            
            # Try without manual vector
            print(f"🔄 Trying without manual vector...")
            try:
                result_uuid = collection.data.insert(properties=test_doc)
                print(f"✅ Inserted document without manual vector: {result_uuid}")
            except Exception as e2:
                print(f"❌ Failed to insert without manual vector: {e2}")
                return False
        
        # Wait a moment
        import time
        time.sleep(1)
        
        # Test search
        print(f"\n🔍 Testing search...")
        
        # Try vector search first
        query = "artificial intelligence machine learning"
        query_embedding = model.encode(query).tolist()
        
        try:
            print(f"🔍 Trying near_vector search...")
            search_results = collection.query.near_vector(
                near_vector=query_embedding,
                limit=1,
                return_metadata=['distance']
            )
            
            if search_results.objects:
                result = search_results.objects[0]
                distance = result.metadata.distance if result.metadata else "unknown"
                content = result.properties.get('content', '')
                
                print(f"✅ Vector search worked!")
                print(f"   Distance: {distance}")
                print(f"   Content: {content[:80]}...")
                client.close()
                return True
            else:
                print(f"⚠️  Vector search returned no results")
        except Exception as e:
            print(f"⚠️  Vector search failed: {e}")
        
        # Try text search
        try:
            print(f"🔍 Trying near_text search...")
            text_results = collection.query.near_text(
                query=query,
                limit=1,
                return_metadata=['distance']
            )
            
            if text_results.objects:
                result = text_results.objects[0]
                distance = result.metadata.distance if result.metadata else "unknown"
                content = result.properties.get('content', '')
                
                print(f"✅ Text search worked!")
                print(f"   Distance: {distance}")
                print(f"   Content: {content[:80]}...")
                client.close()
                return True
            else:
                print(f"⚠️  Text search returned no results")
        except Exception as e:
            print(f"⚠️  Text search failed: {e}")
        
        # Try BM25 search
        try:
            print(f"🔍 Trying BM25 search...")
            bm25_results = collection.query.bm25(
                query="machine learning",
                limit=1
            )
            
            if bm25_results.objects:
                result = bm25_results.objects[0]
                content = result.properties.get('content', '')
                
                print(f"✅ BM25 search worked!")
                print(f"   Content: {content[:80]}...")
                client.close()
                return True
            else:
                print(f"❌ BM25 search returned no results")
        except Exception as e:
            print(f"❌ BM25 search failed: {e}")
        
        print(f"❌ All search methods failed")
        client.close()
        return False
        
    except Exception as e:
        print(f"❌ Simple vectors test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_simple_vectors()
    
    if success:
        print(f"\n🎉 Simple vectors test successful!")
        print(f"✅ Found a working search method!")
    else:
        print(f"\n❌ Simple vectors test failed!")
    
    sys.exit(0 if success else 1)
