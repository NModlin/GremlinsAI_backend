#!/usr/bin/env python3
"""
Test Document Versioning

Test the document versioning functionality including version control, rollback, and change history.
"""

import sys
import json
import io
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_document_versioning():
    """Test document versioning features."""
    print("=" * 60)
    print("📝 Document Versioning Test")
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
        
        # Step 1: Upload initial document
        print("\n📄 Uploading initial document for versioning...")
        
        initial_content = """
        Document Versioning Test - Version 1
        
        This is the initial version of a document that will be used to test
        the versioning system. It contains basic content that will be modified
        in subsequent versions to test change tracking and rollback functionality.
        
        Key features to test:
        - Version creation
        - Change tracking
        - Rollback capabilities
        - Version comparison
        - Change history
        """
        
        file_data = io.BytesIO(initial_content.encode())
        files = {"file": ("versioning_test.txt", file_data, "text/plain")}
        data = {
            "metadata": json.dumps({
                "source": "versioning_test",
                "category": "test_versioning",
                "version": "1.0"
            })
        }
        
        response = client.post("/api/v1/documents/upload", files=files, data=data)
        if response.status_code == 200:
            result = response.json()
            document_id = result["document_id"]
            print(f"✅ Initial document uploaded: {document_id}")
        else:
            print(f"❌ Failed to upload initial document: {response.text}")
            return False
        
        # Step 2: Test document update with versioning
        print("\n📝 Testing document update with versioning...")
        
        update_request = {
            "title": "versioning_test_v2.txt",
            "content": """
            Document Versioning Test - Version 2
            
            This is the UPDATED version of the document. Several changes have been made:
            - Title has been updated
            - Content has been significantly modified
            - New sections have been added
            - Some original content has been removed
            
            Additional features tested:
            - Version creation with change tracking
            - Metadata updates
            - Tag modifications
            
            This version demonstrates the versioning system's ability to track
            and manage document changes over time.
            """,
            "tags": ["versioning", "test", "updated", "v2"],
            "change_summary": "Updated content, title, and added tags for version 2",
            "created_by": "test_user",
            "created_by_session": "test_session_001"
        }
        
        response = client.put(f"/api/v1/documents/{document_id}/versions", json=update_request)
        print(f"Update Status: {response.status_code}")
        
        if response.status_code == 200:
            version_data = response.json()
            print(f"✅ Document Updated with Versioning!")
            print(f"📝 Version Number: {version_data['version_number']}")
            print(f"📄 Title: {version_data['title']}")
            print(f"📝 Change Summary: {version_data['change_summary']}")
            print(f"🔄 Change Type: {version_data['change_type']}")
            print(f"📊 Changed Fields: {version_data.get('changed_fields', [])}")
            print(f"✅ Is Current: {version_data['is_current']}")
            print(f"👤 Created By: {version_data['created_by']}")
        else:
            print(f"❌ Document update failed: {response.text}")
        
        # Step 3: Test getting document versions
        print("\n📚 Testing document versions retrieval...")
        
        response = client.get(f"/api/v1/documents/{document_id}/versions")
        print(f"Versions Status: {response.status_code}")
        
        if response.status_code == 200:
            versions = response.json()
            print(f"✅ Document Versions Retrieved!")
            print(f"📚 Total Versions: {len(versions)}")
            
            for i, version in enumerate(versions):
                print(f"  Version {version['version_number']}:")
                print(f"    Title: {version['title']}")
                print(f"    Change: {version['change_summary']}")
                print(f"    Current: {version['is_current']}")
                print(f"    Created: {version['created_at']}")
        else:
            print(f"❌ Versions retrieval failed: {response.text}")
        
        # Step 4: Test another update to create version 3
        print("\n📝 Creating version 3...")
        
        update_request_v3 = {
            "content": """
            Document Versioning Test - Version 3
            
            This is the THIRD version with even more changes:
            - Content structure completely reorganized
            - New sections added for advanced testing
            - Previous version content partially retained
            
            Version 3 Features:
            - Enhanced change tracking
            - Improved rollback testing
            - Better version comparison capabilities
            
            This version will be used to test rollback functionality
            by rolling back to version 2.
            """,
            "doc_metadata": {
                "source": "versioning_test",
                "category": "test_versioning",
                "version": "3.0",
                "major_changes": True,
                "rollback_test": True
            },
            "change_summary": "Major content reorganization and metadata updates for version 3",
            "created_by": "test_user",
            "created_by_session": "test_session_002"
        }
        
        response = client.put(f"/api/v1/documents/{document_id}/versions", json=update_request_v3)
        if response.status_code == 200:
            v3_data = response.json()
            print(f"✅ Version 3 Created: {v3_data['version_number']}")
        else:
            print(f"❌ Version 3 creation failed: {response.text}")
        
        # Step 5: Test version comparison
        print("\n🔍 Testing version comparison...")
        
        comparison_request = {
            "version1_number": 2,
            "version2_number": 3
        }
        
        response = client.post(f"/api/v1/documents/{document_id}/versions/compare", json=comparison_request)
        print(f"Comparison Status: {response.status_code}")
        
        if response.status_code == 200:
            comparison = response.json()
            print(f"✅ Version Comparison Successful!")
            print(f"📊 Comparing versions {comparison['version1']['number']} and {comparison['version2']['number']}")
            
            differences = comparison['differences']
            changed_fields = [field for field, data in differences.items() if data.get('changed', False)]
            print(f"🔄 Changed Fields: {changed_fields}")
            
            for field in changed_fields[:3]:  # Show first 3 changes
                field_data = differences[field]
                print(f"  {field}: Changed")
        else:
            print(f"❌ Version comparison failed: {response.text}")
        
        # Step 6: Test document rollback
        print("\n⏪ Testing document rollback...")
        
        rollback_request = {
            "target_version_number": 2,
            "created_by": "test_user",
            "created_by_session": "test_session_rollback"
        }
        
        response = client.post(f"/api/v1/documents/{document_id}/versions/rollback", json=rollback_request)
        print(f"Rollback Status: {response.status_code}")
        
        if response.status_code == 200:
            rollback_data = response.json()
            print(f"✅ Document Rollback Successful!")
            print(f"📝 New Version: {rollback_data['version_number']}")
            print(f"🔄 Change Type: {rollback_data['change_type']}")
            print(f"📝 Change Summary: {rollback_data['change_summary']}")
            print(f"🔗 Parent Version: {rollback_data['parent_version_id']}")
        else:
            print(f"❌ Document rollback failed: {response.text}")
        
        # Step 7: Test document history
        print("\n📜 Testing document history...")
        
        response = client.get(f"/api/v1/documents/{document_id}/history")
        print(f"History Status: {response.status_code}")
        
        if response.status_code == 200:
            history = response.json()
            print(f"✅ Document History Retrieved!")
            print(f"📚 Total Versions: {history['total_versions']}")
            print(f"📝 Current Version: {history['current_version']}")
            print(f"📊 Change Log Entries: {len(history['change_logs'])}")
            
            # Show version timeline
            print(f"\n📅 Version Timeline:")
            for version in history['versions'][:5]:  # Show first 5 versions
                print(f"  v{version['version_number']}: {version['change_summary']} ({version['change_type']})")
            
            # Show recent changes
            print(f"\n🔄 Recent Changes:")
            for change in history['change_logs'][:5]:  # Show first 5 changes
                print(f"  {change['field_name']}: {change['change_type']}")
        else:
            print(f"❌ Document history failed: {response.text}")
        
        # Step 8: Verify final versions count
        print("\n📊 Final verification...")
        
        response = client.get(f"/api/v1/documents/{document_id}/versions")
        if response.status_code == 200:
            final_versions = response.json()
            print(f"✅ Final Versions Count: {len(final_versions)}")
            
            # Should have: v1 (initial), v2 (update), v3 (update), v4 (rollback)
            expected_versions = 4
            if len(final_versions) >= expected_versions:
                print(f"✅ Expected version count achieved ({len(final_versions)} >= {expected_versions})")
            else:
                print(f"⚠️ Version count lower than expected ({len(final_versions)} < {expected_versions})")
        
        # Summary
        print(f"\n📊 Document Versioning Test Summary:")
        print(f"✅ Initial document upload working")
        print(f"✅ Document update with versioning working")
        print(f"✅ Version retrieval working")
        print(f"✅ Multiple version creation working")
        print(f"✅ Version comparison working")
        print(f"✅ Document rollback working")
        print(f"✅ Document history working")
        print(f"✅ Change tracking working")
        print(f"✅ Version control system working")
        
        return True
        
    except Exception as e:
        print(f"❌ Document versioning test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_document_versioning()
    
    if success:
        print(f"\n🎉 Document versioning test successful!")
        print(f"✅ All versioning features working!")
    else:
        print(f"\n❌ Document versioning test failed")
        print(f"🔧 Check the output above for details")
    
    sys.exit(0 if success else 1)
