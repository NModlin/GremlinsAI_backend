# app/database/models.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON, LargeBinary, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.database import Base
import uuid


class Conversation(Base):
    """Model for chat conversations."""
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    
    # Relationships
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    multimodal_content = relationship("MultiModalContent", back_populates="conversation", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Conversation(id={self.id}, title={self.title})>"


class Message(Base):
    """Model for individual messages in conversations."""
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    role = Column(String(50), nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Additional metadata
    tool_calls = Column(Text, nullable=True)  # JSON string for tool calls
    extra_data = Column(Text, nullable=True)  # JSON string for additional metadata
    
    # Relationship to conversation
    conversation = relationship("Conversation", back_populates="messages")

    def __repr__(self):
        return f"<Message(id={self.id}, role={self.role}, conversation_id={self.conversation_id})>"


class Document(Base):
    """
    Model for storing documents and their metadata for vector search and RAG.
    """
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    content_type = Column(String(100), default="text/plain")  # MIME type
    file_path = Column(String(1000), nullable=True)  # Original file path if uploaded
    file_size = Column(Integer, nullable=True)  # File size in bytes

    # Vector store integration
    vector_id = Column(String, nullable=True)  # ID in vector store (Qdrant)
    embedding_model = Column(String(200), nullable=True)  # Model used for embeddings

    # Metadata
    doc_metadata = Column(JSON, nullable=True)  # Additional metadata as JSON
    tags = Column(JSON, nullable=True)  # Tags for categorization

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Soft delete
    is_active = Column(Boolean, default=True)

    # Relationships
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Document(id={self.id}, title={self.title[:50]})>"


class DocumentChunk(Base):
    """
    Model for storing document chunks for better vector search performance.
    """
    __tablename__ = "document_chunks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)

    # Chunk content
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)  # Order within document
    chunk_size = Column(Integer, nullable=False)  # Size in characters

    # Vector store integration
    vector_id = Column(String, nullable=True)  # ID in vector store
    embedding_model = Column(String(200), nullable=True)

    # Chunk metadata
    start_position = Column(Integer, nullable=True)  # Start position in original document
    end_position = Column(Integer, nullable=True)  # End position in original document
    chunk_metadata = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    document = relationship("Document", back_populates="chunks")

    def __repr__(self):
        return f"<DocumentChunk(id={self.id}, document_id={self.document_id}, index={self.chunk_index})>"


class SearchQuery(Base):
    """
    Model for tracking search queries and their results for analytics.
    """
    __tablename__ = "search_queries"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    query_text = Column(Text, nullable=False)
    query_type = Column(String(50), default="semantic")  # semantic, keyword, hybrid

    # Search parameters
    limit_requested = Column(Integer, default=5)
    score_threshold = Column(Float, nullable=True)
    filter_conditions = Column(JSON, nullable=True)

    # Results
    results_count = Column(Integer, default=0)
    results_metadata = Column(JSON, nullable=True)  # Summary of results

    # Performance metrics
    execution_time_ms = Column(Float, nullable=True)
    embedding_time_ms = Column(Float, nullable=True)
    search_time_ms = Column(Float, nullable=True)

    # Context
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=True)
    user_context = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    conversation = relationship("Conversation")

    def __repr__(self):
        return f"<SearchQuery(id={self.id}, query={self.query_text[:50]})>"


class AgentInteraction(Base):
    """
    Model for tracking agent interactions and multi-agent workflows.
    """
    __tablename__ = "agent_interactions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Agent information
    agent_name = Column(String(100), nullable=False)  # researcher, analyst, writer, coordinator
    agent_role = Column(String(200), nullable=True)

    # Interaction details
    interaction_type = Column(String(50), nullable=False)  # workflow, query, task
    input_data = Column(Text, nullable=True)
    output_data = Column(Text, nullable=True)

    # Workflow context
    workflow_id = Column(String, nullable=True)  # Links related agent interactions
    workflow_type = Column(String(100), nullable=True)  # simple_research, complex_analysis, etc.
    step_number = Column(Integer, nullable=True)  # Order in workflow

    # Performance metrics
    execution_time_ms = Column(Float, nullable=True)
    tokens_used = Column(Integer, nullable=True)

    # Context and metadata
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=True)
    task_metadata = Column(JSON, nullable=True)

    # Status tracking
    status = Column(String(50), default="completed")  # pending, running, completed, failed
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    conversation = relationship("Conversation")

    def __repr__(self):
        return f"<AgentInteraction(id={self.id}, agent={self.agent_name}, type={self.interaction_type})>"


class MultiModalContent(Base):
    """
    Model for storing multi-modal content and processing results.
    Supports audio, video, and image content with processing metadata.
    """
    __tablename__ = "multimodal_content"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Content information
    media_type = Column(String(50), nullable=False)  # audio, video, image
    filename = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    content_hash = Column(String(64), nullable=True)  # SHA-256 hash for deduplication
    storage_path = Column(String(1000), nullable=True)  # Path to stored file

    # Processing information
    processing_status = Column(String(50), default="pending")  # pending, processing, completed, failed
    processing_result = Column(JSON, nullable=True)  # Processing results and metadata
    error_message = Column(Text, nullable=True)

    # Context
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    conversation = relationship("Conversation")

    def __repr__(self):
        return f"<MultiModalContent(id={self.id}, type={self.media_type}, filename={self.filename})>"
