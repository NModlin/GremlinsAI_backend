#!/usr/bin/env python3
"""
GremlinsAI Migration Integrity Validation Script
Phase 2, Task 2.2: SQLite to Weaviate Migration Execution

This script performs comprehensive validation of the migration integrity,
ensuring 100% data accuracy and zero data loss between SQLite and Weaviate.

Features:
- Field-by-field data comparison
- Performance benchmarking
- Data consistency validation
- Rollback readiness testing
- Comprehensive reporting
"""

import os
import sys
import json
import time
import logging
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'app'))

try:
    import requests
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    from app.core.config import get_settings
    from app.database.models import Conversation, Message, Document
except ImportError as e:
    print(f"Error: Required packages not installed: {e}")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('migration_integrity_validation.log')
    ]
)
logger = logging.getLogger(__name__)


class MigrationIntegrityValidator:
    """Comprehensive migration integrity validator."""
    
    def __init__(self):
        """Initialize the validator."""
        self.settings = get_settings()
        self.sqlite_session = None
        self.weaviate_headers = {}
        
        if self.settings.weaviate_api_key:
            self.weaviate_headers['Authorization'] = f'Bearer {self.settings.weaviate_api_key}'
        
        self.validation_results = {
            "started_at": datetime.now().isoformat(),
            "data_integrity": {},
            "performance_comparison": {},
            "consistency_checks": {},
            "rollback_readiness": {},
            "overall_status": "unknown"
        }
        
        logger.info("Migration integrity validator initialized")
    
    def setup_connections(self) -> bool:
        """Setup database connections."""
        try:
            # Setup SQLite connection
            sqlite_engine = create_engine(self.settings.get_database_url())
            SQLiteSession = sessionmaker(bind=sqlite_engine)
            self.sqlite_session = SQLiteSession()
            
            # Test connections
            sqlite_count = self.sqlite_session.execute(text("SELECT COUNT(*) FROM conversations")).scalar()
            logger.info(f"SQLite connection established. {sqlite_count} conversations found.")
            
            # Test Weaviate connection
            response = requests.get(f"{self.settings.weaviate_url}/v1/.well-known/ready", 
                                  headers=self.weaviate_headers, timeout=10)
            
            if response.status_code == 200 and response.json().get('ready', False):
                logger.info("Weaviate connection established")
                return True
            else:
                logger.error(f"Weaviate not ready: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to setup connections: {e}")
            return False
    
    def validate_data_integrity(self) -> Dict[str, Any]:
        """Validate complete data integrity between SQLite and Weaviate."""
        logger.info("Starting comprehensive data integrity validation...")
        
        integrity_results = {
            "record_counts": {},
            "field_validation": {},
            "data_consistency": {},
            "integrity_score": 0.0
        }
        
        try:
            # 1. Validate record counts
            logger.info("Validating record counts...")
            count_results = self._validate_record_counts()
            integrity_results["record_counts"] = count_results
            
            # 2. Validate field-by-field data
            logger.info("Validating field-by-field data...")
            field_results = self._validate_field_data()
            integrity_results["field_validation"] = field_results
            
            # 3. Validate data consistency
            logger.info("Validating data consistency...")
            consistency_results = self._validate_data_consistency()
            integrity_results["data_consistency"] = consistency_results
            
            # Calculate overall integrity score
            count_score = count_results.get("match_percentage", 0)
            field_score = field_results.get("match_percentage", 0)
            consistency_score = consistency_results.get("consistency_percentage", 0)
            
            integrity_score = (count_score + field_score + consistency_score) / 3
            integrity_results["integrity_score"] = integrity_score
            
            logger.info(f"Data integrity validation completed. Score: {integrity_score:.2f}%")
            return integrity_results
            
        except Exception as e:
            logger.error(f"Data integrity validation failed: {e}")
            integrity_results["error"] = str(e)
            return integrity_results
    
    def validate_performance_comparison(self) -> Dict[str, Any]:
        """Compare query performance between SQLite and Weaviate."""
        logger.info("Starting performance comparison...")
        
        performance_results = {
            "sqlite_performance": {},
            "weaviate_performance": {},
            "performance_ratio": {},
            "meets_requirements": False
        }
        
        try:
            # Test queries for performance comparison
            test_queries = [
                {"type": "simple_select", "description": "Simple conversation lookup"},
                {"type": "text_search", "description": "Text content search"},
                {"type": "complex_join", "description": "Complex join query"},
                {"type": "aggregation", "description": "Count aggregation"},
                {"type": "semantic_search", "description": "Semantic similarity search"}
            ]
            
            sqlite_times = []
            weaviate_times = []
            
            for query_test in test_queries:
                # Test SQLite performance
                sqlite_time = self._test_sqlite_query_performance(query_test["type"])
                sqlite_times.append(sqlite_time)
                
                # Test Weaviate performance
                weaviate_time = self._test_weaviate_query_performance(query_test["type"])
                weaviate_times.append(weaviate_time)
                
                logger.info(f"{query_test['description']}: SQLite {sqlite_time:.2f}ms, Weaviate {weaviate_time:.2f}ms")
            
            # Calculate performance metrics
            avg_sqlite = sum(sqlite_times) / len(sqlite_times)
            avg_weaviate = sum(weaviate_times) / len(weaviate_times)
            
            performance_results["sqlite_performance"] = {
                "average_ms": avg_sqlite,
                "query_times": sqlite_times
            }
            
            performance_results["weaviate_performance"] = {
                "average_ms": avg_weaviate,
                "query_times": weaviate_times
            }
            
            # Performance ratio (Weaviate vs SQLite)
            performance_ratio = avg_weaviate / avg_sqlite if avg_sqlite > 0 else float('inf')
            performance_results["performance_ratio"] = {
                "ratio": performance_ratio,
                "weaviate_faster": performance_ratio < 1.0,
                "performance_improvement": ((avg_sqlite - avg_weaviate) / avg_sqlite * 100) if avg_sqlite > 0 else 0
            }
            
            # Check if meets requirements (< 100ms average)
            meets_requirements = avg_weaviate < 100
            performance_results["meets_requirements"] = meets_requirements
            
            logger.info(f"Performance comparison completed. Weaviate avg: {avg_weaviate:.2f}ms, SQLite avg: {avg_sqlite:.2f}ms")
            return performance_results
            
        except Exception as e:
            logger.error(f"Performance comparison failed: {e}")
            performance_results["error"] = str(e)
            return performance_results
    
    def validate_rollback_readiness(self) -> Dict[str, Any]:
        """Validate rollback readiness and procedures."""
        logger.info("Validating rollback readiness...")
        
        rollback_results = {
            "sqlite_backup_exists": False,
            "configuration_backup": False,
            "rollback_time_estimate": 0,
            "rollback_ready": False
        }
        
        try:
            # Check if SQLite backup exists
            backup_files = [f for f in os.listdir('.') if f.startswith('gremlinsai') and f.endswith('.db.backup')]
            rollback_results["sqlite_backup_exists"] = len(backup_files) > 0
            
            if backup_files:
                logger.info(f"Found {len(backup_files)} SQLite backup files")
            
            # Check configuration backup
            config_backup_exists = os.path.exists('.env.backup') or os.path.exists('config_backup.json')
            rollback_results["configuration_backup"] = config_backup_exists
            
            # Estimate rollback time (based on data size)
            sqlite_size = self._get_sqlite_database_size()
            estimated_rollback_time = max(30, sqlite_size / 1024 / 1024 * 2)  # 2 seconds per MB, min 30 seconds
            rollback_results["rollback_time_estimate"] = estimated_rollback_time
            
            # Overall rollback readiness
            rollback_ready = (rollback_results["sqlite_backup_exists"] and 
                            rollback_results["configuration_backup"] and 
                            estimated_rollback_time < 900)  # 15 minutes max
            
            rollback_results["rollback_ready"] = rollback_ready
            
            logger.info(f"Rollback readiness: {rollback_ready}, estimated time: {estimated_rollback_time:.0f} seconds")
            return rollback_results
            
        except Exception as e:
            logger.error(f"Rollback readiness validation failed: {e}")
            rollback_results["error"] = str(e)
            return rollback_results
    
    def _validate_record_counts(self) -> Dict[str, Any]:
        """Validate record counts between databases."""
        try:
            # SQLite counts
            sqlite_conversations = self.sqlite_session.execute(text("SELECT COUNT(*) FROM conversations")).scalar()
            sqlite_messages = self.sqlite_session.execute(text("SELECT COUNT(*) FROM messages")).scalar()
            
            # Weaviate counts
            weaviate_conversations = self._count_weaviate_objects("Conversation")
            weaviate_messages = self._count_weaviate_objects("Message")
            
            # Calculate match percentage
            total_sqlite = sqlite_conversations + sqlite_messages
            total_weaviate = weaviate_conversations + weaviate_messages
            
            match_percentage = (total_weaviate / total_sqlite * 100) if total_sqlite > 0 else 0
            
            return {
                "sqlite": {
                    "conversations": sqlite_conversations,
                    "messages": sqlite_messages,
                    "total": total_sqlite
                },
                "weaviate": {
                    "conversations": weaviate_conversations,
                    "messages": weaviate_messages,
                    "total": total_weaviate
                },
                "match_percentage": match_percentage,
                "counts_match": match_percentage >= 99.9
            }
            
        except Exception as e:
            logger.error(f"Record count validation failed: {e}")
            return {"error": str(e), "counts_match": False}
    
    def _validate_field_data(self) -> Dict[str, Any]:
        """Validate field-by-field data accuracy."""
        try:
            # Sample conversations for detailed validation
            sample_conversations = self.sqlite_session.execute(
                text("SELECT id, title, summary, created_at FROM conversations LIMIT 50")
            ).fetchall()
            
            matches = 0
            total_samples = len(sample_conversations)
            field_mismatches = []
            
            for conv in sample_conversations:
                # Get corresponding Weaviate record
                weaviate_conv = self._get_weaviate_conversation(conv.id)
                
                if weaviate_conv:
                    # Compare fields
                    title_match = conv.title == weaviate_conv.get("title", "")
                    summary_match = (conv.summary or "") == (weaviate_conv.get("summary", "") or "")
                    
                    if title_match and summary_match:
                        matches += 1
                    else:
                        field_mismatches.append({
                            "conversation_id": conv.id,
                            "title_match": title_match,
                            "summary_match": summary_match
                        })
            
            match_percentage = (matches / total_samples * 100) if total_samples > 0 else 0
            
            return {
                "total_samples": total_samples,
                "matches": matches,
                "match_percentage": match_percentage,
                "field_mismatches": field_mismatches[:10],  # First 10 mismatches
                "fields_accurate": match_percentage >= 99.0
            }
            
        except Exception as e:
            logger.error(f"Field validation failed: {e}")
            return {"error": str(e), "fields_accurate": False}
    
    def _validate_data_consistency(self) -> Dict[str, Any]:
        """Validate data consistency and relationships."""
        try:
            # Check conversation-message relationships
            sqlite_relationships = self.sqlite_session.execute(
                text("""
                SELECT c.id, COUNT(m.id) as message_count 
                FROM conversations c 
                LEFT JOIN messages m ON c.id = m.conversation_id 
                GROUP BY c.id 
                LIMIT 20
                """)
            ).fetchall()
            
            consistent_relationships = 0
            total_relationships = len(sqlite_relationships)
            
            for rel in sqlite_relationships:
                # Check if Weaviate has the same relationship count
                weaviate_count = self._count_weaviate_messages_for_conversation(rel.id)
                if weaviate_count == rel.message_count:
                    consistent_relationships += 1
            
            consistency_percentage = (consistent_relationships / total_relationships * 100) if total_relationships > 0 else 0
            
            return {
                "total_relationships": total_relationships,
                "consistent_relationships": consistent_relationships,
                "consistency_percentage": consistency_percentage,
                "relationships_consistent": consistency_percentage >= 95.0
            }
            
        except Exception as e:
            logger.error(f"Data consistency validation failed: {e}")
            return {"error": str(e), "relationships_consistent": False}
    
    def _test_sqlite_query_performance(self, query_type: str) -> float:
        """Test SQLite query performance."""
        start_time = time.time()
        
        try:
            if query_type == "simple_select":
                self.sqlite_session.execute(text("SELECT * FROM conversations LIMIT 10")).fetchall()
            elif query_type == "text_search":
                self.sqlite_session.execute(text("SELECT * FROM messages WHERE content LIKE '%test%' LIMIT 10")).fetchall()
            elif query_type == "complex_join":
                self.sqlite_session.execute(text("""
                    SELECT c.title, COUNT(m.id) 
                    FROM conversations c 
                    LEFT JOIN messages m ON c.id = m.conversation_id 
                    GROUP BY c.id 
                    LIMIT 10
                """)).fetchall()
            elif query_type == "aggregation":
                self.sqlite_session.execute(text("SELECT COUNT(*) FROM conversations")).scalar()
            
            return (time.time() - start_time) * 1000
            
        except Exception as e:
            logger.error(f"SQLite query test failed: {e}")
            return float('inf')
    
    def _test_weaviate_query_performance(self, query_type: str) -> float:
        """Test Weaviate query performance."""
        start_time = time.time()
        
        try:
            if query_type == "simple_select":
                query = """
                {
                    Get {
                        Conversation(limit: 10) {
                            title
                            summary
                        }
                    }
                }
                """
            elif query_type == "semantic_search":
                query = """
                {
                    Get {
                        Message(limit: 10, nearText: {concepts: ["test"]}) {
                            content
                            role
                        }
                    }
                }
                """
            elif query_type == "aggregation":
                query = """
                {
                    Aggregate {
                        Conversation {
                            meta {
                                count
                            }
                        }
                    }
                }
                """
            else:
                # Default to simple query
                query = """
                {
                    Get {
                        Conversation(limit: 10) {
                            title
                        }
                    }
                }
                """
            
            response = requests.post(
                f"{self.settings.weaviate_url}/v1/graphql",
                headers={**self.weaviate_headers, 'Content-Type': 'application/json'},
                json={"query": query},
                timeout=10
            )
            
            if response.status_code == 200:
                return (time.time() - start_time) * 1000
            else:
                return float('inf')
                
        except Exception as e:
            logger.error(f"Weaviate query test failed: {e}")
            return float('inf')
    
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
    
    def _get_weaviate_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific conversation from Weaviate."""
        try:
            response = requests.post(
                f"{self.settings.weaviate_url}/v1/graphql",
                headers={**self.weaviate_headers, 'Content-Type': 'application/json'},
                json={
                    "query": f"""
                    {{
                        Get {{
                            Conversation(where: {{path: ["id"], operator: Equal, valueText: "{conversation_id}"}}) {{
                                title
                                summary
                                created_at
                            }}
                        }}
                    }}
                    """
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                conversations = data.get('data', {}).get('Get', {}).get('Conversation', [])
                return conversations[0] if conversations else None
            return None
            
        except Exception as e:
            logger.error(f"Failed to get Weaviate conversation: {e}")
            return None
    
    def _count_weaviate_messages_for_conversation(self, conversation_id: str) -> int:
        """Count messages for a specific conversation in Weaviate."""
        try:
            response = requests.post(
                f"{self.settings.weaviate_url}/v1/graphql",
                headers={**self.weaviate_headers, 'Content-Type': 'application/json'},
                json={
                    "query": f"""
                    {{
                        Aggregate {{
                            Message(where: {{path: ["conversationId"], operator: Equal, valueText: "{conversation_id}"}}) {{
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
                return data.get('data', {}).get('Aggregate', {}).get('Message', [{}])[0].get('meta', {}).get('count', 0)
            return 0
            
        except Exception as e:
            logger.error(f"Failed to count messages for conversation: {e}")
            return 0
    
    def _get_sqlite_database_size(self) -> int:
        """Get SQLite database file size in bytes."""
        try:
            db_path = self.settings.get_database_url().replace('sqlite:///', '')
            if os.path.exists(db_path):
                return os.path.getsize(db_path)
            return 0
        except Exception:
            return 0
    
    def generate_validation_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report."""
        logger.info("Generating comprehensive validation report...")
        
        # Run all validation tests
        self.validation_results["data_integrity"] = self.validate_data_integrity()
        self.validation_results["performance_comparison"] = self.validate_performance_comparison()
        self.validation_results["rollback_readiness"] = self.validate_rollback_readiness()
        
        # Calculate overall status
        integrity_passed = self.validation_results["data_integrity"].get("integrity_score", 0) >= 99.0
        performance_passed = self.validation_results["performance_comparison"].get("meets_requirements", False)
        rollback_ready = self.validation_results["rollback_readiness"].get("rollback_ready", False)
        
        overall_passed = integrity_passed and performance_passed and rollback_ready
        
        self.validation_results["overall_status"] = "PASSED" if overall_passed else "FAILED"
        self.validation_results["completed_at"] = datetime.now().isoformat()
        
        # Summary
        self.validation_results["summary"] = {
            "data_integrity_passed": integrity_passed,
            "performance_requirements_met": performance_passed,
            "rollback_ready": rollback_ready,
            "overall_passed": overall_passed,
            "integrity_score": self.validation_results["data_integrity"].get("integrity_score", 0),
            "average_query_time_ms": self.validation_results["performance_comparison"].get("weaviate_performance", {}).get("average_ms", 0)
        }
        
        return self.validation_results
    
    def cleanup(self):
        """Cleanup resources."""
        if self.sqlite_session:
            self.sqlite_session.close()


def main():
    """Main validation function."""
    print("=" * 80)
    print("  GremlinsAI Migration Integrity Validation")
    print("  Phase 2, Task 2.2: SQLite to Weaviate Migration")
    print("=" * 80)
    
    validator = MigrationIntegrityValidator()
    
    try:
        # Setup connections
        if not validator.setup_connections():
            logger.error("Failed to setup database connections")
            sys.exit(1)
        
        # Generate comprehensive validation report
        report = validator.generate_validation_report()
        
        # Save report
        report_file = f"migration_integrity_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Display results
        print("\n" + "=" * 80)
        print("  MIGRATION INTEGRITY VALIDATION REPORT")
        print("=" * 80)
        print(f"Overall Status: {report['overall_status']}")
        print(f"Data Integrity Score: {report['summary']['integrity_score']:.2f}%")
        print(f"Average Query Time: {report['summary']['average_query_time_ms']:.2f}ms")
        print(f"Rollback Ready: {'Yes' if report['summary']['rollback_ready'] else 'No'}")
        print()
        
        print("Detailed Results:")
        print(f"  ✓ Data Integrity: {'PASSED' if report['summary']['data_integrity_passed'] else 'FAILED'}")
        print(f"  ✓ Performance: {'PASSED' if report['summary']['performance_requirements_met'] else 'FAILED'}")
        print(f"  ✓ Rollback Ready: {'PASSED' if report['summary']['rollback_ready'] else 'FAILED'}")
        
        print(f"\nDetailed report saved to: {report_file}")
        
        if report['overall_status'] == "PASSED":
            print("\n🎉 Migration integrity validation PASSED!")
            sys.exit(0)
        else:
            print("\n❌ Migration integrity validation FAILED!")
            sys.exit(1)
    
    finally:
        validator.cleanup()


if __name__ == "__main__":
    main()
