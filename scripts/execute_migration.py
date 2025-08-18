#!/usr/bin/env python3
"""
GremlinsAI SQLite to Weaviate Migration Execution Script
Phase 2, Task 2.2: SQLite to Weaviate Migration Execution

This script orchestrates the complete migration from SQLite to Weaviate with:
- Zero data loss validation
- Dual-write system for seamless transition
- Automated rollback capabilities
- Performance validation
- Less than 1 hour planned downtime

Usage:
    python scripts/execute_migration.py --step=migrate-data
    python scripts/execute_migration.py --step=enable-dual-write
    python scripts/execute_migration.py --step=validate
    python scripts/execute_migration.py --step=switch-reads
    python scripts/execute_migration.py --step=rollback
"""

import os
import sys
import json
import time
import argparse
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'app'))

try:
    import requests
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    import weaviate
    from app.database.models import Conversation, Message, Document, DocumentChunk
    from app.database.migration_utils import WeaviateMigrationManager
    from app.migrations.sqlite_to_weaviate import SQLiteToWeaviateMigrator, MigrationConfig
    from app.core.config import get_settings
    from app.database.database import AsyncSessionLocal, SessionLocal
    from app.services.chat_history import ChatHistoryService
    from app.services.document_service import DocumentService
except ImportError as e:
    print(f"Error: Required packages not installed: {e}")
    print("Please ensure all dependencies are installed")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('migration_execution.log')
    ]
)
logger = logging.getLogger(__name__)

# Migration configuration
MIGRATION_CONFIG = {
    "batch_size": 100,
    "validation_sample_size": 1000,
    "max_downtime_minutes": 60,
    "rollback_timeout_minutes": 15,
    "performance_threshold_ms": 100,
    "data_integrity_threshold": 100.0  # 100% data integrity required
}


class MigrationOrchestrator:
    """Orchestrates the complete SQLite to Weaviate migration process."""
    
    def __init__(self):
        """Initialize the migration orchestrator."""
        self.settings = get_settings()
        self.migration_state = {}
        self.start_time = None
        self.weaviate_client = None
        self.sqlite_session = None
        
        # Migration tracking
        self.migration_id = f"migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.state_file = f"migration_state_{self.migration_id}.json"
        self.validation_report_file = f"migration_validation_report_{self.migration_id}.json"
        
        logger.info(f"Initialized migration orchestrator: {self.migration_id}")
    
    def setup_connections(self) -> bool:
        """Setup database connections."""
        try:
            logger.info("Setting up database connections...")
            
            # Setup SQLite connection
            sqlite_engine = create_engine(self.settings.get_database_url())
            SQLiteSession = sessionmaker(bind=sqlite_engine)
            self.sqlite_session = SQLiteSession()
            
            # Test SQLite connection
            result = self.sqlite_session.execute(text("SELECT COUNT(*) FROM conversations")).scalar()
            logger.info(f"SQLite connection established. Found {result} conversations.")
            
            # Setup Weaviate connection
            headers = {}
            if self.settings.weaviate_api_key:
                headers['Authorization'] = f'Bearer {self.settings.weaviate_api_key}'
            
            # Test Weaviate connection
            response = requests.get(f"{self.settings.weaviate_url}/v1/.well-known/ready", 
                                  headers=headers, timeout=10)
            
            if response.status_code == 200 and response.json().get('ready', False):
                logger.info("Weaviate connection established")
                self.weaviate_headers = headers
                return True
            else:
                logger.error(f"Weaviate not ready: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to setup connections: {e}")
            return False
    
    def save_migration_state(self, step: str, status: str, data: Dict[str, Any] = None):
        """Save migration state to file."""
        self.migration_state.update({
            "migration_id": self.migration_id,
            "current_step": step,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "data": data or {}
        })
        
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.migration_state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save migration state: {e}")
    
    def load_migration_state(self) -> Dict[str, Any]:
        """Load migration state from file."""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load migration state: {e}")
        return {}
    
    def execute_data_migration(self) -> bool:
        """Execute the core data migration from SQLite to Weaviate."""
        logger.info("Starting data migration phase...")
        self.start_time = time.time()
        
        try:
            self.save_migration_state("migrate-data", "in_progress", {
                "started_at": datetime.now().isoformat()
            })
            
            # Create migration configuration
            config = MigrationConfig(
                sqlite_url=self.settings.get_database_url(),
                weaviate_url=self.settings.weaviate_url,
                weaviate_api_key=self.settings.weaviate_api_key,
                batch_size=MIGRATION_CONFIG["batch_size"],
                validation_sample_size=MIGRATION_CONFIG["validation_sample_size"],
                dry_run=False,
                backup_before_migration=True,
                rollback_on_failure=True
            )
            
            # Execute migration using existing tools
            migrator = SQLiteToWeaviateMigrator(config)
            result = migrator.migrate()
            
            migration_time = time.time() - self.start_time
            
            if result.success:
                logger.info(f"Data migration completed successfully in {migration_time:.2f} seconds")
                self.save_migration_state("migrate-data", "completed", {
                    "migration_time_seconds": migration_time,
                    "conversations_migrated": result.conversations_migrated,
                    "messages_migrated": result.messages_migrated,
                    "documents_migrated": result.documents_migrated,
                    "total_records": result.total_records_migrated
                })
                return True
            else:
                logger.error(f"Data migration failed: {result.error_message}")
                self.save_migration_state("migrate-data", "failed", {
                    "error": result.error_message,
                    "migration_time_seconds": migration_time
                })
                return False
                
        except Exception as e:
            migration_time = time.time() - self.start_time if self.start_time else 0
            logger.error(f"Data migration failed with exception: {e}")
            self.save_migration_state("migrate-data", "failed", {
                "error": str(e),
                "migration_time_seconds": migration_time
            })
            return False
    
    def enable_dual_write_system(self) -> bool:
        """Enable dual-write system for seamless transition."""
        logger.info("Enabling dual-write system...")
        
        try:
            self.save_migration_state("enable-dual-write", "in_progress")
            
            # Update configuration to enable dual-write
            config_updates = {
                "DUAL_WRITE_ENABLED": "true",
                "MIGRATION_MODE": "dual_write",
                "WEAVIATE_PRIMARY": "false"  # Still reading from SQLite
            }
            
            # Write configuration updates to environment file
            env_file = ".env"
            if os.path.exists(env_file):
                with open(env_file, 'r') as f:
                    lines = f.readlines()
                
                # Update existing lines or add new ones
                updated_lines = []
                updated_keys = set()
                
                for line in lines:
                    if '=' in line and not line.strip().startswith('#'):
                        key = line.split('=')[0].strip()
                        if key in config_updates:
                            updated_lines.append(f"{key}={config_updates[key]}\n")
                            updated_keys.add(key)
                        else:
                            updated_lines.append(line)
                    else:
                        updated_lines.append(line)
                
                # Add new configuration keys
                for key, value in config_updates.items():
                    if key not in updated_keys:
                        updated_lines.append(f"{key}={value}\n")
                
                # Write updated configuration
                with open(env_file, 'w') as f:
                    f.writelines(updated_lines)
                
                logger.info("Dual-write system enabled in configuration")
                self.save_migration_state("enable-dual-write", "completed", config_updates)
                return True
            else:
                logger.error("Environment file not found")
                return False
                
        except Exception as e:
            logger.error(f"Failed to enable dual-write system: {e}")
            self.save_migration_state("enable-dual-write", "failed", {"error": str(e)})
            return False
    
    def validate_migration(self) -> bool:
        """Validate migration with comprehensive data integrity checks."""
        logger.info("Starting migration validation...")
        
        try:
            self.save_migration_state("validate", "in_progress")
            
            validation_results = {
                "started_at": datetime.now().isoformat(),
                "data_integrity": {},
                "performance_tests": {},
                "sample_validation": {},
                "overall_success": False
            }
            
            # 1. Data integrity validation
            logger.info("Validating data integrity...")
            integrity_results = self._validate_data_integrity()
            validation_results["data_integrity"] = integrity_results
            
            # 2. Performance validation
            logger.info("Validating query performance...")
            performance_results = self._validate_performance()
            validation_results["performance_tests"] = performance_results
            
            # 3. Sample data validation
            logger.info("Validating sample data...")
            sample_results = self._validate_sample_data()
            validation_results["sample_validation"] = sample_results
            
            # Calculate overall success
            data_integrity_passed = integrity_results.get("integrity_percentage", 0) >= MIGRATION_CONFIG["data_integrity_threshold"]
            performance_passed = performance_results.get("average_query_time_ms", float('inf')) <= MIGRATION_CONFIG["performance_threshold_ms"]
            sample_passed = sample_results.get("sample_match_percentage", 0) >= 95.0
            
            overall_success = data_integrity_passed and performance_passed and sample_passed
            validation_results["overall_success"] = overall_success
            validation_results["completed_at"] = datetime.now().isoformat()
            
            # Save validation report
            with open(self.validation_report_file, 'w') as f:
                json.dump(validation_results, f, indent=2)
            
            if overall_success:
                logger.info("Migration validation passed all tests")
                self.save_migration_state("validate", "completed", validation_results)
                return True
            else:
                logger.error("Migration validation failed")
                self.save_migration_state("validate", "failed", validation_results)
                return False
                
        except Exception as e:
            logger.error(f"Migration validation failed: {e}")
            self.save_migration_state("validate", "failed", {"error": str(e)})
            return False
    
    def switch_to_weaviate_reads(self) -> bool:
        """Switch read operations to Weaviate."""
        logger.info("Switching read operations to Weaviate...")
        
        try:
            self.save_migration_state("switch-reads", "in_progress")
            
            # Update configuration to use Weaviate for reads
            config_updates = {
                "WEAVIATE_PRIMARY": "true",
                "MIGRATION_MODE": "weaviate_primary"
            }
            
            # Update environment file
            env_file = ".env"
            if os.path.exists(env_file):
                with open(env_file, 'r') as f:
                    lines = f.readlines()
                
                updated_lines = []
                for line in lines:
                    if '=' in line and not line.strip().startswith('#'):
                        key = line.split('=')[0].strip()
                        if key in config_updates:
                            updated_lines.append(f"{key}={config_updates[key]}\n")
                        else:
                            updated_lines.append(line)
                    else:
                        updated_lines.append(line)
                
                with open(env_file, 'w') as f:
                    f.writelines(updated_lines)
                
                logger.info("Switched to Weaviate for read operations")
                self.save_migration_state("switch-reads", "completed", config_updates)
                return True
            else:
                logger.error("Environment file not found")
                return False
                
        except Exception as e:
            logger.error(f"Failed to switch reads to Weaviate: {e}")
            self.save_migration_state("switch-reads", "failed", {"error": str(e)})
            return False
    
    def execute_rollback(self) -> bool:
        """Execute rollback to SQLite-only operation."""
        logger.info("Executing rollback to SQLite...")
        rollback_start = time.time()
        
        try:
            self.save_migration_state("rollback", "in_progress")
            
            # Disable dual-write and switch back to SQLite
            config_updates = {
                "DUAL_WRITE_ENABLED": "false",
                "WEAVIATE_PRIMARY": "false",
                "MIGRATION_MODE": "sqlite_only"
            }
            
            # Update environment file
            env_file = ".env"
            if os.path.exists(env_file):
                with open(env_file, 'r') as f:
                    lines = f.readlines()
                
                updated_lines = []
                for line in lines:
                    if '=' in line and not line.strip().startswith('#'):
                        key = line.split('=')[0].strip()
                        if key in config_updates:
                            updated_lines.append(f"{key}={config_updates[key]}\n")
                        else:
                            updated_lines.append(line)
                    else:
                        updated_lines.append(line)
                
                with open(env_file, 'w') as f:
                    f.writelines(updated_lines)
                
                rollback_time = time.time() - rollback_start
                
                if rollback_time <= MIGRATION_CONFIG["rollback_timeout_minutes"] * 60:
                    logger.info(f"Rollback completed successfully in {rollback_time:.2f} seconds")
                    self.save_migration_state("rollback", "completed", {
                        "rollback_time_seconds": rollback_time,
                        "config_updates": config_updates
                    })
                    return True
                else:
                    logger.error(f"Rollback exceeded timeout: {rollback_time:.2f} seconds")
                    return False
            else:
                logger.error("Environment file not found")
                return False
                
        except Exception as e:
            rollback_time = time.time() - rollback_start
            logger.error(f"Rollback failed: {e}")
            self.save_migration_state("rollback", "failed", {
                "error": str(e),
                "rollback_time_seconds": rollback_time
            })
            return False
    
    def _validate_data_integrity(self) -> Dict[str, Any]:
        """Validate data integrity between SQLite and Weaviate."""
        try:
            # Count records in SQLite
            sqlite_conversations = self.sqlite_session.execute(text("SELECT COUNT(*) FROM conversations")).scalar()
            sqlite_messages = self.sqlite_session.execute(text("SELECT COUNT(*) FROM messages")).scalar()
            
            # Count records in Weaviate
            weaviate_conversations = self._count_weaviate_objects("Conversation")
            weaviate_messages = self._count_weaviate_objects("Message")
            
            # Calculate integrity percentage
            total_sqlite = sqlite_conversations + sqlite_messages
            total_weaviate = weaviate_conversations + weaviate_messages
            
            integrity_percentage = (total_weaviate / total_sqlite * 100) if total_sqlite > 0 else 0
            
            return {
                "sqlite_counts": {
                    "conversations": sqlite_conversations,
                    "messages": sqlite_messages,
                    "total": total_sqlite
                },
                "weaviate_counts": {
                    "conversations": weaviate_conversations,
                    "messages": weaviate_messages,
                    "total": total_weaviate
                },
                "integrity_percentage": integrity_percentage,
                "integrity_passed": integrity_percentage >= MIGRATION_CONFIG["data_integrity_threshold"]
            }
            
        except Exception as e:
            logger.error(f"Data integrity validation failed: {e}")
            return {"error": str(e), "integrity_passed": False}
    
    def _validate_performance(self) -> Dict[str, Any]:
        """Validate query performance in Weaviate."""
        try:
            query_times = []
            
            # Test multiple queries
            test_queries = [
                "test conversation",
                "user message",
                "system response",
                "document content",
                "search query"
            ]
            
            for query in test_queries:
                start_time = time.time()
                
                # Execute semantic search query
                response = requests.post(
                    f"{self.settings.weaviate_url}/v1/graphql",
                    headers={**self.weaviate_headers, 'Content-Type': 'application/json'},
                    json={
                        "query": f"""
                        {{
                            Get {{
                                Conversation(limit: 10, nearText: {{concepts: ["{query}"]}}) {{
                                    title
                                    summary
                                }}
                            }}
                        }}
                        """
                    },
                    timeout=5
                )
                
                query_time = (time.time() - start_time) * 1000
                query_times.append(query_time)
            
            avg_query_time = sum(query_times) / len(query_times)
            max_query_time = max(query_times)
            min_query_time = min(query_times)
            
            return {
                "average_query_time_ms": avg_query_time,
                "max_query_time_ms": max_query_time,
                "min_query_time_ms": min_query_time,
                "total_queries": len(query_times),
                "performance_passed": avg_query_time <= MIGRATION_CONFIG["performance_threshold_ms"]
            }
            
        except Exception as e:
            logger.error(f"Performance validation failed: {e}")
            return {"error": str(e), "performance_passed": False}
    
    def _validate_sample_data(self) -> Dict[str, Any]:
        """Validate sample data matches between SQLite and Weaviate."""
        try:
            # Get sample conversations from SQLite
            sample_conversations = self.sqlite_session.execute(
                text("SELECT id, title, summary FROM conversations LIMIT 10")
            ).fetchall()
            
            matches = 0
            total_samples = len(sample_conversations)
            
            for conv in sample_conversations:
                # Check if conversation exists in Weaviate
                response = requests.post(
                    f"{self.settings.weaviate_url}/v1/graphql",
                    headers={**self.weaviate_headers, 'Content-Type': 'application/json'},
                    json={
                        "query": f"""
                        {{
                            Get {{
                                Conversation(where: {{path: ["title"], operator: Equal, valueText: "{conv.title}"}}) {{
                                    title
                                    summary
                                }}
                            }}
                        }}
                        """
                    },
                    timeout=5
                )
                
                if response.status_code == 200:
                    data = response.json()
                    conversations = data.get('data', {}).get('Get', {}).get('Conversation', [])
                    if conversations:
                        matches += 1
            
            match_percentage = (matches / total_samples * 100) if total_samples > 0 else 0
            
            return {
                "total_samples": total_samples,
                "matches": matches,
                "sample_match_percentage": match_percentage,
                "sample_passed": match_percentage >= 95.0
            }
            
        except Exception as e:
            logger.error(f"Sample validation failed: {e}")
            return {"error": str(e), "sample_passed": False}
    
    def _count_weaviate_objects(self, class_name: str) -> int:
        """Count objects in a Weaviate class."""
        try:
            response = requests.post(
                f"{self.settings.weaviate_url}/v1/graphql",
                headers={**self.weaviate_headers, 'Content-Type': 'application/json'},
                json={
                    "query": f"""
                    {{
                        Aggregate {{
                            {class_name} {{
                                meta {{
                                    count
                                }}
                            }}
                        }}
                    }}
                    """
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('data', {}).get('Aggregate', {}).get(class_name, [{}])[0].get('meta', {}).get('count', 0)
            return 0
            
        except Exception as e:
            logger.error(f"Failed to count {class_name} objects: {e}")
            return 0
    
    def cleanup(self):
        """Cleanup resources."""
        if self.sqlite_session:
            self.sqlite_session.close()


def main():
    """Main migration execution function."""
    parser = argparse.ArgumentParser(
        description="Execute SQLite to Weaviate migration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Migration Steps:
  migrate-data      - Execute core data migration
  enable-dual-write - Enable dual-write system
  validate          - Validate migration integrity and performance
  switch-reads      - Switch read operations to Weaviate
  rollback          - Rollback to SQLite-only operation
  
Examples:
  python scripts/execute_migration.py --step=migrate-data
  python scripts/execute_migration.py --step=enable-dual-write
  python scripts/execute_migration.py --step=validate
  python scripts/execute_migration.py --step=switch-reads
  python scripts/execute_migration.py --step=rollback
        """
    )
    
    parser.add_argument(
        "--step",
        required=True,
        choices=["migrate-data", "enable-dual-write", "validate", "switch-reads", "rollback"],
        help="Migration step to execute"
    )
    
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force execution without confirmation"
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("  GremlinsAI SQLite to Weaviate Migration")
    print("  Phase 2, Task 2.2: Migration Execution")
    print("=" * 80)
    print(f"Executing step: {args.step}")
    print()
    
    # Confirmation for destructive operations
    if not args.force and args.step in ["migrate-data", "switch-reads", "rollback"]:
        response = input(f"Are you sure you want to execute '{args.step}'? (y/N): ")
        if not response.lower().startswith('y'):
            print("Operation cancelled by user")
            return
    
    # Initialize orchestrator
    orchestrator = MigrationOrchestrator()
    
    try:
        # Setup connections
        if not orchestrator.setup_connections():
            logger.error("Failed to setup database connections")
            sys.exit(1)
        
        # Execute requested step
        success = False
        
        if args.step == "migrate-data":
            success = orchestrator.execute_data_migration()
        elif args.step == "enable-dual-write":
            success = orchestrator.enable_dual_write_system()
        elif args.step == "validate":
            success = orchestrator.validate_migration()
        elif args.step == "switch-reads":
            success = orchestrator.switch_to_weaviate_reads()
        elif args.step == "rollback":
            success = orchestrator.execute_rollback()
        
        # Report results
        if success:
            print(f"\n✅ Migration step '{args.step}' completed successfully!")
            if args.step == "validate":
                print(f"📊 Validation report saved to: {orchestrator.validation_report_file}")
            print(f"📋 Migration state saved to: {orchestrator.state_file}")
        else:
            print(f"\n❌ Migration step '{args.step}' failed!")
            print(f"📋 Check migration state in: {orchestrator.state_file}")
            sys.exit(1)
    
    finally:
        orchestrator.cleanup()


if __name__ == "__main__":
    main()
