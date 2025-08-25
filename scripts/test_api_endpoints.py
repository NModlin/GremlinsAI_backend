#!/usr/bin/env python3
"""
Test API Endpoints

Test the RAG system API endpoints using FastAPI TestClient.
"""

import sys
from pathlib import Path
import json
import io

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_api_endpoints():
    """Test the API endpoints."""
    print("=" * 50)
    print("🌐 API Endpoints Test")
    print("=" * 50)
    
    try:
        from fastapi.testclient import TestClient
        
        # Import just the documents router for testing
        print("📦 Importing documents router...")
        from app.api.v1.endpoints.documents import router
        from fastapi import FastAPI
        
        # Create a minimal test app
        test_app = FastAPI()
        test_app.include_router(router, prefix="/api/v1/documents")
        
        client = TestClient(test_app)
        print("✅ Test client created")
        
        # Test 1: System status endpoint
        print("\n🔍 Testing system status endpoint...")
        try:
            response = client.get("/api/v1/documents/system/status")
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ System Status: {data.get('status', 'unknown')}")
                print(f"📊 Vector Store Connected: {data.get('vector_store', {}).get('connected', False)}")
                print(f"🤖 LLM Available: {data.get('llm_status', {}).get('available', False)}")
            else:
                print(f"❌ Status endpoint failed: {response.text}")
                
        except Exception as e:
            print(f"❌ Status endpoint error: {e}")
        
        # Test 2: Document creation endpoint
        print("\n📄 Testing document creation endpoint...")
        try:
            test_doc = {
                "title": "API Test Document",
                "content": "This is a test document created via the API to verify RAG system functionality.",
                "content_type": "text/plain",
                "doc_metadata": {"source": "api_test", "category": "testing"},
                "tags": ["test", "api"],
                "chunk_size": 1000,
                "chunk_overlap": 200
            }
            
            response = client.post("/api/v1/documents/", json=test_doc)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                doc_id = data.get("id")
                print(f"✅ Document created: {doc_id}")
                print(f"📝 Title: {data.get('title')}")
                
                # Test 3: RAG query endpoint
                print("\n🤖 Testing RAG query endpoint...")
                try:
                    rag_query = {
                        "query": "What is this document about?",
                        "search_limit": 3,
                        "score_threshold": 0.1,
                        "search_type": "chunks",
                        "use_multi_agent": False,
                        "save_conversation": False
                    }
                    
                    rag_response = client.post("/api/v1/documents/rag", json=rag_query)
                    print(f"RAG Status Code: {rag_response.status_code}")
                    
                    if rag_response.status_code == 200:
                        rag_data = rag_response.json()
                        print(f"✅ RAG query successful")
                        print(f"🔍 Query: {rag_data.get('query')}")
                        print(f"💬 Answer: {rag_data.get('answer', '')[:150]}...")
                        print(f"📄 Sources found: {len(rag_data.get('sources', []))}")
                        print(f"🧠 Context used: {rag_data.get('context_used', False)}")
                        
                        if rag_data.get('context_used', False):
                            print(f"🎉 End-to-end RAG system working via API!")
                            return True
                        else:
                            print(f"⚠️  RAG working but no context used")
                    else:
                        print(f"❌ RAG query failed: {rag_response.text}")
                        
                except Exception as e:
                    print(f"❌ RAG query error: {e}")
                    
            else:
                print(f"❌ Document creation failed: {response.text}")
                
        except Exception as e:
            print(f"❌ Document creation error: {e}")
        
        # Test 4: Document upload endpoint (file upload)
        print("\n📁 Testing document upload endpoint...")
        try:
            # Create a test file in memory
            test_content = "This is a test file uploaded via the API. It contains information about machine learning and artificial intelligence for testing the RAG system."
            test_file = io.BytesIO(test_content.encode())
            
            files = {"file": ("test_upload.txt", test_file, "text/plain")}
            data = {"metadata": json.dumps({"source": "file_upload", "category": "test"})}
            
            upload_response = client.post("/api/v1/documents/upload", files=files, data=data)
            print(f"Upload Status Code: {upload_response.status_code}")
            
            if upload_response.status_code == 200:
                upload_data = upload_response.json()
                print(f"✅ File uploaded: {upload_data.get('document_id')}")
                print(f"📁 Title: {upload_data.get('title')}")
                print(f"📊 File size: {upload_data.get('file_size')} bytes")
                print(f"🧩 Chunks created: {upload_data.get('chunks_created')}")
                print(f"⚡ Processing time: {upload_data.get('processing_time_ms'):.1f}ms")
            else:
                print(f"❌ File upload failed: {upload_response.text}")
                
        except Exception as e:
            print(f"❌ File upload error: {e}")
        
        return False
        
    except Exception as e:
        print(f"❌ API endpoints test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_api_endpoints()
    
    if success:
        print(f"\n🎉 API endpoints test successful!")
        print(f"✅ Complete RAG system working via API!")
    else:
        print(f"\n⚠️  API endpoints test completed with issues")
        print(f"🔧 Check the output above for details")
    
    sys.exit(0 if success else 1)
