#!/usr/bin/env python3
"""
Test Working Manual Vectors

Create a properly configured collection for manual vectors.
"""

import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_working_vectors():
    """Test manual vectors with proper configuration."""
    print("=" * 50)
    print("🔧 Working Manual Vectors Test")
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
        test_collection_name = "WorkingVectorTest"
        try:
            client.collections.delete(test_collection_name)
            print(f"🗑️  Deleted existing '{test_collection_name}'")
        except:
            pass
        
        # Create collection with proper manual vector configuration
        print(f"\n🏗️  Creating collection with manual vectors...")
        
        collection = client.collections.create(
            name=test_collection_name,
            properties=[
                wvc.Property(name="content", data_type=wvc.DataType.TEXT),
                wvc.Property(name="title", data_type=wvc.DataType.TEXT),
                wvc.Property(name="document_id", data_type=wvc.DataType.TEXT)
            ],
            # Use none vectorizer for manual vectors
            vector_config=wvc.Configure.VectorIndex.none()
        )
        
        print(f"✅ Created collection with manual vector config")
        
        # Load embedding model
        print(f"\n🧮 Loading embedding model...")
        model = SentenceTransformer('all-MiniLM-L6-v2')
        print(f"✅ Loaded embedding model")
        
        # Test adding multiple documents
        print(f"\n📄 Adding test documents...")
        
        test_docs = [
            {
                "content": "Artificial intelligence is revolutionizing technology through machine learning algorithms.",
                "title": "AI Revolution",
                "document_id": "doc1"
            },
            {
                "content": "Machine learning models use neural networks to process complex data patterns.",
                "title": "ML Neural Networks", 
                "document_id": "doc2"
            },
            {
                "content": "Deep learning is a subset of machine learning that uses multi-layered neural networks.",
                "title": "Deep Learning Basics",
                "document_id": "doc3"
            }
        ]
        
        doc_ids = []
        for i, doc in enumerate(test_docs):
            # Generate embedding
            embedding = model.encode(doc["content"]).tolist()
            
            # Insert with manual vector
            result_uuid = collection.data.insert(
                properties=doc,
                vector=embedding
            )
            
            doc_ids.append(result_uuid)
            print(f"✅ Inserted document {i+1}: {result_uuid}")
        
        # Test vector search
        print(f"\n🔍 Testing vector search...")
        
        query = "neural networks machine learning"
        query_embedding = model.encode(query).tolist()
        
        print(f"Query: '{query}'")
        print(f"Query embedding size: {len(query_embedding)}")
        
        # Try different distance thresholds
        for distance_threshold in [0.5, 1.0, 1.5, 2.0]:
            print(f"\n🔍 Searching with distance <= {distance_threshold}...")
            
            search_results = collection.query.near_vector(
                near_vector=query_embedding,
                limit=3,
                distance=distance_threshold,
                return_metadata=['distance']
            )
            
            print(f"Found {len(search_results.objects)} results")
            
            for j, result in enumerate(search_results.objects):
                distance = result.metadata.distance if result.metadata else "unknown"
                content = result.properties.get('content', '')
                title = result.properties.get('title', '')
                
                print(f"  Result {j+1}:")
                print(f"    Distance: {distance}")
                print(f"    Title: {title}")
                print(f"    Content: {content[:80]}...")
            
            if search_results.objects:
                print(f"✅ Vector search working with distance <= {distance_threshold}!")
                client.close()
                return True
        
        print(f"❌ No results found with any distance threshold")
        client.close()
        return False
        
    except Exception as e:
        print(f"❌ Working vectors test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_working_vectors()
    
    if success:
        print(f"\n🎉 Working vectors test successful!")
        print(f"✅ Manual vector storage and search is working!")
    else:
        print(f"\n❌ Working vectors test failed!")
    
    sys.exit(0 if success else 1)
