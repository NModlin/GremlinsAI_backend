# app/core/vector_store.py
import logging
import os
from typing import List, Dict, Any, Optional, Tuple
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

class VectorStoreManager:
    """
    Manages vector storage and retrieval using Qdrant for semantic search and RAG capabilities.
    """
    
    def __init__(
        self, 
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        embedding_model: str = "all-MiniLM-L6-v2",
        collection_name: str = "gremlins_documents"
    ):
        """Initialize the vector store manager."""
        self.qdrant_host = qdrant_host
        self.qdrant_port = qdrant_port
        self.collection_name = collection_name
        self.embedding_model_name = embedding_model
        
        # Initialize embedding model
        try:
            self.embedding_model = SentenceTransformer(embedding_model)
            self.vector_size = self.embedding_model.get_sentence_embedding_dimension()
            logger.info(f"Initialized embedding model: {embedding_model} (dimension: {self.vector_size})")
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            self.embedding_model = None
            self.vector_size = 384  # Default for all-MiniLM-L6-v2
        
        # Initialize Qdrant client
        self.client = None
        self.is_connected = False
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Qdrant client and create collection if needed."""
        try:
            # Try to connect to Qdrant
            self.client = QdrantClient(host=self.qdrant_host, port=self.qdrant_port)
            
            # Test connection
            collections = self.client.get_collections()
            self.is_connected = True
            logger.info(f"Connected to Qdrant at {self.qdrant_host}:{self.qdrant_port}")
            
            # Create collection if it doesn't exist
            self._ensure_collection_exists()
            
        except Exception as e:
            logger.warning(f"Failed to connect to Qdrant: {e}")
            logger.info("Vector store will operate in fallback mode")
            self.is_connected = False
    
    def _ensure_collection_exists(self):
        """Ensure the collection exists, create if not."""
        if not self.is_connected:
            return
        
        try:
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created collection: {self.collection_name}")
            else:
                logger.info(f"Collection {self.collection_name} already exists")
                
        except Exception as e:
            logger.error(f"Failed to ensure collection exists: {e}")
    
    def embed_text(self, text: str) -> Optional[List[float]]:
        """Generate embeddings for text."""
        if not self.embedding_model:
            logger.warning("Embedding model not available")
            return None
        
        try:
            embedding = self.embedding_model.encode(text, convert_to_tensor=False)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None
    
    def add_document(
        self, 
        content: str, 
        metadata: Optional[Dict[str, Any]] = None,
        document_id: Optional[str] = None
    ) -> Optional[str]:
        """Add a document to the vector store."""
        if not self.is_connected:
            logger.warning("Vector store not connected, cannot add document")
            return None
        
        try:
            # Generate embedding
            embedding = self.embed_text(content)
            if not embedding:
                return None
            
            # Generate document ID if not provided
            if not document_id:
                document_id = str(uuid.uuid4())
            
            # Prepare metadata
            payload = {
                "content": content,
                "document_id": document_id,
                "created_at": datetime.utcnow().isoformat(),
                **(metadata or {})
            }
            
            # Create point
            point = PointStruct(
                id=document_id,
                vector=embedding,
                payload=payload
            )
            
            # Insert into Qdrant
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            logger.info(f"Added document to vector store: {document_id}")
            return document_id
            
        except Exception as e:
            logger.error(f"Failed to add document to vector store: {e}")
            return None
    
    def search_similar(
        self, 
        query: str, 
        limit: int = 5,
        score_threshold: float = 0.7,
        filter_conditions: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar documents."""
        if not self.is_connected:
            logger.warning("Vector store not connected, cannot search")
            return []
        
        try:
            # Generate query embedding
            query_embedding = self.embed_text(query)
            if not query_embedding:
                return []
            
            # Prepare filter
            query_filter = None
            if filter_conditions:
                conditions = []
                for key, value in filter_conditions.items():
                    conditions.append(
                        FieldCondition(key=key, match=MatchValue(value=value))
                    )
                if conditions:
                    query_filter = Filter(must=conditions)
            
            # Search
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=query_filter
            )
            
            # Format results
            results = []
            for result in search_results:
                results.append({
                    "id": result.id,
                    "score": result.score,
                    "content": result.payload.get("content", ""),
                    "metadata": {k: v for k, v in result.payload.items() if k != "content"}
                })
            
            logger.info(f"Found {len(results)} similar documents for query")
            return results
            
        except Exception as e:
            logger.error(f"Failed to search vector store: {e}")
            return []
    
    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific document by ID."""
        if not self.is_connected:
            return None
        
        try:
            result = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[document_id]
            )
            
            if result:
                point = result[0]
                return {
                    "id": point.id,
                    "content": point.payload.get("content", ""),
                    "metadata": {k: v for k, v in point.payload.items() if k != "content"}
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve document: {e}")
            return None
    
    def delete_document(self, document_id: str) -> bool:
        """Delete a document from the vector store."""
        if not self.is_connected:
            return False
        
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=[document_id]
            )
            logger.info(f"Deleted document: {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            return False
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the collection."""
        if not self.is_connected:
            return {
                "connected": False,
                "collection_name": self.collection_name,
                "error": "Not connected to Qdrant"
            }
        
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "connected": True,
                "collection_name": self.collection_name,
                "points_count": info.points_count,
                "vector_size": info.config.params.vectors.size,
                "distance": info.config.params.vectors.distance.value,
                "embedding_model": self.embedding_model_name
            }
            
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            return {
                "connected": False,
                "collection_name": self.collection_name,
                "error": str(e)
            }
    
    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split text into overlapping chunks for better vector storage."""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to break at sentence boundaries
            if end < len(text):
                # Look for sentence endings
                for i in range(end, max(start + chunk_size // 2, end - 100), -1):
                    if text[i] in '.!?':
                        end = i + 1
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap
            if start >= len(text):
                break
        
        return chunks


# Global instance
vector_store = VectorStoreManager(
    qdrant_host=os.getenv("QDRANT_HOST", "localhost"),
    qdrant_port=int(os.getenv("QDRANT_PORT", "6333")),
    embedding_model=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
    collection_name=os.getenv("QDRANT_COLLECTION", "gremlins_documents")
)
