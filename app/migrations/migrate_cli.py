#!/usr/bin/env python3
"""
Command-line interface for SQLite to Weaviate migration.

This script provides a CLI for running the migration pipeline with
various configuration options and monitoring capabilities.
"""

import argparse
import json
import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.migrations.sqlite_to_weaviate import (
    MigrationConfig,
    run_migration,
    create_migration_config
)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Migrate data from SQLite to Weaviate",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic migration
  python migrate_cli.py --sqlite-url sqlite:///data/app.db --weaviate-url http://localhost:8080

  # Dry run with custom batch size
  python migrate_cli.py --sqlite-url sqlite:///data/app.db --weaviate-url http://localhost:8080 --dry-run --batch-size 50

  # Production migration with API key
  python migrate_cli.py --sqlite-url sqlite:///data/app.db --weaviate-url https://cluster.weaviate.network --api-key YOUR_API_KEY --batch-size 200

  # Migration with validation and backup
  python migrate_cli.py --sqlite-url sqlite:///data/app.db --weaviate-url http://localhost:8080 --backup --validation-sample 500
        """
    )
    
    # Required arguments
    parser.add_argument(
        "--sqlite-url",
        required=True,
        help="SQLite database URL (e.g., sqlite:///data/app.db)"
    )
    
    parser.add_argument(
        "--weaviate-url", 
        required=True,
        help="Weaviate cluster URL (e.g., http://localhost:8080)"
    )
    
    # Optional arguments
    parser.add_argument(
        "--api-key",
        help="Weaviate API key for authentication"
    )
    
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Batch size for migration (default: 100)"
    )
    
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum retry attempts (default: 3)"
    )
    
    parser.add_argument(
        "--retry-delay",
        type=float,
        default=1.0,
        help="Delay between retries in seconds (default: 1.0)"
    )
    
    parser.add_argument(
        "--validation-sample",
        type=int,
        default=1000,
        help="Sample size for validation (default: 1000)"
    )
    
    parser.add_argument(
        "--memory-limit",
        type=int,
        default=1024,
        help="Memory limit in MB (default: 1024)"
    )
    
    # Flags
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform dry run without actual data migration"
    )
    
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Create backup before migration"
    )
    
    parser.add_argument(
        "--no-rollback",
        action="store_true",
        help="Disable rollback on failure"
    )
    
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Enable parallel processing"
    )
    
    parser.add_argument(
        "--worker-count",
        type=int,
        default=4,
        help="Number of parallel workers (default: 4)"
    )
    
    # Logging options
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--log-file",
        help="Log file path (default: console only)"
    )
    
    # Output options
    parser.add_argument(
        "--output-format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)"
    )
    
    parser.add_argument(
        "--output-file",
        help="Output file for results (default: stdout)"
    )
    
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress output"
    )
    
    return parser.parse_args()


def validate_arguments(args):
    """Validate command line arguments."""
    errors = []
    
    # Validate SQLite URL
    if not args.sqlite_url.startswith(('sqlite:///', 'sqlite://')):
        errors.append("SQLite URL must start with 'sqlite://' or 'sqlite:///'")
    
    # Validate Weaviate URL
    if not args.weaviate_url.startswith(('http://', 'https://')):
        errors.append("Weaviate URL must start with 'http://' or 'https://'")
    
    # Validate batch size
    if args.batch_size <= 0:
        errors.append("Batch size must be positive")
    
    # Validate worker count
    if args.worker_count <= 0:
        errors.append("Worker count must be positive")
    
    # Validate memory limit
    if args.memory_limit <= 0:
        errors.append("Memory limit must be positive")
    
    # Check if SQLite file exists (for file URLs)
    if args.sqlite_url.startswith('sqlite:///'):
        db_path = args.sqlite_url[10:]  # Remove 'sqlite:///'
        if not os.path.exists(db_path):
            errors.append(f"SQLite database file not found: {db_path}")
    
    if errors:
        print("Validation errors:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)


def create_config_from_args(args):
    """Create migration configuration from arguments."""
    return MigrationConfig(
        sqlite_url=args.sqlite_url,
        weaviate_url=args.weaviate_url,
        weaviate_api_key=args.api_key,
        batch_size=args.batch_size,
        max_retries=args.max_retries,
        retry_delay=args.retry_delay,
        validation_sample_size=args.validation_sample,
        enable_parallel_processing=args.parallel,
        worker_count=args.worker_count,
        memory_limit_mb=args.memory_limit,
        dry_run=args.dry_run,
        backup_before_migration=args.backup,
        rollback_on_failure=not args.no_rollback,
        log_level=args.log_level,
        log_file=args.log_file
    )


def format_output(result, format_type="text"):
    """Format migration result for output."""
    if format_type == "json":
        return json.dumps(result.to_dict(), indent=2)
    
    # Text format
    lines = []
    lines.append("=" * 60)
    lines.append("MIGRATION RESULT")
    lines.append("=" * 60)
    
    # Status
    status = "SUCCESS" if result.success else "FAILED"
    lines.append(f"Status: {status}")
    lines.append("")
    
    # Timing
    lines.append("Timing:")
    lines.append(f"  Started:   {result.started_at}")
    lines.append(f"  Completed: {result.completed_at}")
    lines.append(f"  Duration:  {result.duration_seconds:.2f} seconds")
    lines.append("")
    
    # Statistics
    lines.append("Statistics:")
    lines.append(f"  Total records:    {result.total_records}")
    lines.append(f"  Migrated:         {result.migrated_records}")
    lines.append(f"  Failed:           {result.failed_records}")
    lines.append(f"  Skipped:          {result.skipped_records}")
    lines.append(f"  Rate:             {result.records_per_second:.2f} records/second")
    lines.append("")
    
    # Validation
    validation_status = "PASSED" if result.validation_passed else "FAILED"
    lines.append(f"Validation: {validation_status}")
    
    if result.validation_errors:
        lines.append("Validation Errors:")
        for error in result.validation_errors:
            lines.append(f"  - {error}")
        lines.append("")
    
    # Errors
    if result.errors:
        lines.append("Errors:")
        for error in result.errors:
            lines.append(f"  - {error.get('type', 'Unknown')}: {error.get('message', 'No message')}")
        lines.append("")
    
    # Warnings
    if result.warnings:
        lines.append("Warnings:")
        for warning in result.warnings:
            lines.append(f"  - {warning}")
        lines.append("")
    
    lines.append("=" * 60)
    
    return "\n".join(lines)


def main():
    """Main CLI function."""
    try:
        # Parse and validate arguments
        args = parse_arguments()
        validate_arguments(args)
        
        if not args.quiet:
            print("Starting SQLite to Weaviate migration...")
            print(f"Source: {args.sqlite_url}")
            print(f"Target: {args.weaviate_url}")
            print(f"Batch size: {args.batch_size}")
            print(f"Dry run: {args.dry_run}")
            print()
        
        # Create configuration
        config = create_config_from_args(args)
        
        # Run migration
        result = run_migration(config)
        
        # Format and output results
        output = format_output(result, args.output_format)
        
        if args.output_file:
            with open(args.output_file, 'w') as f:
                f.write(output)
            if not args.quiet:
                print(f"Results written to: {args.output_file}")
        else:
            print(output)
        
        # Exit with appropriate code
        sys.exit(0 if result.success else 1)
        
    except KeyboardInterrupt:
        print("\nMigration interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"Migration failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
