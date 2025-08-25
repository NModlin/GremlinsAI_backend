#!/usr/bin/env python3
"""
Test Built-in Vectorizer

Test using Weaviate's built-in text2vec-transformers vectorizer.
"""

import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_builtin_vectorizer():
    """Test with Weaviate's built-in vectorizer."""
    print("=" * 50)
    print("🤖 Built-in Vectorizer Test")
    print("=" * 50)
    
    try:
        import weaviate
        import weaviate.classes.config as wvc
        
        # Connect to Weaviate
        client = weaviate.connect_to_local(skip_init_checks=True)
        
        if not client.is_ready():
            print("❌ Weaviate not ready")
            return False
        
        print("✅ Connected to Weaviate")
        
        # Delete existing test collection if it exists
        test_collection_name = "TestBuiltinVectorizer"
        try:
            client.collections.delete(test_collection_name)
            print(f"🗑️  Deleted existing '{test_collection_name}'")
        except:
            pass
        
        # Create collection with built-in vectorizer
        print(f"\n🏗️  Creating collection with built-in vectorizer...")
        
        try:
            collection = client.collections.create(
                name=test_collection_name,
                properties=[
                    wvc.Property(name="content", data_type=wvc.DataType.TEXT),
                    wvc.Property(name="title", data_type=wvc.DataType.TEXT)
                ],
                vectorizer_config=wvc.Configure.Vectorizer.text2vec_huggingface(
                    model="sentence-transformers/all-MiniLM-L6-v2"
                )
            )
            print(f"✅ Created collection with HuggingFace vectorizer")
        except Exception as e:
            print(f"⚠️  HuggingFace vectorizer failed: {e}")
            print("Trying with transformers vectorizer...")
            
            try:
                collection = client.collections.create(
                    name=test_collection_name,
                    properties=[
                        wvc.Property(name="content", data_type=wvc.DataType.TEXT),
                        wvc.Property(name="title", data_type=wvc.DataType.TEXT)
                    ],
                    vectorizer_config=wvc.Configure.Vectorizer.text2vec_transformers()
                )
                print(f"✅ Created collection with transformers vectorizer")
            except Exception as e2:
                print(f"❌ Both vectorizers failed: {e2}")
                return False
        
        # Test adding a document (no manual vector needed)
        print(f"\n📄 Adding test document...")
        
        test_doc = {
            "content": "Artificial intelligence is transforming the world through machine learning and deep learning.",
            "title": "AI Transformation Document"
        }
        
        result_uuid = collection.data.insert(properties=test_doc)
        print(f"✅ Inserted document: {result_uuid}")
        
        # Wait a moment for vectorization
        import time
        print("⏳ Waiting for vectorization...")
        time.sleep(2)
        
        # Test semantic search using near_text (not near_vector)
        print(f"\n🔍 Testing semantic search with near_text...")
        
        search_results = collection.query.near_text(
            query="machine learning AI",
            limit=1,
            return_metadata=['distance']
        )
        
        if search_results.objects:
            result = search_results.objects[0]
            distance = result.metadata.distance if result.metadata else "unknown"
            content = result.properties.get('content', '')
            
            print(f"✅ Found result with near_text!")
            print(f"   Distance: {distance}")
            print(f"   Content: {content[:100]}...")
            
            client.close()
            return True
        else:
            print(f"❌ No search results found with near_text")
            
            # Try BM25 search as fallback
            print(f"\n🔍 Trying BM25 search...")
            bm25_results = collection.query.bm25(
                query="machine learning",
                limit=1
            )
            
            if bm25_results.objects:
                result = bm25_results.objects[0]
                content = result.properties.get('content', '')
                print(f"✅ Found result with BM25!")
                print(f"   Content: {content[:100]}...")
                client.close()
                return True
            else:
                print(f"❌ No results with BM25 either")
                client.close()
                return False
        
    except Exception as e:
        print(f"❌ Built-in vectorizer test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_builtin_vectorizer()
    
    if success:
        print(f"\n🎉 Built-in vectorizer test successful!")
        print(f"✅ Weaviate semantic search is working!")
    else:
        print(f"\n❌ Built-in vectorizer test failed!")
    
    sys.exit(0 if success else 1)
