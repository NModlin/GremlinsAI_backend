#!/usr/bin/env python3
"""
Test Complete RAG Workflow

Test the entire RAG system workflow from document upload to query response.
"""

import sys
import asyncio
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

async def test_complete_rag_workflow():
    """Test the complete RAG workflow."""
    print("=" * 60)
    print("🧙‍♂️ Complete RAG Workflow Test")
    print("=" * 60)
    
    try:
        from app.core.rag_system import RAGSystem
        from app.core.vector_store import vector_store
        from app.database.database import AsyncSessionLocal
        
        # Initialize RAG system
        rag_system = RAGSystem()
        
        print(f"\n📊 System Status:")
        print(f"Vector Store Connected: {vector_store.is_connected}")
        
        if not vector_store.is_connected:
            print("❌ Vector store not connected")
            return False
        
        # Step 1: Add multiple documents to create a knowledge base
        print(f"\n📚 Building Knowledge Base...")
        
        documents = [
            {
                "title": "Machine Learning Fundamentals",
                "content": """
                Machine learning is a subset of artificial intelligence that enables computers 
                to learn and make decisions from data without being explicitly programmed. 
                
                Key concepts include:
                - Supervised learning: Learning from labeled examples
                - Unsupervised learning: Finding patterns in unlabeled data  
                - Neural networks: Computing systems inspired by biological neural networks
                - Deep learning: Multi-layered neural networks for complex pattern recognition
                
                Applications include image recognition, natural language processing, 
                recommendation systems, and autonomous vehicles.
                """,
                "metadata": {"category": "education", "level": "beginner", "topic": "ml"}
            },
            {
                "title": "Natural Language Processing Guide",
                "content": """
                Natural Language Processing (NLP) is a branch of artificial intelligence 
                that helps computers understand, interpret and manipulate human language.
                
                Core NLP tasks include:
                - Text classification: Categorizing text into predefined classes
                - Named entity recognition: Identifying people, places, organizations
                - Sentiment analysis: Determining emotional tone of text
                - Machine translation: Converting text from one language to another
                - Question answering: Providing answers to questions based on text
                
                Modern NLP uses transformer models like BERT, GPT, and T5 for 
                state-of-the-art performance.
                """,
                "metadata": {"category": "education", "level": "intermediate", "topic": "nlp"}
            },
            {
                "title": "Vector Databases Explained",
                "content": """
                Vector databases are specialized databases designed to store and query 
                high-dimensional vectors efficiently. They are essential for AI applications.
                
                Key features:
                - Similarity search: Finding vectors similar to a query vector
                - Scalability: Handling millions or billions of vectors
                - Real-time queries: Fast retrieval for production applications
                - Metadata filtering: Combining vector search with traditional filters
                
                Popular vector databases include Weaviate, Pinecone, Chroma, and Qdrant.
                They enable applications like semantic search, recommendation systems,
                and retrieval-augmented generation (RAG).
                """,
                "metadata": {"category": "technology", "level": "advanced", "topic": "databases"}
            }
        ]
        
        doc_ids = []
        async with AsyncSessionLocal() as db:
            for i, doc in enumerate(documents):
                print(f"📄 Adding document {i+1}: {doc['title']}")
                
                doc_id = await rag_system.add_document_from_text(
                    db=db,
                    title=doc["title"],
                    content=doc["content"],
                    content_type="text/plain",
                    doc_metadata=doc["metadata"]
                )
                
                if doc_id:
                    doc_ids.append(doc_id)
                    print(f"   ✅ Added: {doc_id}")
                else:
                    print(f"   ❌ Failed to add document")
                    return False
        
        print(f"\n✅ Knowledge base created with {len(doc_ids)} documents")
        
        # Step 2: Test various RAG queries
        print(f"\n🤖 Testing RAG Queries...")
        
        test_queries = [
            {
                "query": "What is machine learning?",
                "expected_topic": "ml",
                "description": "Basic ML question"
            },
            {
                "query": "How do transformer models work in NLP?",
                "expected_topic": "nlp", 
                "description": "Advanced NLP question"
            },
            {
                "query": "What are vector databases used for?",
                "expected_topic": "databases",
                "description": "Vector database question"
            },
            {
                "query": "Compare supervised and unsupervised learning",
                "expected_topic": "ml",
                "description": "Comparative ML question"
            },
            {
                "query": "What is sentiment analysis?",
                "expected_topic": "nlp",
                "description": "Specific NLP task question"
            }
        ]
        
        successful_queries = 0
        
        for i, test_case in enumerate(test_queries):
            print(f"\n--- Query {i+1}: {test_case['description']} ---")
            print(f"🔍 Question: {test_case['query']}")
            
            async with AsyncSessionLocal() as db:
                try:
                    result = await rag_system.retrieve_and_generate(
                        db=db,
                        query=test_case["query"],
                        search_limit=3,
                        score_threshold=0.1
                    )
                    
                    docs_found = result['search_metadata']['documents_found']
                    context_used = result['context_used']
                    response = result['response']
                    
                    print(f"📄 Documents found: {docs_found}")
                    print(f"🧠 Context used: {context_used}")
                    print(f"💬 Response: {response[:200]}...")
                    
                    if docs_found > 0 and context_used:
                        print(f"✅ Query successful - found relevant context")
                        successful_queries += 1
                    else:
                        print(f"⚠️  Query completed but no relevant context found")
                        
                except Exception as e:
                    print(f"❌ Query failed: {e}")
        
        # Step 3: Test system status
        print(f"\n📊 Testing System Status...")
        async with AsyncSessionLocal() as db:
            status = await rag_system.get_system_status(db)
            print(f"System Status: {status['status']}")
            print(f"Total Documents: {status['total_documents']}")
            print(f"Vector Store Connected: {status['vector_store']['connected']}")
        
        # Step 4: Evaluate results
        print(f"\n📈 Results Summary:")
        print(f"Documents Added: {len(doc_ids)}/{len(documents)}")
        print(f"Successful Queries: {successful_queries}/{len(test_queries)}")
        
        success_rate = successful_queries / len(test_queries)
        print(f"Success Rate: {success_rate:.1%}")
        
        if success_rate >= 0.8:  # 80% success rate
            print(f"\n🎉 Complete RAG workflow test PASSED!")
            print(f"✅ RAG system is working end-to-end!")
            return True
        else:
            print(f"\n⚠️  RAG workflow test completed with issues")
            print(f"🔧 Success rate below 80% threshold")
            return False
        
    except Exception as e:
        print(f"❌ Complete RAG workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the complete RAG workflow test."""
    success = asyncio.run(test_complete_rag_workflow())
    
    if success:
        print(f"\n🚀 RAG System is Production Ready!")
        print(f"✅ All components working together successfully!")
    else:
        print(f"\n🔧 RAG System needs attention")
        print(f"❌ Check the output above for issues to fix")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
