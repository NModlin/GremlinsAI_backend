#!/usr/bin/env python3
"""
Test Processing Stats Endpoint

Test the document processing statistics endpoint.
"""

import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_processing_stats():
    """Test the processing stats endpoint."""
    print("=" * 50)
    print("📊 Processing Stats Test")
    print("=" * 50)
    
    try:
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from app.api.v1.endpoints.documents import router
        
        # Create test app
        test_app = FastAPI()
        test_app.include_router(router, prefix="/api/v1/documents")
        client = TestClient(test_app)
        
        print("✅ Test client created")
        
        # Test processing stats endpoint
        print("\n📊 Testing processing stats endpoint...")
        response = client.get("/api/v1/documents/processing/stats")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Processing Stats Retrieved Successfully!")
            print(f"📄 Total Documents: {data.get('total_documents', 0)}")
            print(f"🕐 Recent Uploads (24h): {data.get('recent_uploads_24h', 0)}")
            print(f"📊 Document Types: {data.get('documents_by_type', {})}")
            print(f"🔧 Vector Store Documents: {data.get('vector_store_documents', 0)}")
            
            capabilities = data.get('processing_capabilities', {})
            print(f"🔧 Supported Formats: {len(capabilities.get('supported_formats', []))}")
            print(f"📏 Max File Size: {capabilities.get('max_file_size_mb', 0)}MB")
            print(f"📁 Batch Limit: {capabilities.get('batch_upload_limit', 0)} files")
            print(f"⏰ Timestamp: {data.get('timestamp', 'N/A')}")
            
            return True
        else:
            print(f"❌ Processing stats failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Processing stats test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_processing_stats()
    
    if success:
        print(f"\n🎉 Processing stats test successful!")
    else:
        print(f"\n❌ Processing stats test failed")
    
    sys.exit(0 if success else 1)
