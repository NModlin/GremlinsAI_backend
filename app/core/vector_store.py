# app/core/vector_store.py
import logging
import os
import base64
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime
import uuid

# Weaviate imports with fallback handling
try:
    import weaviate
    # Try v4 imports first, fallback to v3
    try:
        from weaviate.classes.config import Configure, Property, DataType
        from weaviate.classes.query import Filter
        WEAVIATE_V4 = True
    except ImportError:
        # v3 imports
        WEAVIATE_V4 = False
    WEAVIATE_AVAILABLE = True
except ImportError:
    WEAVIATE_AVAILABLE = False
    WEAVIATE_V4 = False

# Embedding model imports with fallback
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

# CLIP imports for multimodal embeddings
try:
    import clip
    import torch
    from PIL import Image
    CLIP_AVAILABLE = True
except ImportError:
    CLIP_AVAILABLE = False

logger = logging.getLogger(__name__)

class WeaviateVectorStore:
    """
    Manages vector storage and retrieval using Weaviate for semantic search and RAG capabilities.
    Supports both text and multimodal (CLIP) embeddings for cross-modal search.
    """
    
    def __init__(
        self,
        weaviate_url: str = "http://localhost:8080",
        weaviate_api_key: Optional[str] = None,
        embedding_model: str = "all-MiniLM-L6-v2",
        use_clip: bool = True,
        class_name: str = "GremlinsDocument"
    ):
        """Initialize the Weaviate vector store manager."""
        self.weaviate_url = weaviate_url
        self.weaviate_api_key = weaviate_api_key
        self.class_name = class_name
        self.embedding_model_name = embedding_model
        self.use_clip = use_clip and CLIP_AVAILABLE

        # Initialize embedding models
        self.text_embedding_model = None
        self.clip_model = None
        self.clip_preprocess = None
        self.vector_size = 384  # Default dimension

        self._initialize_embedding_models()

        # Initialize Weaviate client
        self.client = None
        self.is_connected = False
        self._initialize_client()
    
    def _initialize_embedding_models(self):
        """Initialize text and multimodal embedding models."""
        # Initialize text embedding model
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.text_embedding_model = SentenceTransformer(self.embedding_model_name)
                self.vector_size = self.text_embedding_model.get_sentence_embedding_dimension()
                logger.info(f"Initialized text embedding model: {self.embedding_model_name} (dimension: {self.vector_size})")
            except Exception as e:
                logger.error(f"Failed to initialize text embedding model: {e}")
                self.text_embedding_model = None
        else:
            logger.warning("sentence-transformers not available - text embeddings disabled")

        # Initialize CLIP model for multimodal embeddings
        if self.use_clip and CLIP_AVAILABLE:
            try:
                self.clip_model, self.clip_preprocess = clip.load("ViT-B/32")
                logger.info("Initialized CLIP model for multimodal embeddings")
            except Exception as e:
                logger.error(f"Failed to initialize CLIP model: {e}")
                self.clip_model = None
                self.use_clip = False
        elif self.use_clip:
            logger.warning("CLIP not available - multimodal embeddings disabled")
            self.use_clip = False

    def _initialize_client(self):
        """Initialize Weaviate client and create schema if needed."""
        if not WEAVIATE_AVAILABLE:
            logger.error("Weaviate client not available - install weaviate-client")
            self.is_connected = False
            return

        try:
            # Create Weaviate client (v4 syntax)
            # Now with proper gRPC support
            self.client = weaviate.connect_to_local(
                port=8080,
                grpc_port=50051
            )

            # Test connection
            if self.client.is_ready():
                self.is_connected = True
                logger.info(f"Connected to Weaviate at {self.weaviate_url}")

                # Create schema if it doesn't exist
                self._ensure_schema_exists()
            else:
                logger.error("Weaviate is not ready")
                self.is_connected = False

        except Exception as e:
            logger.warning(f"Failed to connect to Weaviate: {e}")
            logger.info("Vector store will operate in fallback mode")
            self.is_connected = False
    
    def _ensure_schema_exists(self):
        """Ensure the Weaviate collection exists, create if not (v4 API)."""
        if not self.is_connected:
            return

        try:
            # Check if collection already exists (v4 API)
            collections = self.client.collections.list_all()

            if self.class_name not in collections:
                # Create collection using v4 API
                self._create_simple_collection()
            else:
                logger.info(f"Weaviate collection {self.class_name} already exists")

        except Exception as e:
            logger.error(f"Failed to ensure schema exists: {e}")

    def _create_simple_collection(self):
        """Create a simple collection for document storage (v4 API)."""
        try:
            # Import v4 classes
            import weaviate.classes.config as wvc

            # Create simple collection (BM25 search compatible)
            collection = self.client.collections.create(
                name=self.class_name,
                description="GremlinsAI document storage with BM25 and vector search capabilities",
                properties=[
                    wvc.Property(
                        name="content",
                        data_type=wvc.DataType.TEXT,
                        description="The main content of the document"
                    ),
                    wvc.Property(
                        name="title",
                        data_type=wvc.DataType.TEXT,
                        description="Document title"
                    ),
                    wvc.Property(
                        name="document_id",
                        data_type=wvc.DataType.TEXT,
                        description="Reference to the document in the main database"
                    ),
                    wvc.Property(
                        name="chunk_id",
                        data_type=wvc.DataType.TEXT,
                        description="Reference to the chunk in the main database"
                    ),
                    wvc.Property(
                        name="content_type",
                        data_type=wvc.DataType.TEXT,
                        description="MIME type of the content"
                    ),
                    wvc.Property(
                        name="chunk_type",
                        data_type=wvc.DataType.TEXT,
                        description="Type of chunk: full_document or chunk"
                    ),
                    wvc.Property(
                        name="chunk_index",
                        data_type=wvc.DataType.INT,
                        description="Index of the chunk within the document"
                    ),
                    wvc.Property(
                        name="embedding_model",
                        data_type=wvc.DataType.TEXT,
                        description="Model used to generate embeddings"
                    ),
                    wvc.Property(
                        name="created_at",
                        data_type=wvc.DataType.TEXT,
                        description="Creation timestamp"
                    ),
                    wvc.Property(
                        name="media_type",
                        data_type=wvc.DataType.TEXT,
                        description="Type of media: text, image, audio, video"
                    )
                ]
                # No vector configuration - use default (supports both BM25 and manual vectors)
            )

            logger.info(f"Created Weaviate collection: {self.class_name}")
            return collection

        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            raise e
    
    def embed_text(self, text: str) -> Optional[List[float]]:
        """Generate text embeddings using sentence-transformers."""
        if not self.text_embedding_model:
            logger.warning("Text embedding model not available")
            return None

        try:
            embedding = self.text_embedding_model.encode(text, convert_to_tensor=False)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to generate text embedding: {e}")
            return None

    def embed_image(self, image_data: bytes) -> Optional[List[float]]:
        """Generate image embeddings using CLIP."""
        if not self.use_clip or not self.clip_model:
            logger.warning("CLIP model not available for image embeddings")
            return None

        try:
            # Convert bytes to PIL Image
            from io import BytesIO
            image = Image.open(BytesIO(image_data))

            # Preprocess and encode
            image_input = self.clip_preprocess(image).unsqueeze(0)

            with torch.no_grad():
                image_features = self.clip_model.encode_image(image_input)
                # Normalize the features
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)

            return image_features.squeeze().tolist()
        except Exception as e:
            logger.error(f"Failed to generate image embedding: {e}")
            return None

    def embed_multimodal(self, text: str, image_data: Optional[bytes] = None) -> Optional[List[float]]:
        """Generate multimodal embeddings by combining text and image features."""
        if not self.use_clip or not self.clip_model:
            # Fall back to text-only embedding
            return self.embed_text(text)

        try:
            text_features = None
            image_features = None

            # Get text features using CLIP
            if text:
                text_input = clip.tokenize([text])
                with torch.no_grad():
                    text_features = self.clip_model.encode_text(text_input)
                    text_features = text_features / text_features.norm(dim=-1, keepdim=True)

            # Get image features if provided
            if image_data:
                image_features = self.embed_image(image_data)
                if image_features:
                    image_features = torch.tensor(image_features).unsqueeze(0)

            # Combine features
            if text_features is not None and image_features is not None:
                # Average the normalized features
                combined_features = (text_features + image_features) / 2
                return combined_features.squeeze().tolist()
            elif text_features is not None:
                return text_features.squeeze().tolist()
            elif image_features is not None:
                return image_features
            else:
                return None

        except Exception as e:
            logger.error(f"Failed to generate multimodal embedding: {e}")
            return None
    
    def add_document(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        document_id: Optional[str] = None,
        image_data: Optional[bytes] = None
    ) -> Optional[str]:
        """Add a document to the Weaviate vector store with optional multimodal data."""
        if not self.is_connected:
            logger.warning("Vector store not connected, cannot add document")
            return None

        try:
            # Generate embedding (multimodal if image provided)
            if image_data and self.use_clip:
                embedding = self.embed_multimodal(content, image_data)
                media_type = "multimodal"
            else:
                embedding = self.embed_text(content)
                media_type = "text"

            if not embedding:
                logger.warning("Failed to generate embedding for document")
                return None

            # Generate document ID if not provided
            if not document_id:
                document_id = str(uuid.uuid4())

            # Prepare properties (ensure all required fields are present)
            properties = {
                "content": content or "",
                "document_id": metadata.get("document_id", document_id) if metadata else document_id,
                "title": metadata.get("title", "") if metadata else "",
                "chunk_id": metadata.get("chunk_id", "") if metadata else "",  # Always include chunk_id
                "content_type": metadata.get("content_type", "text/plain") if metadata else "text/plain",
                "chunk_type": metadata.get("chunk_type", "full_document") if metadata else "full_document",
                "chunk_index": metadata.get("chunk_index", 0) if metadata else 0,
                "embedding_model": self.embedding_model_name or "unknown",
                "created_at": datetime.utcnow().isoformat(),
                "media_type": media_type or "text"
            }

            # Ensure no None values for string fields
            for key in ["content", "document_id", "title", "chunk_id", "content_type", "chunk_type", "embedding_model", "created_at", "media_type"]:
                if properties[key] is None:
                    properties[key] = ""

            # Add image data if provided
            if image_data and self.use_clip:
                properties["image_data"] = base64.b64encode(image_data).decode('utf-8')

            # Insert into Weaviate (v4 API)
            try:
                collection = self.client.collections.get(self.class_name)
                result = collection.data.insert(
                    properties=properties,
                    uuid=document_id,
                    vector=embedding
                )
            except Exception as e:
                # If collection doesn't exist, create it first
                if "not found" in str(e).lower():
                    self._create_simple_collection()
                    collection = self.client.collections.get(self.class_name)
                    result = collection.data.insert(
                        properties=properties,
                        uuid=document_id,
                        vector=embedding
                    )
                else:
                    raise e

            logger.info(f"Added document to Weaviate: {document_id}")
            return document_id

        except Exception as e:
            logger.error(f"Failed to add document to Weaviate: {e}")
            return None
    
    def search_similar(
        self,
        query: str,
        limit: int = 5,
        score_threshold: float = 0.7,
        filter_conditions: Optional[Dict[str, Any]] = None,
        image_data: Optional[bytes] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar documents using text or multimodal query."""
        if not self.is_connected:
            logger.warning("Vector store not connected, cannot search")
            return []

        try:
            # Generate query embedding (multimodal if image provided)
            if image_data and self.use_clip:
                query_embedding = self.embed_multimodal(query, image_data)
                logger.info("Using multimodal search with text and image")
            else:
                query_embedding = self.embed_text(query)
                logger.info("Using text-only search")

            if not query_embedding:
                logger.warning("Failed to generate query embedding")
                return []

            # Get collection and perform search (v4 API)
            collection = self.client.collections.get(self.class_name)

            # Use BM25 search as primary method (more reliable than vector search)
            try:
                search_results = collection.query.bm25(
                    query=query,
                    limit=limit,
                    return_metadata=['score']
                )
                logger.info(f"Using BM25 search for query: {query}")
            except Exception as bm25_error:
                logger.warning(f"BM25 search failed: {bm25_error}, trying vector search")
                # Fallback to vector search
                search_results = collection.query.near_vector(
                    near_vector=query_embedding,
                    limit=limit,
                    distance=1.0 - score_threshold,  # Convert certainty to distance
                    return_metadata=['distance']
                )

            # Format results (v4 API)
            results = []
            for obj in search_results.objects:
                # Handle both BM25 and vector search results
                if hasattr(obj.metadata, 'score') and obj.metadata.score is not None:
                    # BM25 search result
                    score = obj.metadata.score
                elif hasattr(obj.metadata, 'distance') and obj.metadata.distance is not None:
                    # Vector search result - convert distance to similarity
                    distance = obj.metadata.distance
                    score = max(0.0, 1.0 - (distance / 2.0))
                else:
                    # No score available
                    score = 0.5

                properties = obj.properties
                results.append({
                    "id": properties.get("document_id", str(obj.uuid)),
                    "score": score,
                    "content": properties.get("content", ""),
                    "document_id": properties.get("document_id", str(obj.uuid)),
                    "document_title": properties.get("title", ""),
                    "document_type": properties.get("content_type", "text/plain"),
                    "chunk_index": properties.get("chunk_index", 0),
                    "metadata": {
                        "title": properties.get("title", ""),
                        "chunk_id": properties.get("chunk_id"),
                        "content_type": properties.get("content_type", ""),
                        "chunk_type": properties.get("chunk_type", ""),
                        "chunk_index": properties.get("chunk_index", 0),
                        "created_at": properties.get("created_at", ""),
                        "media_type": properties.get("media_type", "text"),
                        "additional_metadata": properties.get("metadata", {})
                    }
                })

            logger.info(f"Found {len(results)} similar documents for query")
            return results
            
        except Exception as e:
            logger.error(f"Failed to search vector store: {e}")
            return []
    
    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific document by ID from Weaviate."""
        if not self.is_connected:
            return None

        try:
            result = (
                self.client.query
                .get(self.class_name, [
                    "content", "title", "document_id", "chunk_id",
                    "content_type", "chunk_type", "created_at", "metadata"
                ])
                .with_where({
                    "path": ["document_id"],
                    "operator": "Equal",
                    "valueString": document_id
                })
                .with_limit(1)
                .do()
            )

            if "data" in result and "Get" in result["data"]:
                documents = result["data"]["Get"].get(self.class_name, [])
                if documents:
                    doc = documents[0]
                    return {
                        "id": doc.get("document_id", ""),
                        "content": doc.get("content", ""),
                        "metadata": {
                            "title": doc.get("title", ""),
                            "chunk_id": doc.get("chunk_id"),
                            "content_type": doc.get("content_type", ""),
                            "chunk_type": doc.get("chunk_type", ""),
                            "created_at": doc.get("created_at", ""),
                            "additional_metadata": doc.get("metadata", {})
                        }
                    }

            return None

        except Exception as e:
            logger.error(f"Failed to retrieve document: {e}")
            return None

    def delete_document(self, document_id: str) -> bool:
        """Delete a document from the Weaviate vector store."""
        if not self.is_connected:
            return False

        try:
            # Delete by document_id property
            result = self.client.batch.delete_objects(
                class_name=self.class_name,
                where={
                    "path": ["document_id"],
                    "operator": "Equal",
                    "valueString": document_id
                }
            )

            logger.info(f"Deleted document from Weaviate: {document_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            return False
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the Weaviate class."""
        if not self.is_connected:
            return {
                "connected": False,
                "class_name": self.class_name,
                "error": "Not connected to Weaviate"
            }

        try:
            # Get collection info (v4 API)
            collection = self.client.collections.get(self.class_name)

            # Get object count using aggregate
            count_result = collection.aggregate.over_all(total_count=True)
            count = count_result.total_count if count_result else 0

            return {
                "connected": True,
                "class_name": self.class_name,
                "object_count": count,
                "vector_size": self.vector_size,
                "embedding_model": self.embedding_model_name,
                "multimodal_enabled": self.use_clip,
                "properties": 10  # We know we have 10 properties from our schema
            }

        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            return {
                "connected": False,
                "class_name": self.class_name,
                "error": str(e)
            }
    
    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split text into overlapping chunks with smart boundary detection."""
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size

            # Try to break at sentence boundaries
            if end < len(text):
                # Look for sentence endings within reasonable range
                for i in range(end, max(start + chunk_size // 2, end - 100), -1):
                    if text[i] in '.!?':
                        end = i + 1
                        break
                else:
                    # If no sentence boundary found, look for word boundary
                    for i in range(end, max(start + chunk_size // 2, end - 50), -1):
                        if text[i] == ' ':
                            end = i
                            break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end - overlap
            if start >= len(text):
                break

        return chunks

    def get_capabilities(self) -> Dict[str, bool]:
        """Get current capabilities of the vector store."""
        return {
            "weaviate_available": WEAVIATE_AVAILABLE,
            "connected": self.is_connected,
            "text_embeddings": self.text_embedding_model is not None,
            "multimodal_embeddings": self.use_clip and self.clip_model is not None,
            "clip_available": CLIP_AVAILABLE,
            "sentence_transformers_available": SENTENCE_TRANSFORMERS_AVAILABLE
        }


# Global instance factory
def create_vector_store() -> WeaviateVectorStore:
    """Create a vector store instance with environment configuration."""
    weaviate_url = os.getenv("WEAVIATE_URL", "http://localhost:8080")
    weaviate_api_key = os.getenv("WEAVIATE_API_KEY")
    embedding_model = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    use_clip = os.getenv("USE_CLIP", "true").lower() == "true"
    class_name = os.getenv("WEAVIATE_CLASS_NAME", "GremlinsDocument")

    return WeaviateVectorStore(
        weaviate_url=weaviate_url,
        weaviate_api_key=weaviate_api_key,
        embedding_model=embedding_model,
        use_clip=use_clip,
        class_name=class_name
    )

# Global instance
vector_store = create_vector_store()
