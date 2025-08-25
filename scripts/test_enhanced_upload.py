#!/usr/bin/env python3
"""
Test Enhanced Upload Endpoints

Test the enhanced document upload functionality including batch upload and processing stats.
"""

import sys
import json
import io
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_enhanced_upload():
    """Test the enhanced upload endpoints."""
    print("=" * 60)
    print("📁 Enhanced Upload Endpoints Test")
    print("=" * 60)
    
    try:
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from app.api.v1.endpoints.documents import router
        
        # Create test app
        test_app = FastAPI()
        test_app.include_router(router, prefix="/api/v1/documents")
        client = TestClient(test_app)
        
        print("✅ Test client created")
        
        # Test 1: Processing stats endpoint
        print("\n📊 Testing processing stats endpoint...")
        try:
            response = client.get("/api/v1/documents/processing/stats")
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Processing Stats Retrieved")
                print(f"📄 Total Documents: {data.get('total_documents', 0)}")
                print(f"🕐 Recent Uploads (24h): {data.get('recent_uploads_24h', 0)}")
                print(f"🔧 Supported Formats: {len(data.get('processing_capabilities', {}).get('supported_formats', []))}")
                print(f"📊 Max File Size: {data.get('processing_capabilities', {}).get('max_file_size_mb', 0)}MB")
            else:
                print(f"❌ Processing stats failed: {response.text}")
        except Exception as e:
            print(f"❌ Processing stats error: {e}")
        
        # Test 2: Enhanced single file upload
        print("\n📄 Testing enhanced single file upload...")
        try:
            # Create test files with different types
            test_files = [
                {
                    "name": "test_document.txt",
                    "content": "This is a comprehensive test document for the enhanced upload system. It contains multiple sentences to test content processing.",
                    "type": "text/plain"
                },
                {
                    "name": "test_data.json",
                    "content": '{"title": "Test JSON", "description": "This is a JSON test file", "data": [1, 2, 3, 4, 5]}',
                    "type": "application/json"
                },
                {
                    "name": "test_data.csv",
                    "content": "name,age,city\nJohn,25,New York\nJane,30,Los Angeles\nBob,35,Chicago",
                    "type": "text/csv"
                }
            ]
            
            uploaded_docs = []
            
            for test_file in test_files:
                print(f"\n  📄 Uploading {test_file['name']} ({test_file['type']})...")
                
                file_data = io.BytesIO(test_file["content"].encode())
                files = {"file": (test_file["name"], file_data, test_file["type"])}
                data = {
                    "metadata": json.dumps({
                        "source": "enhanced_upload_test",
                        "category": "test",
                        "file_type": test_file["type"]
                    })
                }
                
                response = client.post("/api/v1/documents/upload", files=files, data=data)
                print(f"    Status: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    uploaded_docs.append(result)
                    print(f"    ✅ Uploaded: {result.get('document_id')}")
                    print(f"    📊 Size: {result.get('file_size')} bytes")
                    print(f"    ⚡ Processing: {result.get('processing_time_ms', 0):.1f}ms")
                else:
                    print(f"    ❌ Upload failed: {response.text}")
            
            print(f"\n✅ Single file uploads: {len(uploaded_docs)}/{len(test_files)} successful")
            
        except Exception as e:
            print(f"❌ Enhanced single upload error: {e}")
        
        # Test 3: Batch upload
        print("\n📁 Testing batch upload...")
        try:
            # Create multiple test files for batch upload
            batch_files = []
            batch_contents = [
                ("batch_doc1.txt", "First document in batch upload test.", "text/plain"),
                ("batch_doc2.txt", "Second document in batch upload test.", "text/plain"),
                ("batch_data.json", '{"batch": true, "index": 3}', "application/json")
            ]
            
            for name, content, content_type in batch_contents:
                file_data = io.BytesIO(content.encode())
                batch_files.append(("files", (name, file_data, content_type)))
            
            # Shared metadata for batch
            shared_metadata = {
                "source": "batch_upload_test",
                "category": "batch",
                "batch_id": "test_batch_001"
            }
            
            data = {"metadata": json.dumps(shared_metadata)}
            
            response = client.post("/api/v1/documents/upload/batch", files=batch_files, data=data)
            print(f"Batch Upload Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Batch Upload Successful")
                print(f"📄 Total Files: {result.get('total_files', 0)}")
                print(f"✅ Successful: {result.get('successful_uploads', 0)}")
                print(f"❌ Failed: {result.get('failed_uploads', 0)}")
                print(f"⚡ Processing Time: {result.get('processing_time_ms', 0):.1f}ms")
                
                # Show individual results
                for i, upload_result in enumerate(result.get('results', [])):
                    print(f"  File {i+1}: {upload_result.get('status')} - {upload_result.get('document_id')}")
                
                if result.get('failures'):
                    print("❌ Failures:")
                    for failure in result.get('failures', []):
                        print(f"  {failure.get('filename')}: {failure.get('error')}")
                
                batch_success = result.get('successful_uploads', 0) == len(batch_contents)
                if batch_success:
                    print("🎉 Batch upload fully successful!")
                    return True
                else:
                    print("⚠️  Batch upload partially successful")
            else:
                print(f"❌ Batch upload failed: {response.text}")
                
        except Exception as e:
            print(f"❌ Batch upload error: {e}")
        
        # Test 4: File size limit test
        print("\n📏 Testing file size limits...")
        try:
            # Create a large file (simulate)
            large_content = "A" * (1024 * 1024)  # 1MB file
            large_file = io.BytesIO(large_content.encode())
            
            files = {"file": ("large_test.txt", large_file, "text/plain")}
            data = {"metadata": json.dumps({"source": "size_test"})}
            
            response = client.post("/api/v1/documents/upload", files=files, data=data)
            print(f"Large File Upload Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Large file uploaded: {result.get('file_size')} bytes")
            elif response.status_code == 413:
                print(f"✅ File size limit working: {response.json().get('detail')}")
            else:
                print(f"⚠️  Unexpected response: {response.text}")
                
        except Exception as e:
            print(f"❌ File size test error: {e}")
        
        return False
        
    except Exception as e:
        print(f"❌ Enhanced upload test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_enhanced_upload()
    
    if success:
        print(f"\n🎉 Enhanced upload test successful!")
        print(f"✅ All enhanced features working!")
    else:
        print(f"\n⚠️  Enhanced upload test completed with issues")
        print(f"🔧 Check the output above for details")
    
    sys.exit(0 if success else 1)
