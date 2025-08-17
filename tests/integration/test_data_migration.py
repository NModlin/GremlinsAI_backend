"""
Integration tests for SQLite to Weaviate data migration pipeline.

Tests verify zero-downtime migration with 100% data integrity verification
using temporary in-memory SQLite database and mocked Weaviate client.
"""

import pytest
import tempfile
import os
import json
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.models import Base, Conversation, Message
from app.migrations.sqlite_to_weaviate import (
    SQLiteToWeaviateMigrator,
    MigrationConfig,
    MigrationResult,
    run_migration,
    create_migration_config
)


class TestDataMigration:
    """Test cases for data migration pipeline."""
    
    @pytest.fixture
    def temp_sqlite_db(self):
        """Create temporary SQLite database with sample data."""
        # Create temporary database file
        db_fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(db_fd)
        
        try:
            # Create engine and tables
            engine = create_engine(f'sqlite:///{db_path}')
            Base.metadata.create_all(engine)
            
            # Create session and add sample data
            Session = sessionmaker(bind=engine)
            session = Session()
            
            # Add sample conversations
            conversations = [
                Conversation(
                    id="conv-1",
                    title="Test Conversation 1",
                    created_at=datetime(2024, 1, 1, 12, 0, 0),
                    updated_at=datetime(2024, 1, 1, 12, 30, 0)
                ),
                Conversation(
                    id="conv-2",
                    title="Test Conversation 2",
                    created_at=datetime(2024, 1, 2, 10, 0, 0),
                    updated_at=datetime(2024, 1, 2, 10, 15, 0)
                ),
                Conversation(
                    id="conv-3",
                    title=None,  # Test null title
                    created_at=datetime(2024, 1, 3, 14, 0, 0),
                    updated_at=datetime(2024, 1, 3, 14, 5, 0)
                )
            ]
            
            for conv in conversations:
                session.add(conv)
            
            # Add sample messages
            messages = [
                Message(
                    id="msg-1",
                    conversation_id="conv-1",
                    role="user",
                    content="Hello, how are you?",
                    created_at=datetime(2024, 1, 1, 12, 0, 0),
                    tool_calls=None,
                    extra_data=None
                ),
                Message(
                    id="msg-2",
                    conversation_id="conv-1", 
                    role="assistant",
                    content="I'm doing well, thank you!",
                    created_at=datetime(2024, 1, 1, 12, 1, 0),
                    tool_calls='{"function": "respond"}',
                    extra_data='{"confidence": 0.95}'
                ),
                Message(
                    id="msg-3",
                    conversation_id="conv-2",
                    role="user",
                    content="What's the weather like?",
                    created_at=datetime(2024, 1, 2, 10, 0, 0),
                    tool_calls=None,
                    extra_data=None
                ),
                Message(
                    id="msg-4",
                    conversation_id="conv-2",
                    role="assistant", 
                    content="I'll check the weather for you.",
                    created_at=datetime(2024, 1, 2, 10, 1, 0),
                    tool_calls='{"function": "get_weather", "args": {}}',
                    extra_data='{"tool_used": true}'
                ),
                Message(
                    id="msg-5",
                    conversation_id="conv-3",
                    role="user",
                    content="Test message with no extra data",
                    created_at=datetime(2024, 1, 3, 14, 0, 0),
                    tool_calls=None,
                    extra_data=None
                )
            ]
            
            for msg in messages:
                session.add(msg)
            
            session.commit()
            session.close()
            engine.dispose()  # Close all connections

            yield f'sqlite:///{db_path}'

        finally:
            # Cleanup
            try:
                if os.path.exists(db_path):
                    os.unlink(db_path)
            except PermissionError:
                # On Windows, sometimes the file is still locked
                import time
                time.sleep(0.1)
                try:
                    os.unlink(db_path)
                except PermissionError:
                    pass  # Ignore if we can't delete
    
    @pytest.fixture
    def mock_weaviate_client(self):
        """Create mock Weaviate client."""
        client = Mock()
        
        # Mock client properties
        client.is_ready.return_value = True
        client.close = Mock()
        
        # Mock collections
        client.collections = Mock()
        client.collections.get = Mock()
        
        # Mock conversation collection
        conv_collection = Mock()
        conv_collection.batch = Mock()
        conv_collection.batch.dynamic = Mock()
        conv_collection.query = Mock()
        conv_collection.query.fetch_objects.return_value = Mock(objects=[])
        conv_collection.query.fetch_object_by_id = Mock(return_value=None)
        conv_collection.data = Mock()
        conv_collection.data.delete_many = Mock()
        
        # Mock message collection
        msg_collection = Mock()
        msg_collection.batch = Mock()
        msg_collection.batch.dynamic = Mock()
        msg_collection.query = Mock()
        msg_collection.query.fetch_objects.return_value = Mock(objects=[])
        msg_collection.query.fetch_object_by_id = Mock(return_value=None)
        msg_collection.data = Mock()
        msg_collection.data.delete_many = Mock()
        
        # Configure collection getter
        def get_collection(name):
            if name == "Conversation":
                return conv_collection
            elif name == "Message":
                return msg_collection
            else:
                raise ValueError(f"Unknown collection: {name}")
        
        client.collections.get.side_effect = get_collection
        
        return client
    
    @pytest.fixture
    def mock_schema_manager(self):
        """Create mock schema manager."""
        with patch('app.migrations.sqlite_to_weaviate.WeaviateSchemaManager') as mock_class:
            mock_manager = Mock()
            mock_manager.get_schema_info.return_value = {
                "Conversation": {"exists": True},
                "Message": {"exists": True}
            }
            mock_manager.create_weaviate_schema.return_value = True
            mock_class.return_value = mock_manager
            yield mock_manager
    
    def test_migration_config_creation(self):
        """Test migration configuration creation."""
        config = create_migration_config(
            sqlite_url="sqlite:///test.db",
            weaviate_url="http://localhost:8080",
            batch_size=50,
            dry_run=True
        )
        
        assert config.sqlite_url == "sqlite:///test.db"
        assert config.weaviate_url == "http://localhost:8080"
        assert config.batch_size == 50
        assert config.dry_run is True
        assert config.max_retries == 3  # Default value
    
    def test_migration_initialization(self, temp_sqlite_db):
        """Test migrator initialization."""
        config = MigrationConfig(
            sqlite_url=temp_sqlite_db,
            weaviate_url="http://localhost:8080"
        )
        
        migrator = SQLiteToWeaviateMigrator(config)
        
        assert migrator.config == config
        assert isinstance(migrator.result, MigrationResult)
        assert migrator.result.success is False
        assert migrator.result.started_at is not None
    
    @patch('weaviate.connect_to_local')
    def test_successful_migration(self, mock_connect, temp_sqlite_db, mock_weaviate_client, mock_schema_manager):
        """Test successful migration with mocked Weaviate client."""
        # Setup mocks
        mock_connect.return_value = mock_weaviate_client
        
        # Create migration config
        config = MigrationConfig(
            sqlite_url=temp_sqlite_db,
            weaviate_url="http://localhost:8080",
            batch_size=2,  # Small batch for testing
            dry_run=False
        )
        
        # Run migration
        migrator = SQLiteToWeaviateMigrator(config)
        result = migrator.migrate()
        
        # Verify result
        assert result.success is True
        assert result.total_records == 8  # 3 conversations + 5 messages
        assert result.migrated_records == 8
        assert result.failed_records == 0
        assert result.validation_passed is True
        assert len(result.errors) == 0
        
        # Verify Weaviate client calls
        assert mock_weaviate_client.collections.get.call_count >= 2
        mock_weaviate_client.collections.get.assert_any_call("Conversation")
        mock_weaviate_client.collections.get.assert_any_call("Message")
    
    @patch('weaviate.connect_to_local')
    def test_dry_run_migration(self, mock_connect, temp_sqlite_db, mock_weaviate_client, mock_schema_manager):
        """Test dry run migration."""
        # Setup mocks
        mock_connect.return_value = mock_weaviate_client
        
        # Create migration config with dry run
        config = MigrationConfig(
            sqlite_url=temp_sqlite_db,
            weaviate_url="http://localhost:8080",
            batch_size=10,
            dry_run=True
        )
        
        # Run migration
        result = run_migration(config)
        
        # Verify result
        assert result.success is True
        assert result.total_records == 8
        assert result.migrated_records == 8  # Should count dry run records
        assert result.failed_records == 0
        
        # Verify no actual data was written (batch operations not called)
        conv_collection = mock_weaviate_client.collections.get("Conversation")
        msg_collection = mock_weaviate_client.collections.get("Message")
        
        # In dry run, batch.dynamic should not be called
        conv_collection.batch.dynamic.assert_not_called()
        msg_collection.batch.dynamic.assert_not_called()
    
    @patch('weaviate.connect_to_local')
    def test_batch_processing(self, mock_connect, temp_sqlite_db, mock_weaviate_client, mock_schema_manager):
        """Test that data is processed in correct batches."""
        # Setup mocks
        mock_connect.return_value = mock_weaviate_client
        
        # Track batch operations
        conv_batches = []
        msg_batches = []
        
        def track_conv_batch():
            batch_mock = Mock()
            batch_mock.__enter__ = Mock(return_value=batch_mock)
            batch_mock.__exit__ = Mock(return_value=None)
            batch_mock.add_object = Mock()
            conv_batches.append(batch_mock)
            return batch_mock
        
        def track_msg_batch():
            batch_mock = Mock()
            batch_mock.__enter__ = Mock(return_value=batch_mock)
            batch_mock.__exit__ = Mock(return_value=None)
            batch_mock.add_object = Mock()
            msg_batches.append(batch_mock)
            return batch_mock
        
        conv_collection = mock_weaviate_client.collections.get("Conversation")
        msg_collection = mock_weaviate_client.collections.get("Message")
        
        conv_collection.batch.dynamic.side_effect = track_conv_batch
        msg_collection.batch.dynamic.side_effect = track_msg_batch
        
        # Create migration config with small batch size
        config = MigrationConfig(
            sqlite_url=temp_sqlite_db,
            weaviate_url="http://localhost:8080",
            batch_size=2,  # Force multiple batches
            dry_run=False
        )
        
        # Run migration
        result = run_migration(config)
        
        # Verify batching
        assert result.success is True
        
        # Should have multiple conversation batches (3 conversations, batch size 2)
        assert len(conv_batches) == 2  # Ceil(3/2) = 2 batches
        
        # Should have multiple message batches (5 messages, batch size 2)
        assert len(msg_batches) == 3  # Ceil(5/2) = 3 batches
        
        # Verify add_object calls
        total_conv_adds = sum(batch.add_object.call_count for batch in conv_batches)
        total_msg_adds = sum(batch.add_object.call_count for batch in msg_batches)
        
        assert total_conv_adds == 3  # 3 conversations
        assert total_msg_adds == 5   # 5 messages

    @patch('weaviate.connect_to_local')
    def test_data_transformation(self, mock_connect, temp_sqlite_db, mock_weaviate_client, mock_schema_manager):
        """Test that SQLite data is correctly transformed for Weaviate."""
        # Setup mocks
        mock_connect.return_value = mock_weaviate_client

        # Track transformed data
        transformed_conversations = []
        transformed_messages = []

        def capture_conv_data(*args, **kwargs):
            batch_mock = Mock()
            batch_mock.__enter__ = Mock(return_value=batch_mock)
            batch_mock.__exit__ = Mock(return_value=None)

            def capture_add_object(properties=None, uuid=None):
                transformed_conversations.append({
                    "uuid": uuid,
                    "properties": properties
                })

            batch_mock.add_object = capture_add_object
            return batch_mock

        def capture_msg_data(*args, **kwargs):
            batch_mock = Mock()
            batch_mock.__enter__ = Mock(return_value=batch_mock)
            batch_mock.__exit__ = Mock(return_value=None)

            def capture_add_object(properties=None, uuid=None):
                transformed_messages.append({
                    "uuid": uuid,
                    "properties": properties
                })

            batch_mock.add_object = capture_add_object
            return batch_mock

        conv_collection = mock_weaviate_client.collections.get("Conversation")
        msg_collection = mock_weaviate_client.collections.get("Message")

        conv_collection.batch.dynamic.side_effect = capture_conv_data
        msg_collection.batch.dynamic.side_effect = capture_msg_data

        # Run migration
        config = MigrationConfig(
            sqlite_url=temp_sqlite_db,
            weaviate_url="http://localhost:8080",
            batch_size=10,
            dry_run=False
        )

        result = run_migration(config)
        assert result.success is True

        # Verify conversation transformations
        assert len(transformed_conversations) == 3

        conv_1 = next(c for c in transformed_conversations if c["properties"]["conversationId"] == "conv-1")
        assert conv_1["properties"]["title"] == "Test Conversation 1"
        assert conv_1["properties"]["userId"] == "unknown"  # Default value
        assert conv_1["properties"]["isActive"] is True
        assert conv_1["properties"]["metadata"]["migrated_from_sqlite"] is True

        # Test null title handling
        conv_3 = next(c for c in transformed_conversations if c["properties"]["conversationId"] == "conv-3")
        assert conv_3["properties"]["title"] == "Untitled Conversation"

        # Verify message transformations
        assert len(transformed_messages) == 5

        msg_2 = next(m for m in transformed_messages if m["properties"]["messageId"] == "msg-2")
        assert msg_2["properties"]["conversationId"] == "conv-1"
        assert msg_2["properties"]["role"] == "assistant"
        assert msg_2["properties"]["content"] == "I'm doing well, thank you!"
        assert msg_2["properties"]["toolCalls"] == '{"function": "respond"}'
        assert msg_2["properties"]["extraData"]["confidence"] == 0.95
        assert msg_2["properties"]["extraData"]["migrated_from_sqlite"] is True

    @patch('weaviate.connect_to_local')
    def test_migration_failure_handling(self, mock_connect, temp_sqlite_db, mock_schema_manager):
        """Test migration failure handling and rollback."""
        # Setup mock to fail
        mock_client = Mock()
        mock_client.is_ready.return_value = True
        mock_client.close = Mock()
        mock_client.collections.get.side_effect = Exception("Weaviate connection failed")
        mock_connect.return_value = mock_client

        # Run migration
        config = MigrationConfig(
            sqlite_url=temp_sqlite_db,
            weaviate_url="http://localhost:8080",
            rollback_on_failure=True
        )

        result = run_migration(config)

        # Verify failure handling
        assert result.success is False
        assert len(result.errors) > 0
        assert "Weaviate connection failed" in str(result.errors[0]["message"])

    @patch('weaviate.connect_to_local')
    def test_validation_failure(self, mock_connect, temp_sqlite_db, mock_weaviate_client, mock_schema_manager):
        """Test validation failure detection."""
        # Setup mocks
        mock_connect.return_value = mock_weaviate_client

        # Mock validation to return wrong counts
        conv_collection = mock_weaviate_client.collections.get("Conversation")
        msg_collection = mock_weaviate_client.collections.get("Message")

        # Return fewer objects than expected
        conv_collection.query.fetch_objects.return_value = Mock(objects=[Mock(), Mock()])  # 2 instead of 3
        msg_collection.query.fetch_objects.return_value = Mock(objects=[Mock(), Mock(), Mock()])  # 3 instead of 5

        # Run migration
        config = MigrationConfig(
            sqlite_url=temp_sqlite_db,
            weaviate_url="http://localhost:8080",
            batch_size=10
        )

        result = run_migration(config)

        # Should succeed in migration but fail validation
        assert result.success is True  # Migration completed
        assert result.validation_passed is False  # But validation failed
        assert len(result.validation_errors) == 2  # Count mismatches for both tables
        assert "Conversation count mismatch" in result.validation_errors[0]
        assert "Message count mismatch" in result.validation_errors[1]

    def test_uuid_generation(self, temp_sqlite_db):
        """Test UUID generation for records."""
        config = MigrationConfig(
            sqlite_url=temp_sqlite_db,
            weaviate_url="http://localhost:8080"
        )

        migrator = SQLiteToWeaviateMigrator(config)

        # Test valid UUID
        valid_uuid = "550e8400-e29b-41d4-a716-446655440000"
        result_uuid = migrator._generate_uuid(valid_uuid)
        assert result_uuid == valid_uuid

        # Test string ID (should generate deterministic UUID)
        string_id = "conv-1"
        result_uuid_1 = migrator._generate_uuid(string_id)
        result_uuid_2 = migrator._generate_uuid(string_id)
        assert result_uuid_1 == result_uuid_2  # Should be deterministic
        assert len(result_uuid_1) == 36  # Standard UUID length

    def test_migration_result_serialization(self):
        """Test migration result can be serialized to dict."""
        result = MigrationResult(
            success=True,
            started_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            completed_at=datetime(2024, 1, 1, 12, 5, 0, tzinfo=timezone.utc),
            total_records=100,
            migrated_records=95,
            failed_records=5,
            validation_passed=True
        )

        result_dict = result.to_dict()

        assert result_dict["success"] is True
        assert result_dict["total_records"] == 100
        assert result_dict["migrated_records"] == 95
        assert result_dict["failed_records"] == 5
        assert result_dict["validation_passed"] is True
        assert "started_at" in result_dict
        assert "completed_at" in result_dict

    @patch('weaviate.connect_to_local')
    def test_schema_creation_during_migration(self, mock_connect, temp_sqlite_db, mock_weaviate_client):
        """Test that schema is created if it doesn't exist."""
        # Setup mocks
        mock_connect.return_value = mock_weaviate_client

        with patch('app.migrations.sqlite_to_weaviate.WeaviateSchemaManager') as mock_schema_class:
            mock_schema_manager = Mock()

            # Mock schema doesn't exist initially
            mock_schema_manager.get_schema_info.return_value = {
                "Conversation": {"exists": False},
                "Message": {"exists": False}
            }
            mock_schema_manager.create_weaviate_schema.return_value = True
            mock_schema_class.return_value = mock_schema_manager

            # Run migration
            config = MigrationConfig(
                sqlite_url=temp_sqlite_db,
                weaviate_url="http://localhost:8080"
            )

            result = run_migration(config)

            # Verify schema creation was called
            assert result.success is True
            mock_schema_manager.create_weaviate_schema.assert_called_once()

    def test_migration_metrics_calculation(self, temp_sqlite_db):
        """Test migration metrics are calculated correctly."""
        config = MigrationConfig(
            sqlite_url=temp_sqlite_db,
            weaviate_url="http://localhost:8080"
        )

        migrator = SQLiteToWeaviateMigrator(config)

        # Simulate migration timing
        migrator.result.started_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        migrator.result.completed_at = datetime(2024, 1, 1, 12, 0, 10, tzinfo=timezone.utc)  # 10 seconds
        migrator.result.migrated_records = 100

        migrator._calculate_metrics()

        assert migrator.result.duration_seconds == 10.0
        assert migrator.result.records_per_second == 10.0  # 100 records / 10 seconds
