"""
Dual-Write Service for SQLite to Weaviate Migration
Phase 2, Task 2.2: SQLite to Weaviate Migration Execution

This service provides dual-write functionality during the migration transition,
ensuring data consistency between SQLite and Weaviate with automatic fallback
and error handling.
"""

import logging
import json
import time
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Union
from contextlib import asynccontextmanager

import requests
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.models import Conversation, Message, Document, DocumentChunk
from app.core.logging_config import get_logger, log_performance, log_security_event

logger = get_logger(__name__)
settings = get_settings()


class DualWriteService:
    """
    Service for managing dual-write operations during migration.
    
    Provides consistent write operations to both SQLite and Weaviate
    with proper error handling, rollback capabilities, and performance monitoring.
    """
    
    def __init__(self):
        """Initialize dual-write service."""
        self.settings = get_settings()
        self.weaviate_headers = {}
        
        if self.settings.weaviate_api_key:
            self.weaviate_headers['Authorization'] = f'Bearer {self.settings.weaviate_api_key}'
        
        logger.info(f"Dual-write service initialized. Mode: {self.settings.migration_mode}")
    
    @property
    def is_dual_write_enabled(self) -> bool:
        """Check if dual-write is currently enabled."""
        return self.settings.dual_write_enabled and self.settings.migration_mode in ["dual_write", "weaviate_primary"]
    
    @property
    def is_weaviate_primary(self) -> bool:
        """Check if Weaviate is the primary read source."""
        return self.settings.weaviate_primary or self.settings.migration_mode == "weaviate_primary"
    
    async def write_conversation(
        self,
        db: AsyncSession,
        conversation_data: Dict[str, Any],
        conversation_id: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Write conversation to both SQLite and Weaviate if dual-write is enabled.
        
        Args:
            db: SQLite database session
            conversation_data: Conversation data to write
            conversation_id: Optional conversation ID
            
        Returns:
            Tuple of (success, conversation_id, error_info)
        """
        start_time = time.time()
        
        try:
            # Always write to SQLite first
            sqlite_success, conv_id, sqlite_error = await self._write_conversation_sqlite(
                db, conversation_data, conversation_id
            )
            
            if not sqlite_success:
                logger.error(f"SQLite conversation write failed: {sqlite_error}")
                return False, None, {"sqlite_error": sqlite_error}
            
            # Write to Weaviate if dual-write is enabled
            if self.is_dual_write_enabled:
                weaviate_success, weaviate_error = await self._write_conversation_weaviate(
                    conversation_data, conv_id
                )
                
                if not weaviate_success:
                    logger.error(f"Weaviate conversation write failed: {weaviate_error}")
                    
                    # Log dual-write failure but don't fail the operation
                    log_security_event(
                        event_type="dual_write_failure",
                        severity="medium",
                        conversation_id=conv_id,
                        error=str(weaviate_error),
                        operation="write_conversation"
                    )
                    
                    # Continue with SQLite success
                    return True, conv_id, {"weaviate_warning": weaviate_error}
            
            # Log performance
            duration_ms = (time.time() - start_time) * 1000
            log_performance(
                operation="write_conversation",
                duration_ms=duration_ms,
                success=True,
                dual_write=self.is_dual_write_enabled,
                conversation_id=conv_id
            )
            
            return True, conv_id, None
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Dual-write conversation failed: {e}")
            
            log_performance(
                operation="write_conversation",
                duration_ms=duration_ms,
                success=False,
                error=str(e)
            )
            
            return False, None, {"error": str(e)}
    
    async def write_message(
        self,
        db: AsyncSession,
        message_data: Dict[str, Any],
        message_id: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Write message to both SQLite and Weaviate if dual-write is enabled.
        
        Args:
            db: SQLite database session
            message_data: Message data to write
            message_id: Optional message ID
            
        Returns:
            Tuple of (success, message_id, error_info)
        """
        start_time = time.time()
        
        try:
            # Always write to SQLite first
            sqlite_success, msg_id, sqlite_error = await self._write_message_sqlite(
                db, message_data, message_id
            )
            
            if not sqlite_success:
                logger.error(f"SQLite message write failed: {sqlite_error}")
                return False, None, {"sqlite_error": sqlite_error}
            
            # Write to Weaviate if dual-write is enabled
            if self.is_dual_write_enabled:
                weaviate_success, weaviate_error = await self._write_message_weaviate(
                    message_data, msg_id
                )
                
                if not weaviate_success:
                    logger.error(f"Weaviate message write failed: {weaviate_error}")
                    
                    # Log dual-write failure but don't fail the operation
                    log_security_event(
                        event_type="dual_write_failure",
                        severity="medium",
                        message_id=msg_id,
                        error=str(weaviate_error),
                        operation="write_message"
                    )
                    
                    return True, msg_id, {"weaviate_warning": weaviate_error}
            
            # Log performance
            duration_ms = (time.time() - start_time) * 1000
            log_performance(
                operation="write_message",
                duration_ms=duration_ms,
                success=True,
                dual_write=self.is_dual_write_enabled,
                message_id=msg_id
            )
            
            return True, msg_id, None
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Dual-write message failed: {e}")
            
            log_performance(
                operation="write_message",
                duration_ms=duration_ms,
                success=False,
                error=str(e)
            )
            
            return False, None, {"error": str(e)}
    
    async def write_document(
        self,
        db: AsyncSession,
        document_data: Dict[str, Any],
        document_id: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Write document to both SQLite and Weaviate if dual-write is enabled.
        
        Args:
            db: SQLite database session
            document_data: Document data to write
            document_id: Optional document ID
            
        Returns:
            Tuple of (success, document_id, error_info)
        """
        start_time = time.time()
        
        try:
            # Always write to SQLite first
            sqlite_success, doc_id, sqlite_error = await self._write_document_sqlite(
                db, document_data, document_id
            )
            
            if not sqlite_success:
                logger.error(f"SQLite document write failed: {sqlite_error}")
                return False, None, {"sqlite_error": sqlite_error}
            
            # Write to Weaviate if dual-write is enabled
            if self.is_dual_write_enabled:
                weaviate_success, weaviate_error = await self._write_document_weaviate(
                    document_data, doc_id
                )
                
                if not weaviate_success:
                    logger.error(f"Weaviate document write failed: {weaviate_error}")
                    
                    # Log dual-write failure but don't fail the operation
                    log_security_event(
                        event_type="dual_write_failure",
                        severity="medium",
                        document_id=doc_id,
                        error=str(weaviate_error),
                        operation="write_document"
                    )
                    
                    return True, doc_id, {"weaviate_warning": weaviate_error}
            
            # Log performance
            duration_ms = (time.time() - start_time) * 1000
            log_performance(
                operation="write_document",
                duration_ms=duration_ms,
                success=True,
                dual_write=self.is_dual_write_enabled,
                document_id=doc_id
            )
            
            return True, doc_id, None
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Dual-write document failed: {e}")
            
            log_performance(
                operation="write_document",
                duration_ms=duration_ms,
                success=False,
                error=str(e)
            )
            
            return False, None, {"error": str(e)}
    
    async def _write_conversation_sqlite(
        self,
        db: AsyncSession,
        conversation_data: Dict[str, Any],
        conversation_id: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Write conversation to SQLite."""
        try:
            conv_id = conversation_id or str(uuid.uuid4())
            
            conversation = Conversation(
                id=conv_id,
                title=conversation_data.get("title", ""),
                summary=conversation_data.get("summary", ""),
                user_id=conversation_data.get("user_id"),
                metadata=conversation_data.get("metadata", {})
            )
            
            db.add(conversation)
            await db.commit()
            await db.refresh(conversation)
            
            return True, conv_id, None
            
        except Exception as e:
            await db.rollback()
            return False, None, str(e)
    
    async def _write_conversation_weaviate(
        self,
        conversation_data: Dict[str, Any],
        conversation_id: str
    ) -> Tuple[bool, Optional[str]]:
        """Write conversation to Weaviate."""
        try:
            weaviate_data = {
                "title": conversation_data.get("title", ""),
                "summary": conversation_data.get("summary", ""),
                "created_at": datetime.now().isoformat(),
                "user_id": conversation_data.get("user_id", ""),
                "metadata": conversation_data.get("metadata", {})
            }
            
            response = requests.post(
                f"{self.settings.weaviate_url}/v1/objects",
                headers={**self.weaviate_headers, 'Content-Type': 'application/json'},
                json={
                    "class": "Conversation",
                    "id": conversation_id,
                    "properties": weaviate_data
                },
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                return True, None
            else:
                return False, f"HTTP {response.status_code}: {response.text}"
                
        except Exception as e:
            return False, str(e)
    
    async def _write_message_sqlite(
        self,
        db: AsyncSession,
        message_data: Dict[str, Any],
        message_id: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Write message to SQLite."""
        try:
            msg_id = message_id or str(uuid.uuid4())
            
            message = Message(
                id=msg_id,
                conversation_id=message_data.get("conversation_id"),
                role=message_data.get("role", "user"),
                content=message_data.get("content", ""),
                tool_calls=json.dumps(message_data.get("tool_calls")) if message_data.get("tool_calls") else None,
                extra_data=json.dumps(message_data.get("extra_data")) if message_data.get("extra_data") else None
            )
            
            db.add(message)
            await db.commit()
            await db.refresh(message)
            
            return True, msg_id, None
            
        except Exception as e:
            await db.rollback()
            return False, None, str(e)
    
    async def _write_message_weaviate(
        self,
        message_data: Dict[str, Any],
        message_id: str
    ) -> Tuple[bool, Optional[str]]:
        """Write message to Weaviate."""
        try:
            weaviate_data = {
                "content": message_data.get("content", ""),
                "role": message_data.get("role", "user"),
                "timestamp": datetime.now().isoformat(),
                "embedding_model": "text2vec-transformers"
            }
            
            response = requests.post(
                f"{self.settings.weaviate_url}/v1/objects",
                headers={**self.weaviate_headers, 'Content-Type': 'application/json'},
                json={
                    "class": "Message",
                    "id": message_id,
                    "properties": weaviate_data
                },
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                return True, None
            else:
                return False, f"HTTP {response.status_code}: {response.text}"
                
        except Exception as e:
            return False, str(e)
    
    async def _write_document_sqlite(
        self,
        db: AsyncSession,
        document_data: Dict[str, Any],
        document_id: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Write document to SQLite."""
        try:
            doc_id = document_id or str(uuid.uuid4())
            
            document = Document(
                id=doc_id,
                title=document_data.get("title", ""),
                content=document_data.get("content", ""),
                content_type=document_data.get("content_type", "text/plain"),
                file_path=document_data.get("file_path"),
                file_size=document_data.get("file_size", 0),
                doc_metadata=document_data.get("metadata", {}),
                tags=document_data.get("tags", [])
            )
            
            db.add(document)
            await db.commit()
            await db.refresh(document)
            
            return True, doc_id, None
            
        except Exception as e:
            await db.rollback()
            return False, None, str(e)
    
    async def _write_document_weaviate(
        self,
        document_data: Dict[str, Any],
        document_id: str
    ) -> Tuple[bool, Optional[str]]:
        """Write document to Weaviate."""
        try:
            weaviate_data = {
                "content": document_data.get("content", ""),
                "document_title": document_data.get("title", ""),
                "chunk_index": 0,  # Full document
                "metadata": document_data.get("metadata", {})
            }
            
            response = requests.post(
                f"{self.settings.weaviate_url}/v1/objects",
                headers={**self.weaviate_headers, 'Content-Type': 'application/json'},
                json={
                    "class": "DocumentChunk",
                    "id": document_id,
                    "properties": weaviate_data
                },
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                return True, None
            else:
                return False, f"HTTP {response.status_code}: {response.text}"
                
        except Exception as e:
            return False, str(e)


# Global dual-write service instance
dual_write_service = DualWriteService()
