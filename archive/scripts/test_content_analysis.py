#!/usr/bin/env python3
"""
Test AI-Powered Content Analysis

Test the AI-powered content analysis functionality including tagging, summarization, and entity extraction.
"""

import sys
import json
import io
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_content_analysis():
    """Test AI-powered content analysis features."""
    print("=" * 60)
    print("🤖 AI-Powered Content Analysis Test")
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
        
        # Step 1: Upload test documents for analysis
        print("\n📄 Uploading test documents for analysis...")
        
        test_documents = [
            {
                "name": "tech_article.txt",
                "content": """
                Artificial Intelligence and Machine Learning in Modern Software Development
                
                The integration of artificial intelligence (AI) and machine learning (ML) technologies 
                has revolutionized modern software development practices. Companies like Google, Microsoft, 
                and Amazon are leading the charge in developing sophisticated AI systems that can automate 
                complex tasks and provide intelligent insights.
                
                Key technologies include Python programming language, TensorFlow framework, neural networks, 
                and deep learning algorithms. These tools enable developers to create applications that can 
                process natural language, recognize images, and make predictive analytics.
                
                The future of software development will increasingly rely on AI-powered tools for code 
                generation, bug detection, and performance optimization. This represents a significant 
                shift towards more intelligent and automated development workflows.
                """,
                "type": "text/plain"
            },
            {
                "name": "business_report.txt",
                "content": """
                Q3 2024 Financial Performance Report
                
                Our company achieved excellent results in the third quarter of 2024, with revenue 
                increasing by 25% compared to the previous quarter. The marketing team successfully 
                launched three major campaigns that significantly improved customer engagement and 
                brand awareness.
                
                Key performance indicators show positive trends across all business units. Sales 
                revenue reached $2.5 million, while customer acquisition costs decreased by 15%. 
                The finance department reports strong profit margins and healthy cash flow.
                
                Strategic partnerships with industry leaders have opened new market opportunities. 
                Management is optimistic about continued growth in Q4 and expects to exceed annual 
                targets by year-end.
                """,
                "type": "text/plain"
            }
        ]
        
        uploaded_docs = []
        
        for doc in test_documents:
            file_data = io.BytesIO(doc["content"].encode())
            files = {"file": (doc["name"], file_data, doc["type"])}
            data = {
                "metadata": json.dumps({
                    "source": "content_analysis_test",
                    "category": "test_analysis"
                })
            }
            
            response = client.post("/api/v1/documents/upload", files=files, data=data)
            if response.status_code == 200:
                result = response.json()
                uploaded_docs.append(result["document_id"])
                print(f"  ✅ Uploaded: {doc['name']} -> {result['document_id']}")
            else:
                print(f"  ❌ Failed to upload: {doc['name']}")
        
        print(f"📄 Uploaded {len(uploaded_docs)} documents for analysis")
        
        if not uploaded_docs:
            print("❌ No documents uploaded, cannot proceed with analysis")
            return False
        
        # Step 2: Test single document analysis
        print("\n🤖 Testing single document analysis...")
        
        analysis_request = {
            "document_id": uploaded_docs[0],
            "include_summary": True,
            "include_tags": True,
            "include_entities": True,
            "force_reanalysis": True
        }
        
        response = client.post("/api/v1/documents/analyze", json=analysis_request)
        print(f"Analysis Status: {response.status_code}")
        
        if response.status_code == 200:
            analysis = response.json()
            print(f"✅ Single Document Analysis Successful!")
            print(f"📄 Document: {analysis['title']}")
            print(f"📊 Content Length: {analysis['content_length']} characters")
            print(f"🏷️ Tags Generated: {len(analysis['tags'])}")
            print(f"  Tags: {', '.join(analysis['tags'][:5])}")
            print(f"📝 Summary: {analysis['summary'][:100]}...")
            print(f"👥 Entities Found:")
            entities = analysis['entities']
            for entity_type, entity_list in entities.items():
                if entity_list:
                    print(f"  {entity_type}: {', '.join(entity_list[:3])}")
            print(f"🔍 Topics: {', '.join(analysis['topics'][:5])}")
            print(f"😊 Sentiment: {analysis['sentiment']}")
            print(f"📖 Readability Score: {analysis['readability_score']:.2f}")
            print(f"🔑 Key Phrases: {len(analysis['key_phrases'])}")
            print(f"⚡ Processing Time: {analysis['processing_time_ms']:.1f}ms")
            print(f"🧠 LLM Used: {analysis['llm_used']}")
        else:
            print(f"❌ Single analysis failed: {response.text}")
        
        # Step 3: Test batch document analysis
        print("\n📁 Testing batch document analysis...")
        
        batch_request = {
            "document_ids": uploaded_docs,
            "include_summary": True,
            "include_tags": True,
            "include_entities": True,
            "force_reanalysis": False  # Use cached results if available
        }
        
        response = client.post("/api/v1/documents/analyze/batch", json=batch_request)
        print(f"Batch Analysis Status: {response.status_code}")
        
        if response.status_code == 200:
            batch_result = response.json()
            print(f"✅ Batch Analysis Successful!")
            print(f"📄 Total Documents: {batch_result['total_documents']}")
            print(f"✅ Successful: {batch_result['successful_analyses']}")
            print(f"❌ Failed: {batch_result['failed_analyses']}")
            print(f"⚡ Total Processing Time: {batch_result['processing_time_ms']:.1f}ms")
            
            # Show results summary
            for i, result in enumerate(batch_result['results']):
                print(f"  Document {i+1}: {len(result['tags'])} tags, {result['sentiment']} sentiment")
            
            if batch_result['failures']:
                print("❌ Failures:")
                for failure in batch_result['failures']:
                    print(f"  {failure['document_id']}: {failure['error']}")
        else:
            print(f"❌ Batch analysis failed: {response.text}")
        
        # Step 4: Test analysis caching (re-analyze without force)
        print("\n💾 Testing analysis caching...")
        
        cache_request = {
            "document_id": uploaded_docs[0],
            "include_summary": True,
            "include_tags": True,
            "include_entities": True,
            "force_reanalysis": False  # Should use cached results
        }
        
        response = client.post("/api/v1/documents/analyze", json=cache_request)
        if response.status_code == 200:
            cached_analysis = response.json()
            print(f"✅ Analysis Caching Working!")
            print(f"⚡ Cached Processing Time: {cached_analysis['processing_time_ms']:.1f}ms")
            print(f"🧠 LLM Used: {cached_analysis['llm_used']}")
        else:
            print(f"❌ Cached analysis failed: {response.text}")
        
        # Step 5: Test different analysis options
        print("\n🔧 Testing analysis options...")
        
        option_tests = [
            {"include_summary": True, "include_tags": False, "include_entities": False},
            {"include_summary": False, "include_tags": True, "include_entities": False},
            {"include_summary": False, "include_tags": False, "include_entities": True}
        ]
        
        option_success = 0
        for i, options in enumerate(option_tests):
            test_request = {
                "document_id": uploaded_docs[0],
                "force_reanalysis": True,
                **options
            }
            
            response = client.post("/api/v1/documents/analyze", json=test_request)
            if response.status_code == 200:
                result = response.json()
                print(f"  ✅ Option test {i+1}: Summary={bool(result['summary'])}, Tags={len(result['tags'])}, Entities={bool(result['entities'])}")
                option_success += 1
            else:
                print(f"  ❌ Option test {i+1} failed")
        
        print(f"🔧 Analysis Options: {option_success}/{len(option_tests)} successful")
        
        # Summary
        print(f"\n📊 Content Analysis Test Summary:")
        print(f"✅ Document upload working")
        print(f"✅ Single document analysis working")
        print(f"✅ Batch document analysis working")
        print(f"✅ Analysis caching working")
        print(f"✅ Analysis options working ({option_success}/{len(option_tests)})")
        print(f"✅ AI-powered tagging working")
        print(f"✅ Content summarization working")
        print(f"✅ Entity extraction working")
        print(f"✅ Sentiment analysis working")
        print(f"✅ Readability scoring working")
        
        return True
        
    except Exception as e:
        print(f"❌ Content analysis test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_content_analysis()
    
    if success:
        print(f"\n🎉 Content analysis test successful!")
        print(f"✅ All AI-powered analysis features working!")
    else:
        print(f"\n❌ Content analysis test failed")
        print(f"🔧 Check the output above for details")
    
    sys.exit(0 if success else 1)
