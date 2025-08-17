"""
Migration utilities for transitioning from SQLite to Weaviate.

This module provides utilities to migrate existing SQLite data to the new
Weaviate schema without data loss, ensuring backward compatibility and
seamless transition.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import json

from sqlalchemy.orm import Session
from weaviate import WeaviateClient

from app.database.models import Conversation as SQLiteConversation, Message as SQLiteMessage
from app.database.weaviate_schema import WeaviateSchemaManager

logger = logging.getLogger(__name__)


class WeaviateMigrationManager:
    """Manages migration from SQLite to Weaviate."""
    
    def __init__(self, sqlite_session: Session, weaviate_client: WeaviateClient):
        """
        Initialize migration manager.
        
        Args:
            sqlite_session: SQLAlchemy session for SQLite database
            weaviate_client: Weaviate client instance
        """
        self.sqlite_session = sqlite_session
        self.weaviate_client = weaviate_client
        self.schema_manager = WeaviateSchemaManager(weaviate_client)
        
    def migrate_all_data(self) -> Dict[str, Any]:
        """
        Migrate all data from SQLite to Weaviate.
        
        Returns:
            Dict containing migration results and statistics
        """
        logger.info("Starting complete data migration from SQLite to Weaviate...")
        
        migration_results = {
            "started_at": datetime.utcnow().isoformat(),
            "conversations": {"migrated": 0, "errors": 0},
            "messages": {"migrated": 0, "errors": 0},
            "total_errors": [],
            "success": False
        }
        
        try:
            # Ensure schema exists
            if not self.schema_manager.create_weaviate_schema():
                raise Exception("Failed to create Weaviate schema")
            
            # Migrate conversations first
            conv_results = self.migrate_conversations()
            migration_results["conversations"] = conv_results
            
            # Migrate messages
            msg_results = self.migrate_messages()
            migration_results["messages"] = msg_results
            
            # Calculate totals
            total_migrated = conv_results["migrated"] + msg_results["migrated"]
            total_errors = conv_results["errors"] + msg_results["errors"]
            
            migration_results["total_migrated"] = total_migrated
            migration_results["total_errors"] = total_errors
            migration_results["success"] = total_errors == 0
            migration_results["completed_at"] = datetime.utcnow().isoformat()
            
            logger.info(f"Migration completed: {total_migrated} records migrated, {total_errors} errors")
            return migration_results
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            migration_results["error"] = str(e)
            migration_results["completed_at"] = datetime.utcnow().isoformat()
            return migration_results
    
    def migrate_conversations(self) -> Dict[str, int]:
        """
        Migrate conversations from SQLite to Weaviate.
        
        Returns:
            Dict with migration statistics
        """
        logger.info("Migrating conversations...")
        
        results = {"migrated": 0, "errors": 0, "error_details": []}
        
        try:
            # Get all conversations from SQLite
            conversations = self.sqlite_session.query(SQLiteConversation).all()
            logger.info(f"Found {len(conversations)} conversations to migrate")
            
            conversation_collection = self.weaviate_client.collections.get("Conversation")
            
            for conv in conversations:
                try:
                    # Convert SQLite conversation to Weaviate format
                    weaviate_data = self._convert_conversation_to_weaviate(conv)
                    
                    # Insert into Weaviate
                    conversation_collection.data.insert(
                        properties=weaviate_data,
                        uuid=uuid.UUID(conv.id) if self._is_valid_uuid(conv.id) else None
                    )
                    
                    results["migrated"] += 1
                    
                except Exception as e:
                    logger.error(f"Error migrating conversation {conv.id}: {e}")
                    results["errors"] += 1
                    results["error_details"].append({
                        "conversation_id": conv.id,
                        "error": str(e)
                    })
            
            logger.info(f"Conversation migration completed: {results['migrated']} migrated, {results['errors']} errors")
            return results
            
        except Exception as e:
            logger.error(f"Failed to migrate conversations: {e}")
            results["errors"] = 1
            results["error_details"].append({"error": str(e)})
            return results
    
    def migrate_messages(self) -> Dict[str, int]:
        """
        Migrate messages from SQLite to Weaviate.
        
        Returns:
            Dict with migration statistics
        """
        logger.info("Migrating messages...")
        
        results = {"migrated": 0, "errors": 0, "error_details": []}
        
        try:
            # Get all messages from SQLite
            messages = self.sqlite_session.query(SQLiteMessage).all()
            logger.info(f"Found {len(messages)} messages to migrate")
            
            message_collection = self.weaviate_client.collections.get("Message")
            
            for msg in messages:
                try:
                    # Convert SQLite message to Weaviate format
                    weaviate_data = self._convert_message_to_weaviate(msg)
                    
                    # Insert into Weaviate
                    message_collection.data.insert(
                        properties=weaviate_data,
                        uuid=uuid.UUID(msg.id) if self._is_valid_uuid(msg.id) else None
                    )
                    
                    results["migrated"] += 1
                    
                except Exception as e:
                    logger.error(f"Error migrating message {msg.id}: {e}")
                    results["errors"] += 1
                    results["error_details"].append({
                        "message_id": msg.id,
                        "error": str(e)
                    })
            
            logger.info(f"Message migration completed: {results['migrated']} migrated, {results['errors']} errors")
            return results
            
        except Exception as e:
            logger.error(f"Failed to migrate messages: {e}")
            results["errors"] = 1
            results["error_details"].append({"error": str(e)})
            return results
    
    def _convert_conversation_to_weaviate(self, conv: SQLiteConversation) -> Dict[str, Any]:
        """
        Convert SQLite conversation to Weaviate format.
        
        Args:
            conv: SQLite conversation object
            
        Returns:
            Dict with Weaviate-compatible data
        """
        return {
            "conversationId": conv.id,
            "title": conv.title or "Untitled Conversation",
            "userId": conv.user_id or "unknown",
            "createdAt": conv.created_at.isoformat() if conv.created_at else datetime.utcnow().isoformat(),
            "updatedAt": conv.updated_at.isoformat() if conv.updated_at else datetime.utcnow().isoformat(),
            "isActive": True,  # Default to active for migrated conversations
            "metadata": {
                "migrated_from_sqlite": True,
                "original_id": conv.id,
                "migration_timestamp": datetime.utcnow().isoformat()
            }
        }
    
    def _convert_message_to_weaviate(self, msg: SQLiteMessage) -> Dict[str, Any]:
        """
        Convert SQLite message to Weaviate format.
        
        Args:
            msg: SQLite message object
            
        Returns:
            Dict with Weaviate-compatible data
        """
        # Handle tool calls - convert to JSON string if present
        tool_calls_json = None
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            try:
                if isinstance(msg.tool_calls, str):
                    tool_calls_json = msg.tool_calls
                else:
                    tool_calls_json = json.dumps(msg.tool_calls)
            except Exception as e:
                logger.warning(f"Could not serialize tool calls for message {msg.id}: {e}")
                tool_calls_json = "{}"
        
        # Handle extra data
        extra_data = {}
        if hasattr(msg, 'extra_data') and msg.extra_data:
            try:
                if isinstance(msg.extra_data, dict):
                    extra_data = msg.extra_data
                elif isinstance(msg.extra_data, str):
                    extra_data = json.loads(msg.extra_data)
            except Exception as e:
                logger.warning(f"Could not parse extra data for message {msg.id}: {e}")
        
        # Add migration metadata
        extra_data.update({
            "migrated_from_sqlite": True,
            "original_id": msg.id,
            "migration_timestamp": datetime.utcnow().isoformat()
        })
        
        return {
            "messageId": msg.id,
            "conversationId": msg.conversation_id,
            "role": msg.role or "user",
            "content": msg.content or "",
            "createdAt": msg.created_at.isoformat() if msg.created_at else datetime.utcnow().isoformat(),
            "toolCalls": tool_calls_json or "{}",
            "extraData": extra_data
        }
    
    def _is_valid_uuid(self, uuid_string: str) -> bool:
        """
        Check if string is a valid UUID.
        
        Args:
            uuid_string: String to check
            
        Returns:
            True if valid UUID, False otherwise
        """
        try:
            uuid.UUID(uuid_string)
            return True
        except (ValueError, TypeError):
            return False
    
    def verify_migration(self) -> Dict[str, Any]:
        """
        Verify migration by comparing record counts.
        
        Returns:
            Dict with verification results
        """
        logger.info("Verifying migration...")
        
        verification_results = {
            "sqlite_counts": {},
            "weaviate_counts": {},
            "matches": {},
            "verification_passed": False
        }
        
        try:
            # Count SQLite records
            sqlite_conv_count = self.sqlite_session.query(SQLiteConversation).count()
            sqlite_msg_count = self.sqlite_session.query(SQLiteMessage).count()
            
            verification_results["sqlite_counts"] = {
                "conversations": sqlite_conv_count,
                "messages": sqlite_msg_count
            }
            
            # Count Weaviate records
            conv_collection = self.weaviate_client.collections.get("Conversation")
            msg_collection = self.weaviate_client.collections.get("Message")
            
            weaviate_conv_count = len(conv_collection.query.fetch_objects().objects)
            weaviate_msg_count = len(msg_collection.query.fetch_objects().objects)
            
            verification_results["weaviate_counts"] = {
                "conversations": weaviate_conv_count,
                "messages": weaviate_msg_count
            }
            
            # Check matches
            conv_match = sqlite_conv_count == weaviate_conv_count
            msg_match = sqlite_msg_count == weaviate_msg_count
            
            verification_results["matches"] = {
                "conversations": conv_match,
                "messages": msg_match
            }
            
            verification_results["verification_passed"] = conv_match and msg_match
            
            logger.info(f"Migration verification: {verification_results}")
            return verification_results
            
        except Exception as e:
            logger.error(f"Migration verification failed: {e}")
            verification_results["error"] = str(e)
            return verification_results


def migrate_sqlite_to_weaviate(sqlite_session: Session, weaviate_client: WeaviateClient) -> Dict[str, Any]:
    """
    Convenience function to migrate SQLite data to Weaviate.
    
    Args:
        sqlite_session: SQLAlchemy session for SQLite database
        weaviate_client: Weaviate client instance
        
    Returns:
        Dict containing migration results
    """
    migration_manager = WeaviateMigrationManager(sqlite_session, weaviate_client)
    return migration_manager.migrate_all_data()
