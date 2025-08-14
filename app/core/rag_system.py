# app/core/rag_system.py
import logging
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.services.document_service import DocumentService
from app.core.vector_store import vector_store
from app.core.multi_agent import multi_agent_orchestrator

logger = logging.getLogger(__name__)

class RAGSystem:
    """
    Retrieval-Augmented Generation system that combines semantic search
    with agent responses for enhanced, context-aware answers.
    """
    
    def __init__(
        self,
        default_search_limit: int = 5,
        default_score_threshold: float = 0.7,
        max_context_length: int = 4000
    ):
        """Initialize the RAG system."""
        self.default_search_limit = default_search_limit
        self.default_score_threshold = default_score_threshold
        self.max_context_length = max_context_length
    
    async def retrieve_and_generate(
        self,
        db: AsyncSession,
        query: str,
        conversation_id: Optional[str] = None,
        search_limit: Optional[int] = None,
        score_threshold: Optional[float] = None,
        filter_conditions: Optional[Dict[str, Any]] = None,
        use_multi_agent: bool = False,
        search_type: str = "chunks"
    ) -> Dict[str, Any]:
        """
        Perform retrieval-augmented generation.
        
        Args:
            db: Database session
            query: User query
            conversation_id: Optional conversation ID for context
            search_limit: Number of documents to retrieve
            score_threshold: Minimum similarity score
            filter_conditions: Additional filters for search
            use_multi_agent: Whether to use multi-agent system
            search_type: Type of search ("chunks", "documents", "both")
        
        Returns:
            Dict containing the generated response and metadata
        """
        try:
            # Use defaults if not specified
            search_limit = search_limit or self.default_search_limit
            score_threshold = score_threshold or self.default_score_threshold
            
            # Step 1: Retrieve relevant documents
            retrieved_docs, search_query_id = await DocumentService.semantic_search(
                db=db,
                query=query,
                limit=search_limit,
                score_threshold=score_threshold,
                filter_conditions=filter_conditions,
                search_type=search_type,
                conversation_id=conversation_id
            )
            
            # Step 2: Prepare context from retrieved documents
            context = self._prepare_context(retrieved_docs, query)
            
            # Step 3: Generate enhanced prompt with context
            enhanced_prompt = self._create_rag_prompt(query, context)
            
            # Step 4: Generate response using agent system
            if use_multi_agent and multi_agent_orchestrator.llm is not None:
                # Use multi-agent system for complex reasoning
                agent_response = multi_agent_orchestrator.execute_simple_query(
                    query=enhanced_prompt,
                    context=""
                )
            else:
                # Use fallback search or simple agent
                from app.core.tools import duckduckgo_search
                
                # Combine retrieved context with web search if needed
                if not retrieved_docs:
                    web_search_result = duckduckgo_search(query)
                    agent_response = {
                        "query": query,
                        "result": web_search_result,
                        "agents_used": ["web_search"],
                        "task_type": "web_search_fallback"
                    }
                else:
                    # Generate response based on retrieved context
                    response_text = self._generate_context_based_response(query, context)
                    agent_response = {
                        "query": query,
                        "result": response_text,
                        "agents_used": ["rag_system"],
                        "task_type": "rag_response"
                    }
            
            # Step 5: Prepare final response
            rag_response = {
                "query": query,
                "response": agent_response.get("result", ""),
                "retrieved_documents": retrieved_docs,
                "context_used": len(retrieved_docs) > 0,
                "search_metadata": {
                    "search_query_id": search_query_id,
                    "documents_found": len(retrieved_docs),
                    "search_type": search_type,
                    "score_threshold": score_threshold
                },
                "agent_metadata": {
                    "agents_used": agent_response.get("agents_used", []),
                    "task_type": agent_response.get("task_type", "unknown"),
                    "use_multi_agent": use_multi_agent
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"RAG response generated for query with {len(retrieved_docs)} retrieved documents")
            return rag_response
            
        except Exception as e:
            logger.error(f"Error in RAG system: {e}")
            return {
                "query": query,
                "response": f"I apologize, but I encountered an error while processing your request: {str(e)}",
                "retrieved_documents": [],
                "context_used": False,
                "error": str(e)
            }
    
    def _prepare_context(self, retrieved_docs: List[Dict[str, Any]], query: str) -> str:
        """Prepare context string from retrieved documents."""
        if not retrieved_docs:
            return ""
        
        context_parts = []
        current_length = 0
        
        # Sort by relevance score
        sorted_docs = sorted(retrieved_docs, key=lambda x: x["score"], reverse=True)
        
        for i, doc in enumerate(sorted_docs):
            # Create context entry
            doc_context = f"Document {i+1} (Score: {doc['score']:.3f}):\n"
            doc_context += f"Title: {doc['document_title']}\n"
            doc_context += f"Content: {doc['content']}\n"
            
            # Check if adding this document would exceed max length
            if current_length + len(doc_context) > self.max_context_length:
                break
            
            context_parts.append(doc_context)
            current_length += len(doc_context)
        
        return "\n---\n".join(context_parts)
    
    def _create_rag_prompt(self, query: str, context: str) -> str:
        """Create an enhanced prompt that includes retrieved context."""
        if not context:
            return query
        
        prompt = f"""Based on the following relevant documents, please answer the user's question. Use the information from the documents to provide a comprehensive and accurate response. If the documents don't contain enough information to fully answer the question, please indicate what additional information might be needed.

RELEVANT DOCUMENTS:
{context}

USER QUESTION: {query}

Please provide a detailed response based on the above documents:"""
        
        return prompt
    
    def _generate_context_based_response(self, query: str, context: str) -> str:
        """Generate a simple response based on context when no LLM is available."""
        if not context:
            return "I couldn't find any relevant documents to answer your question. You might want to try rephrasing your query or adding more documents to the knowledge base."
        
        # Simple template-based response
        response = f"Based on the available documents, here's what I found regarding your question about '{query}':\n\n"
        
        # Extract key information from context
        lines = context.split('\n')
        content_lines = [line for line in lines if line.startswith('Content:')]
        
        if content_lines:
            response += "Key information from the documents:\n"
            for i, line in enumerate(content_lines[:3]):  # Limit to top 3 results
                content = line.replace('Content:', '').strip()
                if content:
                    response += f"• {content[:200]}{'...' if len(content) > 200 else ''}\n"
        
        response += "\nThis information is based on the documents in the knowledge base. For more detailed information, you may want to review the full documents or ask more specific questions."
        
        return response
    
    async def add_document_from_text(
        self,
        db: AsyncSession,
        title: str,
        content: str,
        content_type: str = "text/plain",
        doc_metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> Optional[str]:
        """Add a document to the RAG system from text content."""
        try:
            document = await DocumentService.create_document(
                db=db,
                title=title,
                content=content,
                content_type=content_type,
                doc_metadata=doc_metadata,
                tags=tags
            )
            
            if document:
                logger.info(f"Added document to RAG system: {document.id}")
                return document.id
            else:
                logger.error("Failed to add document to RAG system")
                return None
                
        except Exception as e:
            logger.error(f"Error adding document to RAG system: {e}")
            return None
    
    async def get_system_status(self, db: AsyncSession) -> Dict[str, Any]:
        """Get the status of the RAG system."""
        try:
            # Get document statistics
            documents, total_docs = await DocumentService.list_documents(db, limit=1)
            
            # Get vector store info
            vector_info = vector_store.get_collection_info()
            
            # Get search analytics
            analytics = await DocumentService.get_search_analytics(db)
            
            return {
                "status": "operational" if vector_store.is_connected else "limited",
                "total_documents": total_docs,
                "vector_store": vector_info,
                "search_analytics": analytics,
                "configuration": {
                    "default_search_limit": self.default_search_limit,
                    "default_score_threshold": self.default_score_threshold,
                    "max_context_length": self.max_context_length
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting RAG system status: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def suggest_related_queries(
        self,
        db: AsyncSession,
        query: str,
        limit: int = 5
    ) -> List[str]:
        """Suggest related queries based on document content."""
        try:
            # Get similar documents
            retrieved_docs, _ = await DocumentService.semantic_search(
                db=db,
                query=query,
                limit=limit * 2,
                score_threshold=0.5,
                search_type="chunks"
            )
            
            # Extract potential related queries from document titles and content
            suggestions = set()
            
            for doc in retrieved_docs:
                title = doc.get("document_title", "")
                content = doc.get("content", "")
                
                # Simple heuristic: extract questions from content
                sentences = content.split('.')
                for sentence in sentences:
                    sentence = sentence.strip()
                    if any(word in sentence.lower() for word in ['what', 'how', 'why', 'when', 'where']):
                        if len(sentence) < 100:  # Keep suggestions concise
                            suggestions.add(sentence)
                
                # Add variations based on title
                if title and len(title) < 100:
                    suggestions.add(f"Tell me more about {title}")
                    suggestions.add(f"How does {title} work?")
            
            # Return top suggestions
            return list(suggestions)[:limit]
            
        except Exception as e:
            logger.error(f"Error generating query suggestions: {e}")
            return []


# Global RAG system instance
rag_system = RAGSystem()
