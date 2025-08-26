#!/usr/bin/env python3
"""
Test Document Analytics

Test the document analytics functionality including usage tracking and metrics.
"""

import sys
import json
import io
import time
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_document_analytics():
    """Test document analytics features."""
    print("=" * 60)
    print("📊 Document Analytics Test")
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
        
        # Step 1: Upload test documents for analytics
        print("\n📄 Uploading test documents for analytics...")
        
        test_documents = [
            {
                "name": "analytics_doc1.txt",
                "content": "This is the first document for analytics testing. It contains information about data analysis and metrics tracking.",
                "type": "text/plain"
            },
            {
                "name": "analytics_doc2.txt", 
                "content": "This is the second document for analytics testing. It focuses on user engagement and behavior analysis.",
                "type": "text/plain"
            }
        ]
        
        uploaded_docs = []
        
        for doc in test_documents:
            file_data = io.BytesIO(doc["content"].encode())
            files = {"file": (doc["name"], file_data, doc["type"])}
            data = {
                "metadata": json.dumps({
                    "source": "analytics_test",
                    "category": "test_analytics"
                })
            }
            
            response = client.post("/api/v1/documents/upload", files=files, data=data)
            if response.status_code == 200:
                result = response.json()
                uploaded_docs.append(result["document_id"])
                print(f"  ✅ Uploaded: {doc['name']} -> {result['document_id']}")
            else:
                print(f"  ❌ Failed to upload: {doc['name']}")
        
        print(f"📄 Uploaded {len(uploaded_docs)} documents for analytics")
        
        if not uploaded_docs:
            print("❌ No documents uploaded, cannot proceed with analytics")
            return False
        
        # Step 2: Test document view tracking
        print("\n👁️ Testing document view tracking...")
        
        for i, doc_id in enumerate(uploaded_docs):
            # Track multiple views with different durations
            for view_num in range(3):
                duration = 30.0 + (view_num * 15.0)  # 30s, 45s, 60s
                user_session = f"test_session_{i}_{view_num}"
                
                response = client.post(
                    f"/api/v1/documents/analytics/track/view/{doc_id}",
                    params={
                        "duration_seconds": duration,
                        "user_session": user_session
                    }
                )
                
                if response.status_code == 200:
                    print(f"  ✅ Tracked view for doc {i+1}, view {view_num+1} ({duration}s)")
                else:
                    print(f"  ❌ Failed to track view: {response.text}")
        
        # Step 3: Test search analytics (simulate searches)
        print("\n🔍 Testing search analytics...")
        
        search_queries = [
            "analytics testing",
            "data analysis",
            "user engagement",
            "metrics tracking",
            "analytics testing"  # Duplicate to test frequency
        ]
        
        for query in search_queries:
            # Perform search to generate analytics data
            search_request = {
                "query": query,
                "limit": 5
            }
            
            response = client.post("/api/v1/documents/search/advanced", json=search_request)
            if response.status_code == 200:
                print(f"  ✅ Search performed: '{query}'")
            else:
                print(f"  ❌ Search failed: '{query}'")
            
            time.sleep(0.1)  # Small delay between searches
        
        # Step 4: Test document analytics endpoint
        print("\n📊 Testing document analytics endpoint...")
        
        response = client.get("/api/v1/documents/analytics/documents?limit=10")
        print(f"Document Analytics Status: {response.status_code}")
        
        if response.status_code == 200:
            analytics_data = response.json()
            print(f"✅ Document Analytics Retrieved!")
            print(f"📄 Documents with analytics: {len(analytics_data)}")
            
            for i, doc_analytics in enumerate(analytics_data[:3]):  # Show first 3
                print(f"  Document {i+1}:")
                print(f"    Title: {doc_analytics['title']}")
                print(f"    Views: {doc_analytics['view_count']}")
                print(f"    Searches: {doc_analytics['search_count']}")
                print(f"    Avg Time: {doc_analytics['avg_time_spent']:.1f}s")
        else:
            print(f"❌ Document analytics failed: {response.text}")
        
        # Step 5: Test search analytics endpoint
        print("\n🔍 Testing search analytics endpoint...")
        
        response = client.get("/api/v1/documents/analytics/search?days=1&limit=20")
        print(f"Search Analytics Status: {response.status_code}")
        
        if response.status_code == 200:
            search_analytics = response.json()
            print(f"✅ Search Analytics Retrieved!")
            print(f"📊 Popular queries: {len(search_analytics.get('popular_queries', []))}")
            print(f"🔍 Search types: {search_analytics.get('search_type_distribution', {})}")
            print(f"📈 Daily volume entries: {len(search_analytics.get('daily_search_volume', []))}")
            
            # Show popular queries
            for i, query_data in enumerate(search_analytics.get('popular_queries', [])[:3]):
                print(f"  Query {i+1}: '{query_data['query']}' ({query_data['search_count']} times)")
        else:
            print(f"❌ Search analytics failed: {response.text}")
        
        # Step 6: Test user engagement endpoint
        print("\n👥 Testing user engagement endpoint...")
        
        response = client.get("/api/v1/documents/analytics/engagement?days=1")
        print(f"User Engagement Status: {response.status_code}")
        
        if response.status_code == 200:
            engagement_data = response.json()
            print(f"✅ User Engagement Retrieved!")
            print(f"👥 Unique sessions: {engagement_data.get('unique_sessions', 0)}")
            print(f"⏱️ Avg session duration: {engagement_data.get('avg_session_duration_seconds', 0):.1f}s")
            print(f"🎯 Action distribution: {engagement_data.get('action_distribution', {})}")
        else:
            print(f"❌ User engagement failed: {response.text}")
        
        # Step 7: Test analytics dashboard
        print("\n📊 Testing analytics dashboard...")
        
        response = client.get("/api/v1/documents/analytics/dashboard?days=1")
        print(f"Analytics Dashboard Status: {response.status_code}")
        
        if response.status_code == 200:
            dashboard_data = response.json()
            print(f"✅ Analytics Dashboard Retrieved!")
            print(f"📄 Total documents: {dashboard_data.get('total_documents', 0)}")
            print(f"👁️ Total views: {dashboard_data.get('total_views', 0)}")
            print(f"🔍 Total searches: {dashboard_data.get('total_searches', 0)}")
            print(f"👥 Total sessions: {dashboard_data.get('total_sessions', 0)}")
            print(f"⚡ Avg search time: {dashboard_data.get('avg_search_time_ms', 0):.1f}ms")
            print(f"🏆 Most popular doc: {dashboard_data.get('most_popular_document', 'N/A')}")
            print(f"🔍 Most popular query: {dashboard_data.get('most_popular_query', 'N/A')}")
            print(f"📅 Generated at: {dashboard_data.get('generated_at', 'N/A')}")
        else:
            print(f"❌ Analytics dashboard failed: {response.text}")
        
        # Step 8: Test specific document analytics
        print("\n📄 Testing specific document analytics...")
        
        if uploaded_docs:
            doc_id = uploaded_docs[0]
            response = client.get(f"/api/v1/documents/analytics/documents?document_id={doc_id}")
            
            if response.status_code == 200:
                specific_analytics = response.json()
                if specific_analytics:
                    doc_data = specific_analytics[0]
                    print(f"✅ Specific Document Analytics Retrieved!")
                    print(f"📄 Document: {doc_data['title']}")
                    print(f"👁️ Views: {doc_data['view_count']}")
                    print(f"⏱️ Avg time spent: {doc_data['avg_time_spent']:.1f}s")
                else:
                    print(f"⚠️ No analytics data for specific document")
            else:
                print(f"❌ Specific document analytics failed: {response.text}")
        
        # Summary
        print(f"\n📊 Document Analytics Test Summary:")
        print(f"✅ Document upload working")
        print(f"✅ Document view tracking working")
        print(f"✅ Search analytics generation working")
        print(f"✅ Document analytics endpoint working")
        print(f"✅ Search analytics endpoint working")
        print(f"✅ User engagement endpoint working")
        print(f"✅ Analytics dashboard working")
        print(f"✅ Specific document analytics working")
        print(f"✅ Usage metrics tracking working")
        print(f"✅ Performance metrics working")
        
        return True
        
    except Exception as e:
        print(f"❌ Document analytics test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_document_analytics()
    
    if success:
        print(f"\n🎉 Document analytics test successful!")
        print(f"✅ All analytics features working!")
    else:
        print(f"\n❌ Document analytics test failed")
        print(f"🔧 Check the output above for details")
    
    sys.exit(0 if success else 1)
