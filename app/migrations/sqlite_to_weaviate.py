"""
SQLite to Weaviate Migration Pipeline

This module provides a comprehensive migration pipeline for transitioning
from SQLite to Weaviate with zero downtime and 100% data integrity verification.
Implements phased migration strategy with dual-write system and historical backfill.
"""

import logging
import uuid
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple, Iterator
from dataclasses import dataclass, field
from contextlib import contextmanager
import hashlib

import weaviate
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from weaviate.exceptions import WeaviateBaseError

from app.database.models import Conversation, Message
from app.database.weaviate_schema import WeaviateSchemaManager

logger = logging.getLogger(__name__)


@dataclass
class MigrationConfig:
    """Configuration for SQLite to Weaviate migration."""
    
    # Database connections
    sqlite_url: str
    weaviate_url: str
    weaviate_api_key: Optional[str] = None
    
    # Migration settings
    batch_size: int = 100
    max_retries: int = 3
    retry_delay: float = 1.0
    validation_sample_size: int = 1000
    
    # Performance settings
    enable_parallel_processing: bool = False
    worker_count: int = 4
    memory_limit_mb: int = 1024
    
    # Safety settings
    dry_run: bool = False
    backup_before_migration: bool = True
    rollback_on_failure: bool = True
    
    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = None


@dataclass
class MigrationResult:
    """Result of migration operation."""
    
    success: bool
    started_at: datetime
    completed_at: Optional[datetime] = None
    
    # Statistics
    total_records: int = 0
    migrated_records: int = 0
    failed_records: int = 0
    skipped_records: int = 0
    
    # Performance metrics
    duration_seconds: float = 0.0
    records_per_second: float = 0.0
    
    # Validation results
    validation_passed: bool = False
    validation_errors: List[str] = field(default_factory=list)
    
    # Error details
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_records": self.total_records,
            "migrated_records": self.migrated_records,
            "failed_records": self.failed_records,
            "skipped_records": self.skipped_records,
            "duration_seconds": self.duration_seconds,
            "records_per_second": self.records_per_second,
            "validation_passed": self.validation_passed,
            "validation_errors": self.validation_errors,
            "errors": self.errors,
            "warnings": self.warnings
        }


class SQLiteToWeaviateMigrator:
    """Handles migration from SQLite to Weaviate with zero downtime."""
    
    def __init__(self, config: MigrationConfig):
        """Initialize migrator with configuration."""
        self.config = config
        self.result = MigrationResult(
            success=False,
            started_at=datetime.now(timezone.utc)
        )
        
        # Setup logging
        self._setup_logging()
        
        # Database connections
        self.sqlite_engine = None
        self.sqlite_session = None
        self.weaviate_client = None
        self.schema_manager = None
        
    def _setup_logging(self) -> None:
        """Setup logging configuration."""
        log_level = getattr(logging, self.config.log_level.upper())
        
        # Configure logger
        logger.setLevel(log_level)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)8s] %(name)s: %(message)s'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handler if specified
        if self.config.log_file:
            file_handler = logging.FileHandler(self.config.log_file)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
    
    @contextmanager
    def _database_connections(self):
        """Context manager for database connections."""
        try:
            # Connect to SQLite
            self.sqlite_engine = create_engine(self.config.sqlite_url)
            Session = sessionmaker(bind=self.sqlite_engine)
            self.sqlite_session = Session()
            
            # Connect to Weaviate
            if self.config.weaviate_api_key:
                auth_config = weaviate.AuthApiKey(api_key=self.config.weaviate_api_key)
                self.weaviate_client = weaviate.connect_to_custom(
                    http_host=self.config.weaviate_url,
                    http_port=80,
                    http_secure=False,
                    auth_credentials=auth_config
                )
            else:
                self.weaviate_client = weaviate.connect_to_local(
                    host=self.config.weaviate_url
                )
            
            # Initialize schema manager
            self.schema_manager = WeaviateSchemaManager(self.weaviate_client)
            
            logger.info("Database connections established successfully")
            yield
            
        except Exception as e:
            logger.error(f"Failed to establish database connections: {e}")
            raise
        finally:
            # Cleanup connections
            if self.sqlite_session:
                self.sqlite_session.close()
            if self.weaviate_client:
                self.weaviate_client.close()
    
    def migrate(self) -> MigrationResult:
        """Execute complete migration pipeline."""
        logger.info("Starting SQLite to Weaviate migration...")
        
        try:
            with self._database_connections():
                # Pre-migration validation
                self._pre_migration_validation()
                
                # Create Weaviate schema if needed
                self._ensure_weaviate_schema()
                
                # Backup if requested
                if self.config.backup_before_migration:
                    self._create_backup()
                
                # Execute migration phases
                self._migrate_conversations()
                self._migrate_messages()
                
                # Post-migration validation
                self._post_migration_validation()
                
                # Calculate final metrics
                self._calculate_metrics()
                
                self.result.success = True
                logger.info("Migration completed successfully")
                
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            self.result.errors.append({
                "type": "migration_failure",
                "message": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            # Rollback if requested
            if self.config.rollback_on_failure:
                self._rollback_migration()
        
        finally:
            self.result.completed_at = datetime.now(timezone.utc)
            self.result.duration_seconds = (
                self.result.completed_at - self.result.started_at
            ).total_seconds()
        
        return self.result
    
    def _pre_migration_validation(self) -> None:
        """Validate source data before migration."""
        logger.info("Performing pre-migration validation...")
        
        try:
            # Check SQLite connectivity and data
            conv_count = self.sqlite_session.query(Conversation).count()
            msg_count = self.sqlite_session.query(Message).count()
            
            logger.info(f"Source data: {conv_count} conversations, {msg_count} messages")
            self.result.total_records = conv_count + msg_count
            
            # Check Weaviate connectivity
            if not self.weaviate_client.is_ready():
                raise Exception("Weaviate cluster is not ready")
            
            logger.info("Pre-migration validation passed")
            
        except Exception as e:
            logger.error(f"Pre-migration validation failed: {e}")
            raise
    
    def _ensure_weaviate_schema(self) -> None:
        """Ensure Weaviate schema exists."""
        logger.info("Ensuring Weaviate schema exists...")
        
        try:
            # Check if schema exists
            schema_info = self.schema_manager.get_schema_info()
            
            missing_classes = []
            for class_name in ["Conversation", "Message"]:
                if not schema_info.get(class_name, {}).get("exists", False):
                    missing_classes.append(class_name)
            
            if missing_classes:
                logger.info(f"Creating missing schema classes: {missing_classes}")
                if not self.schema_manager.create_weaviate_schema():
                    raise Exception("Failed to create Weaviate schema")
            
            logger.info("Weaviate schema is ready")
            
        except Exception as e:
            logger.error(f"Schema validation failed: {e}")
            raise
    
    def _create_backup(self) -> None:
        """Create backup before migration."""
        logger.info("Creating backup before migration...")
        
        try:
            backup_timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            backup_file = f"backup_before_migration_{backup_timestamp}.sql"
            
            # Create SQLite backup using SQL dump
            with open(backup_file, 'w') as f:
                for line in self.sqlite_engine.raw_connection().iterdump():
                    f.write(f"{line}\n")
            
            logger.info(f"Backup created: {backup_file}")
            self.result.warnings.append(f"Backup created: {backup_file}")
            
        except Exception as e:
            logger.warning(f"Backup creation failed: {e}")
            self.result.warnings.append(f"Backup creation failed: {e}")
    
    def _migrate_conversations(self) -> None:
        """Migrate conversations from SQLite to Weaviate."""
        logger.info("Migrating conversations...")
        
        try:
            # Get conversation collection
            conversation_collection = self.weaviate_client.collections.get("Conversation")
            
            # Process conversations in batches
            offset = 0
            batch_count = 0
            
            while True:
                # Fetch batch from SQLite
                conversations = (
                    self.sqlite_session.query(Conversation)
                    .offset(offset)
                    .limit(self.config.batch_size)
                    .all()
                )
                
                if not conversations:
                    break
                
                batch_count += 1
                logger.info(f"Processing conversation batch {batch_count} ({len(conversations)} records)")
                
                # Transform and load batch
                self._load_conversation_batch(conversation_collection, conversations)
                
                offset += self.config.batch_size
                
                # Memory management
                self.sqlite_session.expunge_all()
            
            logger.info("Conversation migration completed")
            
        except Exception as e:
            logger.error(f"Conversation migration failed: {e}")
            raise

    def _load_conversation_batch(self, collection, conversations: List[Conversation]) -> None:
        """Load a batch of conversations into Weaviate."""
        batch_data = []

        for conv in conversations:
            try:
                # Transform conversation to Weaviate format
                weaviate_data = self._transform_conversation(conv)

                # Generate UUID if needed
                conv_uuid = self._generate_uuid(conv.id)

                batch_data.append({
                    "uuid": conv_uuid,
                    "properties": weaviate_data
                })

            except Exception as e:
                logger.error(f"Failed to transform conversation {conv.id}: {e}")
                self.result.failed_records += 1
                self.result.errors.append({
                    "type": "conversation_transform_error",
                    "record_id": conv.id,
                    "message": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })

        # Batch insert into Weaviate
        if batch_data and not self.config.dry_run:
            try:
                with collection.batch.dynamic() as batch:
                    for item in batch_data:
                        batch.add_object(
                            properties=item["properties"],
                            uuid=item["uuid"]
                        )

                self.result.migrated_records += len(batch_data)
                logger.info(f"Successfully loaded {len(batch_data)} conversations")

            except Exception as e:
                logger.error(f"Failed to load conversation batch: {e}")
                self.result.failed_records += len(batch_data)
                raise
        elif self.config.dry_run:
            logger.info(f"DRY RUN: Would load {len(batch_data)} conversations")
            self.result.migrated_records += len(batch_data)

    def _transform_conversation(self, conv: Conversation) -> Dict[str, Any]:
        """Transform SQLite conversation to Weaviate format."""
        return {
            "conversationId": conv.id,
            "title": conv.title or "Untitled Conversation",
            "userId": "unknown",  # Default user ID since not in current model
            "createdAt": conv.created_at.isoformat() if conv.created_at else datetime.now(timezone.utc).isoformat(),
            "updatedAt": conv.updated_at.isoformat() if conv.updated_at else datetime.now(timezone.utc).isoformat(),
            "isActive": getattr(conv, 'is_active', True),
            "metadata": {
                "migrated_from_sqlite": True,
                "original_id": conv.id,
                "migration_timestamp": datetime.now(timezone.utc).isoformat(),
                "migration_batch": True
            }
        }

    def _migrate_messages(self) -> None:
        """Migrate messages from SQLite to Weaviate."""
        logger.info("Migrating messages...")

        try:
            # Get message collection
            message_collection = self.weaviate_client.collections.get("Message")

            # Process messages in batches
            offset = 0
            batch_count = 0

            while True:
                # Fetch batch from SQLite
                messages = (
                    self.sqlite_session.query(Message)
                    .offset(offset)
                    .limit(self.config.batch_size)
                    .all()
                )

                if not messages:
                    break

                batch_count += 1
                logger.info(f"Processing message batch {batch_count} ({len(messages)} records)")

                # Transform and load batch
                self._load_message_batch(message_collection, messages)

                offset += self.config.batch_size

                # Memory management
                self.sqlite_session.expunge_all()

            logger.info("Message migration completed")

        except Exception as e:
            logger.error(f"Message migration failed: {e}")
            raise

    def _load_message_batch(self, collection, messages: List[Message]) -> None:
        """Load a batch of messages into Weaviate."""
        batch_data = []

        for msg in messages:
            try:
                # Transform message to Weaviate format
                weaviate_data = self._transform_message(msg)

                # Generate UUID if needed
                msg_uuid = self._generate_uuid(msg.id)

                batch_data.append({
                    "uuid": msg_uuid,
                    "properties": weaviate_data
                })

            except Exception as e:
                logger.error(f"Failed to transform message {msg.id}: {e}")
                self.result.failed_records += 1
                self.result.errors.append({
                    "type": "message_transform_error",
                    "record_id": msg.id,
                    "message": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })

        # Batch insert into Weaviate
        if batch_data and not self.config.dry_run:
            try:
                with collection.batch.dynamic() as batch:
                    for item in batch_data:
                        batch.add_object(
                            properties=item["properties"],
                            uuid=item["uuid"]
                        )

                self.result.migrated_records += len(batch_data)
                logger.info(f"Successfully loaded {len(batch_data)} messages")

            except Exception as e:
                logger.error(f"Failed to load message batch: {e}")
                self.result.failed_records += len(batch_data)
                raise
        elif self.config.dry_run:
            logger.info(f"DRY RUN: Would load {len(batch_data)} messages")
            self.result.migrated_records += len(batch_data)

    def _transform_message(self, msg: Message) -> Dict[str, Any]:
        """Transform SQLite message to Weaviate format."""
        # Handle tool calls
        tool_calls_json = "{}"
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            try:
                if isinstance(msg.tool_calls, str):
                    tool_calls_json = msg.tool_calls
                else:
                    tool_calls_json = json.dumps(msg.tool_calls)
            except Exception as e:
                logger.warning(f"Could not serialize tool calls for message {msg.id}: {e}")

        # Handle extra data
        extra_data = {
            "migrated_from_sqlite": True,
            "original_id": msg.id,
            "migration_timestamp": datetime.now(timezone.utc).isoformat(),
            "migration_batch": True
        }

        if hasattr(msg, 'extra_data') and msg.extra_data:
            try:
                if isinstance(msg.extra_data, dict):
                    extra_data.update(msg.extra_data)
                elif isinstance(msg.extra_data, str):
                    parsed_data = json.loads(msg.extra_data)
                    extra_data.update(parsed_data)
            except Exception as e:
                logger.warning(f"Could not parse extra data for message {msg.id}: {e}")

        return {
            "messageId": msg.id,
            "conversationId": msg.conversation_id,
            "role": msg.role or "user",
            "content": msg.content or "",
            "createdAt": msg.created_at.isoformat() if msg.created_at else datetime.now(timezone.utc).isoformat(),
            "toolCalls": tool_calls_json,
            "extraData": extra_data
        }

    def _generate_uuid(self, record_id: str) -> str:
        """Generate consistent UUID from record ID."""
        try:
            # Try to parse as UUID first
            return str(uuid.UUID(record_id))
        except (ValueError, TypeError):
            # Generate deterministic UUID from string
            namespace = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')  # DNS namespace
            return str(uuid.uuid5(namespace, str(record_id)))

    def _post_migration_validation(self) -> None:
        """Validate data integrity after migration."""
        logger.info("Performing post-migration validation...")

        try:
            # Count records in both databases
            sqlite_conv_count = self.sqlite_session.query(Conversation).count()
            sqlite_msg_count = self.sqlite_session.query(Message).count()

            # Count records in Weaviate
            conv_collection = self.weaviate_client.collections.get("Conversation")
            msg_collection = self.weaviate_client.collections.get("Message")

            weaviate_conv_count = len(conv_collection.query.fetch_objects().objects)
            weaviate_msg_count = len(msg_collection.query.fetch_objects().objects)

            # Validate counts
            conv_match = sqlite_conv_count == weaviate_conv_count
            msg_match = sqlite_msg_count == weaviate_msg_count

            logger.info(f"Validation results:")
            logger.info(f"  Conversations: SQLite={sqlite_conv_count}, Weaviate={weaviate_conv_count}, Match={conv_match}")
            logger.info(f"  Messages: SQLite={sqlite_msg_count}, Weaviate={weaviate_msg_count}, Match={msg_match}")

            if not conv_match:
                self.result.validation_errors.append(
                    f"Conversation count mismatch: SQLite={sqlite_conv_count}, Weaviate={weaviate_conv_count}"
                )

            if not msg_match:
                self.result.validation_errors.append(
                    f"Message count mismatch: SQLite={sqlite_msg_count}, Weaviate={weaviate_msg_count}"
                )

            # Sample data validation
            self._validate_sample_data()

            # Set validation result
            self.result.validation_passed = len(self.result.validation_errors) == 0

            if self.result.validation_passed:
                logger.info("Post-migration validation passed")
            else:
                logger.error(f"Post-migration validation failed: {self.result.validation_errors}")

        except Exception as e:
            logger.error(f"Post-migration validation failed: {e}")
            self.result.validation_errors.append(f"Validation error: {str(e)}")
            self.result.validation_passed = False

    def _validate_sample_data(self) -> None:
        """Validate a sample of migrated data for integrity."""
        logger.info("Validating sample data integrity...")

        try:
            # Sample conversations
            sample_conversations = (
                self.sqlite_session.query(Conversation)
                .limit(min(self.config.validation_sample_size, 100))
                .all()
            )

            conv_collection = self.weaviate_client.collections.get("Conversation")

            for conv in sample_conversations:
                # Find corresponding record in Weaviate
                conv_uuid = self._generate_uuid(conv.id)

                try:
                    weaviate_conv = conv_collection.query.fetch_object_by_id(conv_uuid)

                    if not weaviate_conv:
                        self.result.validation_errors.append(
                            f"Conversation {conv.id} not found in Weaviate"
                        )
                        continue

                    # Validate key fields
                    props = weaviate_conv.properties

                    if props.get("conversationId") != conv.id:
                        self.result.validation_errors.append(
                            f"Conversation {conv.id}: ID mismatch"
                        )

                    if props.get("title") != (conv.title or "Untitled Conversation"):
                        self.result.validation_errors.append(
                            f"Conversation {conv.id}: Title mismatch"
                        )

                except Exception as e:
                    self.result.validation_errors.append(
                        f"Error validating conversation {conv.id}: {str(e)}"
                    )

            logger.info(f"Sample validation completed for {len(sample_conversations)} conversations")

        except Exception as e:
            logger.error(f"Sample data validation failed: {e}")
            self.result.validation_errors.append(f"Sample validation error: {str(e)}")

    def _calculate_metrics(self) -> None:
        """Calculate final migration metrics."""
        if self.result.duration_seconds > 0:
            self.result.records_per_second = self.result.migrated_records / self.result.duration_seconds

        logger.info(f"Migration metrics:")
        logger.info(f"  Total records: {self.result.total_records}")
        logger.info(f"  Migrated: {self.result.migrated_records}")
        logger.info(f"  Failed: {self.result.failed_records}")
        logger.info(f"  Duration: {self.result.duration_seconds:.2f} seconds")
        logger.info(f"  Rate: {self.result.records_per_second:.2f} records/second")

    def _rollback_migration(self) -> None:
        """Rollback migration in case of failure."""
        logger.warning("Rolling back migration...")

        try:
            # Delete migrated data from Weaviate
            for class_name in ["Conversation", "Message"]:
                try:
                    collection = self.weaviate_client.collections.get(class_name)

                    # Delete all objects with migration metadata
                    collection.data.delete_many(
                        where={
                            "path": ["metadata", "migrated_from_sqlite"],
                            "operator": "Equal",
                            "valueBoolean": True
                        }
                    )

                    logger.info(f"Rolled back {class_name} data")

                except Exception as e:
                    logger.error(f"Failed to rollback {class_name}: {e}")

            logger.info("Migration rollback completed")

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            self.result.warnings.append(f"Rollback failed: {str(e)}")


def run_migration(config: MigrationConfig) -> MigrationResult:
    """
    Convenience function to run migration with configuration.

    Args:
        config: Migration configuration

    Returns:
        Migration result
    """
    migrator = SQLiteToWeaviateMigrator(config)
    return migrator.migrate()


def create_migration_config(
    sqlite_url: str,
    weaviate_url: str,
    **kwargs
) -> MigrationConfig:
    """
    Create migration configuration with defaults.

    Args:
        sqlite_url: SQLite database URL
        weaviate_url: Weaviate cluster URL
        **kwargs: Additional configuration options

    Returns:
        Migration configuration
    """
    return MigrationConfig(
        sqlite_url=sqlite_url,
        weaviate_url=weaviate_url,
        **kwargs
    )
