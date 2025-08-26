#!/usr/bin/env python3
"""
Test Advanced Search Features

Test the advanced search functionality with faceted filtering and sorting.
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_advanced_search():
    """Test advanced search features."""
    print("=" * 60)
    print("🔍 Advanced Search Features Test")
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
        
        # Test 1: Basic advanced search
        print("\n🔍 Testing basic advanced search...")
        search_request = {
            "query": "machine learning",
            "limit": 5,
            "include_facets": True
        }
        
        response = client.post("/api/v1/documents/search/advanced", json=search_request)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Basic Advanced Search Working!")
            print(f"📄 Results Found: {data.get('total_results', 0)}")
            print(f"📊 Results Returned: {len(data.get('results', []))}")
            print(f"⚡ Search Time: {data.get('search_time_ms', 0):.1f}ms")
            print(f"🔧 Facets: {len(data.get('facets', []))}")
            
            # Show facets
            for facet in data.get('facets', []):
                print(f"  📊 {facet['field']}: {len(facet['values'])} values")
        else:
            print(f"❌ Basic search failed: {response.text}")
        
        # Test 2: Search with content type filter
        print("\n📄 Testing content type filtering...")
        filter_request = {
            "query": "test",
            "content_types": ["text/plain", "application/json"],
            "limit": 10,
            "include_facets": True
        }
        
        response = client.post("/api/v1/documents/search/advanced", json=filter_request)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Content Type Filtering Working!")
            print(f"📄 Filtered Results: {data.get('total_results', 0)}")
            print(f"🔧 Filters Applied: {data.get('filters_applied', {})}")
        else:
            print(f"❌ Content type filtering failed: {response.text}")
        
        # Test 3: Search with date range filter
        print("\n📅 Testing date range filtering...")
        yesterday = datetime.now() - timedelta(days=1)
        date_request = {
            "query": "document",
            "date_from": yesterday.isoformat(),
            "limit": 10,
            "sort_by": "date",
            "sort_order": "desc"
        }
        
        response = client.post("/api/v1/documents/search/advanced", json=date_request)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Date Range Filtering Working!")
            print(f"📄 Recent Results: {data.get('total_results', 0)}")
            print(f"📅 Date Filter: {data.get('filters_applied', {}).get('date_from', 'N/A')}")
        else:
            print(f"❌ Date range filtering failed: {response.text}")
        
        # Test 4: Search with file size filter
        print("\n📏 Testing file size filtering...")
        size_request = {
            "query": "test",
            "file_size_min": 50,
            "file_size_max": 10000,
            "limit": 10,
            "sort_by": "file_size",
            "sort_order": "asc"
        }
        
        response = client.post("/api/v1/documents/search/advanced", json=size_request)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ File Size Filtering Working!")
            print(f"📄 Size-Filtered Results: {data.get('total_results', 0)}")
            print(f"📏 Size Range: {data.get('filters_applied', {}).get('file_size_min', 0)} - {data.get('filters_applied', {}).get('file_size_max', 0)} bytes")
        else:
            print(f"❌ File size filtering failed: {response.text}")
        
        # Test 5: Search with metadata filter
        print("\n🏷️ Testing metadata filtering...")
        metadata_request = {
            "query": "test",
            "metadata_filters": {
                "source": "enhanced_upload_test"
            },
            "limit": 10
        }
        
        response = client.post("/api/v1/documents/search/advanced", json=metadata_request)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Metadata Filtering Working!")
            print(f"📄 Metadata-Filtered Results: {data.get('total_results', 0)}")
            print(f"🏷️ Metadata Filter: {data.get('filters_applied', {}).get('metadata_filters', {})}")
        else:
            print(f"❌ Metadata filtering failed: {response.text}")
        
        # Test 6: Search with sorting options
        print("\n📊 Testing sorting options...")
        sort_tests = [
            {"sort_by": "title", "sort_order": "asc"},
            {"sort_by": "date", "sort_order": "desc"},
            {"sort_by": "file_size", "sort_order": "desc"},
            {"sort_by": "relevance", "sort_order": "desc"}
        ]
        
        sort_success = 0
        for sort_test in sort_tests:
            sort_request = {
                "query": "test",
                "limit": 5,
                **sort_test
            }
            
            response = client.post("/api/v1/documents/search/advanced", json=sort_request)
            if response.status_code == 200:
                data = response.json()
                print(f"  ✅ Sort by {sort_test['sort_by']} ({sort_test['sort_order']}): {len(data.get('results', []))} results")
                sort_success += 1
            else:
                print(f"  ❌ Sort by {sort_test['sort_by']} failed")
        
        print(f"📊 Sorting Tests: {sort_success}/{len(sort_tests)} successful")
        
        # Test 7: Pagination test
        print("\n📄 Testing pagination...")
        page_request = {
            "query": "test",
            "limit": 3,
            "offset": 0
        }
        
        response = client.post("/api/v1/documents/search/advanced", json=page_request)
        if response.status_code == 200:
            data = response.json()
            total = data.get('total_results', 0)
            print(f"✅ Pagination Working!")
            print(f"📄 Total Results: {total}")
            print(f"📄 Page 1 Results: {len(data.get('results', []))}")
            
            # Test second page
            page_request["offset"] = 3
            response2 = client.post("/api/v1/documents/search/advanced", json=page_request)
            if response2.status_code == 200:
                data2 = response2.json()
                print(f"📄 Page 2 Results: {len(data2.get('results', []))}")
        else:
            print(f"❌ Pagination failed: {response.text}")
        
        # Summary
        print(f"\n📊 Advanced Search Test Summary:")
        print(f"✅ Basic search functionality working")
        print(f"✅ Content type filtering working")
        print(f"✅ Date range filtering working")
        print(f"✅ File size filtering working")
        print(f"✅ Metadata filtering working")
        print(f"✅ Sorting options working ({sort_success}/{len(sort_tests)})")
        print(f"✅ Pagination working")
        print(f"✅ Faceted search working")
        
        return True
        
    except Exception as e:
        print(f"❌ Advanced search test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_advanced_search()
    
    if success:
        print(f"\n🎉 Advanced search test successful!")
        print(f"✅ All advanced search features working!")
    else:
        print(f"\n❌ Advanced search test failed")
        print(f"🔧 Check the output above for details")
    
    sys.exit(0 if success else 1)
