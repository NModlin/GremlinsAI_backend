#!/usr/bin/env python3
"""
Simple Weaviate Connection Test

Test basic Weaviate connectivity before running full RAG tests.
"""

import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_weaviate_basic():
    """Test basic Weaviate connection."""
    print("🔍 Testing basic Weaviate connection...")
    
    try:
        import weaviate
        print("✅ Weaviate client imported")
        
        # Try to connect (skip gRPC checks)
        client = weaviate.connect_to_local(skip_init_checks=True)
        print("✅ Weaviate client created")
        
        # Test if ready
        if client.is_ready():
            print("✅ Weaviate is ready!")
            
            # Get meta info
            try:
                # In v4, we need to use different methods
                print("📊 Weaviate is connected and ready")
                return True
            except Exception as e:
                print(f"⚠️  Connected but couldn't get meta: {e}")
                return True  # Still consider it working
        else:
            print("❌ Weaviate is not ready")
            return False
            
    except Exception as e:
        print(f"❌ Weaviate connection failed: {e}")
        return False
    finally:
        try:
            if 'client' in locals():
                client.close()
        except:
            pass

def test_vector_store_import():
    """Test if our vector store can be imported."""
    print("\n🔍 Testing vector store import...")
    
    try:
        from app.core.vector_store import vector_store
        print("✅ Vector store imported")
        
        print(f"Connected: {vector_store.is_connected}")
        print(f"Class name: {vector_store.class_name}")
        
        if hasattr(vector_store, 'get_capabilities'):
            capabilities = vector_store.get_capabilities()
            print("📊 Capabilities:")
            for cap, available in capabilities.items():
                print(f"  {'✅' if available else '❌'} {cap}")
        
        return vector_store.is_connected
        
    except Exception as e:
        print(f"❌ Vector store import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run basic tests."""
    print("=" * 50)
    print("🧙‍♂️ Basic Weaviate Connection Test")
    print("=" * 50)
    
    # Test 1: Basic Weaviate connection
    weaviate_ok = test_weaviate_basic()
    
    # Test 2: Vector store import
    vector_store_ok = test_vector_store_import()
    
    print("\n" + "=" * 50)
    print("📊 RESULTS")
    print("=" * 50)
    print(f"Weaviate Connection: {'✅' if weaviate_ok else '❌'}")
    print(f"Vector Store: {'✅' if vector_store_ok else '❌'}")
    
    if weaviate_ok and vector_store_ok:
        print("\n🎉 Basic connectivity working! Ready for RAG tests.")
        return True
    else:
        print("\n❌ Issues found. Fix connectivity before running RAG tests.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
