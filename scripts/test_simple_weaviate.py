#!/usr/bin/env python3
"""
Very Simple Weaviate Test

Just test if we can connect to Weaviate without any complex imports.
"""

def test_simple_connection():
    """Test the simplest possible Weaviate connection."""
    print("🔍 Testing simple Weaviate connection...")
    
    try:
        import weaviate
        print("✅ Weaviate imported")
        
        # Connect with minimal options
        client = weaviate.connect_to_local(skip_init_checks=True)
        print("✅ Client created")
        
        # Test ready
        ready = client.is_ready()
        print(f"Ready: {ready}")
        
        if ready:
            print("✅ Weaviate is ready!")
            
            # Try to list collections/classes
            try:
                # In v4, collections are accessed differently
                collections = client.collections.list_all()
                print(f"Collections: {list(collections.keys()) if collections else 'None'}")
            except Exception as e:
                print(f"⚠️  Couldn't list collections: {e}")
            
            client.close()
            return True
        else:
            print("❌ Weaviate not ready")
            client.close()
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 40)
    print("🧙‍♂️ Simple Weaviate Test")
    print("=" * 40)
    
    success = test_simple_connection()
    
    if success:
        print("\n✅ Simple connection works!")
    else:
        print("\n❌ Connection failed")
    
    exit(0 if success else 1)
