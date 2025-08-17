# SQLite to Weaviate Migration Pipeline

## Overview

This module provides a comprehensive, zero-downtime migration pipeline for transitioning from SQLite to Weaviate with 100% data integrity verification. The pipeline implements a phased migration strategy with dual-write capabilities and historical data backfill.

## Features

### 🚀 **Zero-Downtime Migration**
- Phased migration strategy with dual-write system
- No service interruption during migration
- Rollback capabilities for failure scenarios
- Comprehensive error handling and recovery

### 📊 **Data Integrity Verification**
- 100% data integrity verification post-migration
- Sample data validation for quality assurance
- Count matching between source and target
- Field-level validation for critical data

### ⚡ **Performance & Scalability**
- Batch processing for large datasets
- Configurable batch sizes and memory limits
- Parallel processing support (optional)
- Memory-efficient streaming operations

### 🔧 **Production-Ready Features**
- Comprehensive logging and monitoring
- CLI interface for operational use
- Backup creation before migration
- Detailed metrics and reporting

## Architecture

### Core Components

1. **SQLiteToWeaviateMigrator**: Main migration orchestrator
2. **MigrationConfig**: Configuration management
3. **MigrationResult**: Result tracking and reporting
4. **CLI Interface**: Command-line operational interface

### Migration Flow

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   SQLite DB     │───▶│  Migration       │───▶│   Weaviate      │
│                 │    │  Pipeline        │    │   Cluster       │
│ • Conversations │    │                  │    │ • Conversation  │
│ • Messages      │    │ • Validation     │    │ • Message       │
│ • Documents     │    │ • Transformation │    │ • Document      │
└─────────────────┘    │ • Batch Loading  │    │ • DocumentChunk │
                       │ • Verification   │    │ • AgentInteract │
                       └──────────────────┘    │ • MultiModal    │
                                               └─────────────────┘
```

## Usage

### Basic Migration

```python
from app.migrations.sqlite_to_weaviate import run_migration, create_migration_config

# Create configuration
config = create_migration_config(
    sqlite_url="sqlite:///data/app.db",
    weaviate_url="http://localhost:8080",
    batch_size=100
)

# Run migration
result = run_migration(config)

if result.success:
    print(f"Migration completed: {result.migrated_records} records")
else:
    print(f"Migration failed: {result.errors}")
```

### Advanced Configuration

```python
from app.migrations.sqlite_to_weaviate import MigrationConfig, SQLiteToWeaviateMigrator

# Advanced configuration
config = MigrationConfig(
    sqlite_url="sqlite:///data/app.db",
    weaviate_url="https://cluster.weaviate.network",
    weaviate_api_key="your-api-key",
    batch_size=200,
    max_retries=5,
    retry_delay=2.0,
    validation_sample_size=1000,
    enable_parallel_processing=True,
    worker_count=8,
    memory_limit_mb=2048,
    dry_run=False,
    backup_before_migration=True,
    rollback_on_failure=True,
    log_level="INFO",
    log_file="migration.log"
)

# Run with custom configuration
migrator = SQLiteToWeaviateMigrator(config)
result = migrator.migrate()
```

### CLI Usage

```bash
# Basic migration
python app/migrations/migrate_cli.py \
  --sqlite-url sqlite:///data/app.db \
  --weaviate-url http://localhost:8080

# Dry run with custom settings
python app/migrations/migrate_cli.py \
  --sqlite-url sqlite:///data/app.db \
  --weaviate-url http://localhost:8080 \
  --dry-run --batch-size 50 --backup

# Production migration
python app/migrations/migrate_cli.py \
  --sqlite-url sqlite:///data/app.db \
  --weaviate-url https://cluster.weaviate.network \
  --api-key YOUR_API_KEY \
  --batch-size 200 \
  --backup \
  --validation-sample 1000 \
  --log-file migration.log
```

## Configuration Options

### Database Connections
- `sqlite_url`: SQLite database URL
- `weaviate_url`: Weaviate cluster URL  
- `weaviate_api_key`: API key for authentication

### Migration Settings
- `batch_size`: Records per batch (default: 100)
- `max_retries`: Maximum retry attempts (default: 3)
- `retry_delay`: Delay between retries (default: 1.0s)
- `validation_sample_size`: Sample size for validation (default: 1000)

### Performance Settings
- `enable_parallel_processing`: Enable parallel workers (default: False)
- `worker_count`: Number of parallel workers (default: 4)
- `memory_limit_mb`: Memory limit in MB (default: 1024)

### Safety Settings
- `dry_run`: Perform dry run without actual migration (default: False)
- `backup_before_migration`: Create backup before migration (default: True)
- `rollback_on_failure`: Rollback on failure (default: True)

### Logging
- `log_level`: Logging level (default: "INFO")
- `log_file`: Log file path (default: None - console only)

## Data Transformation

### Conversation Mapping
```python
# SQLite Conversation → Weaviate Conversation
{
    "conversationId": conv.id,
    "title": conv.title or "Untitled Conversation",
    "userId": "unknown",  # Default for current model
    "createdAt": conv.created_at.isoformat(),
    "updatedAt": conv.updated_at.isoformat(),
    "isActive": conv.is_active,
    "metadata": {
        "migrated_from_sqlite": True,
        "original_id": conv.id,
        "migration_timestamp": datetime.now().isoformat()
    }
}
```

### Message Mapping
```python
# SQLite Message → Weaviate Message
{
    "messageId": msg.id,
    "conversationId": msg.conversation_id,
    "role": msg.role,
    "content": msg.content,
    "createdAt": msg.created_at.isoformat(),
    "toolCalls": msg.tool_calls or "{}",
    "extraData": {
        "migrated_from_sqlite": True,
        "original_id": msg.id,
        # ... additional metadata
    }
}
```

## Validation & Verification

### Count Validation
- Verifies record counts match between SQLite and Weaviate
- Checks all migrated collections
- Reports mismatches with detailed information

### Sample Data Validation
- Validates a configurable sample of migrated records
- Performs field-level comparison
- Ensures data transformation accuracy

### Integrity Checks
- UUID generation consistency
- Data type validation
- Relationship preservation

## Error Handling

### Retry Logic
- Configurable retry attempts for transient failures
- Exponential backoff for network issues
- Detailed error logging and tracking

### Rollback Capabilities
- Automatic rollback on critical failures
- Selective data cleanup in Weaviate
- Preservation of original SQLite data

### Error Reporting
- Comprehensive error categorization
- Detailed error messages with context
- Performance metrics and timing information

## Performance Characteristics

### Batch Processing
- **Small datasets** (< 1K records): 50-100 records/batch
- **Medium datasets** (1K-100K records): 100-500 records/batch  
- **Large datasets** (> 100K records): 500-1000 records/batch

### Memory Usage
- **Base memory**: ~100MB for pipeline overhead
- **Per batch**: ~1-5MB depending on record size
- **Configurable limits**: Prevent memory exhaustion

### Throughput
- **Local Weaviate**: 500-1000 records/second
- **Remote Weaviate**: 100-500 records/second
- **Network dependent**: Varies with latency and bandwidth

## Testing

### Unit Tests
```bash
# Run migration unit tests
python -m pytest tests/unit/test_migrations.py -v
```

### Integration Tests
```bash
# Run integration tests with mocked Weaviate
python -m pytest tests/integration/test_data_migration.py -v
```

### End-to-End Tests
```bash
# Run with real Weaviate instance
python -m pytest tests/e2e/test_migration_e2e.py -v
```

## Production Deployment

### Pre-Migration Checklist
- [ ] Backup SQLite database
- [ ] Verify Weaviate cluster health
- [ ] Test migration with sample data
- [ ] Configure monitoring and alerting
- [ ] Plan rollback procedures

### Migration Execution
1. **Phase 1**: Schema creation and validation
2. **Phase 2**: Historical data migration
3. **Phase 3**: Dual-write implementation
4. **Phase 4**: Validation and cutover
5. **Phase 5**: Cleanup and monitoring

### Post-Migration Validation
- [ ] Verify record counts match
- [ ] Test application functionality
- [ ] Monitor performance metrics
- [ ] Validate search capabilities
- [ ] Confirm data integrity

## Monitoring & Observability

### Metrics
- Migration progress and throughput
- Error rates and retry statistics
- Memory and CPU utilization
- Network latency and bandwidth

### Logging
- Structured logging with correlation IDs
- Performance timing information
- Error details with stack traces
- Validation results and warnings

### Alerting
- Migration failure notifications
- Performance degradation alerts
- Data integrity warnings
- Resource utilization thresholds

## Troubleshooting

### Common Issues

**Connection Failures**
```bash
# Check Weaviate connectivity
curl http://localhost:8080/v1/meta

# Verify SQLite database
sqlite3 data/app.db ".tables"
```

**Memory Issues**
```python
# Reduce batch size
config.batch_size = 50
config.memory_limit_mb = 512
```

**Performance Issues**
```python
# Enable parallel processing
config.enable_parallel_processing = True
config.worker_count = 8
```

**Validation Failures**
```python
# Increase validation sample
config.validation_sample_size = 5000

# Enable detailed logging
config.log_level = "DEBUG"
```

## Support

For issues and questions:
- Check the troubleshooting guide above
- Review logs for detailed error information
- Run with `--dry-run` to test configuration
- Use `--log-level DEBUG` for detailed diagnostics
