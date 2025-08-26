#!/usr/bin/env python3
"""
Test API with Real Server

Test the API endpoints by making HTTP requests to a running server.
"""

import sys
import time
import requests
import json
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

def wait_for_server(url="http://localhost:8000", timeout=30):
    """Wait for the server to be ready."""
    print(f"⏳ Waiting for server at {url}...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                print(f"✅ Server is ready!")
                return True
        except requests.exceptions.RequestException:
            pass
        
        time.sleep(2)
    
    print(f"❌ Server not ready after {timeout} seconds")
    return False

def test_api_with_server():
    """Test API endpoints with a real server."""
    print("=" * 50)
    print("🌐 API with Real Server Test")
    print("=" * 50)
    
    base_url = "http://localhost:8000"
    
    # Check if server is running
    if not wait_for_server(base_url):
        print("❌ Server is not running. Please start it with:")
        print("   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000")
        return False
    
    try:
        # Test 1: Health check
        print("\n🔍 Testing health endpoint...")
        response = requests.get(f"{base_url}/health")
        print(f"Health Status: {response.status_code}")
        if response.status_code == 200:
            print(f"✅ Health check passed")
        
        # Test 2: System status
        print("\n🔍 Testing system status endpoint...")
        response = requests.get(f"{base_url}/api/v1/documents/system/status")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ System Status: {data.get('status')}")
            print(f"📊 Total Documents: {data.get('total_documents')}")
            print(f"🔗 Vector Store Connected: {data.get('vector_store', {}).get('connected')}")
            print(f"🧠 LLM Available: {data.get('configuration', {}).get('llm_status', {}).get('available')}")
        else:
            print(f"❌ System status failed: {response.text}")
        
        # Test 3: Document creation
        print("\n📄 Testing document creation endpoint...")
        doc_data = {
            "title": "API Server Test Document",
            "content": "This is a test document created via the API server to verify the RAG system works end-to-end.",
            "content_type": "text/plain",
            "doc_metadata": {"source": "api_server_test", "category": "testing"},
            "tags": ["test", "api", "server"],
            "chunk_size": 1000,
            "chunk_overlap": 200
        }
        
        response = requests.post(f"{base_url}/api/v1/documents/", json=doc_data)
        print(f"Document Creation Status: {response.status_code}")
        
        if response.status_code == 200:
            doc_response = response.json()
            doc_id = doc_response.get("id")
            print(f"✅ Document created: {doc_id}")
            print(f"📝 Title: {doc_response.get('title')}")
            
            # Test 4: RAG query
            print("\n🤖 Testing RAG query endpoint...")
            rag_data = {
                "query": "What is this document about?",
                "search_limit": 3,
                "score_threshold": 0.1,
                "search_type": "chunks",
                "use_multi_agent": False,
                "save_conversation": False
            }
            
            rag_response = requests.post(f"{base_url}/api/v1/documents/rag", json=rag_data)
            print(f"RAG Query Status: {rag_response.status_code}")
            
            if rag_response.status_code == 200:
                rag_result = rag_response.json()
                print(f"✅ RAG query successful!")
                print(f"🔍 Query: {rag_result.get('query')}")
                print(f"💬 Answer: {rag_result.get('answer', '')[:150]}...")
                print(f"📄 Sources: {len(rag_result.get('sources', []))}")
                print(f"🧠 Context used: {rag_result.get('context_used', False)}")
                
                if rag_result.get('context_used', False) and len(rag_result.get('sources', [])) > 0:
                    print(f"🎉 End-to-end RAG system working via API server!")
                    return True
                else:
                    print(f"⚠️  RAG working but no context/sources found")
            else:
                print(f"❌ RAG query failed: {rag_response.text}")
        else:
            print(f"❌ Document creation failed: {response.text}")
        
        # Test 5: File upload
        print("\n📁 Testing file upload endpoint...")
        test_content = "This is a test file uploaded to verify the RAG system can process uploaded documents."
        files = {"file": ("test_upload.txt", test_content, "text/plain")}
        data = {"metadata": json.dumps({"source": "file_upload_test", "category": "test"})}
        
        upload_response = requests.post(f"{base_url}/api/v1/documents/upload", files=files, data=data)
        print(f"File Upload Status: {upload_response.status_code}")
        
        if upload_response.status_code == 200:
            upload_result = upload_response.json()
            print(f"✅ File uploaded successfully")
            print(f"📁 Document ID: {upload_result.get('document_id')}")
            print(f"📄 Filename: {upload_result.get('filename')}")
        else:
            print(f"❌ File upload failed: {upload_response.text}")
        
        return False
        
    except Exception as e:
        print(f"❌ API server test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_api_with_server()
    
    if success:
        print(f"\n🎉 API server test successful!")
        print(f"✅ Complete RAG system working via API server!")
    else:
        print(f"\n⚠️  API server test completed with issues")
        print(f"🔧 Check the output above for details")
    
    sys.exit(0 if success else 1)
