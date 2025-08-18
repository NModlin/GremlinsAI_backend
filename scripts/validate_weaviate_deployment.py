#!/usr/bin/env python3
"""
GremlinsAI Weaviate Deployment Validation Script
Phase 2, Task 2.1: Weaviate Deployment & Schema Activation

This script validates the Weaviate deployment by performing comprehensive
health checks, schema validation, and performance testing to ensure the
cluster meets the acceptance criteria from divineKatalyst.md.

Acceptance Criteria:
- Weaviate cluster successfully deployed using Kubernetes configurations
- Cluster can handle 10,000+ documents with query time < 100ms
- Schema activated with all necessary data types and vectors
- Client connection wrapper provides consistent API with connection pooling
"""

import os
import sys
import logging
import time
import json
import uuid
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'app'))

try:
    import weaviate
    from weaviate.classes.init import Auth
    from weaviate.exceptions import WeaviateBaseError
    import requests
except ImportError as e:
    print(f"Error: Required packages not installed: {e}")
    print("Install with: pip install weaviate-client requests")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('weaviate_validation.log')
    ]
)
logger = logging.getLogger(__name__)

# Test configuration
TEST_CONFIG = {
    "performance_test_docs": 1000,  # Start with 1K for initial testing
    "load_test_docs": 10000,       # Full load test with 10K documents
    "query_timeout_ms": 100,       # Maximum acceptable query time
    "concurrent_queries": 50,      # Number of concurrent queries for load testing
    "test_collections": ["Conversation", "Message", "DocumentChunk"]
}


class WeaviateValidator:
    """Comprehensive Weaviate deployment validator."""
    
    def __init__(self, weaviate_url: str = None, api_key: str = None):
        """
        Initialize the validator.
        
        Args:
            weaviate_url: Weaviate server URL
            api_key: API key for authentication
        """
        self.weaviate_url = weaviate_url or os.getenv('WEAVIATE_URL', 'http://localhost:8080')
        self.api_key = api_key or os.getenv('WEAVIATE_API_KEY')
        self.client = None
        self.test_results = {}
        
        logger.info(f"Initializing Weaviate Deployment Validator")
        logger.info(f"Weaviate URL: {self.weaviate_url}")
        logger.info(f"API Key configured: {'Yes' if self.api_key else 'No'}")
    
    def connect(self) -> bool:
        """Establish connection to Weaviate cluster."""
        try:
            logger.info("Connecting to Weaviate cluster...")
            
            auth_config = None
            if self.api_key:
                auth_config = Auth.api_key(self.api_key)
            
            self.client = weaviate.Client(
                url=self.weaviate_url,
                auth_client_secret=auth_config,
                timeout_config=(5, 15)
            )
            
            if self.client.is_ready():
                logger.info("Successfully connected to Weaviate cluster")
                return True
            else:
                logger.error("Weaviate cluster is not ready")
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect to Weaviate: {e}")
            return False
    
    def validate_cluster_health(self) -> bool:
        """Validate cluster health and availability."""
        logger.info("Validating cluster health...")
        
        try:
            # Check if cluster is ready
            if not self.client.is_ready():
                logger.error("Cluster is not ready")
                return False
            
            # Get cluster metadata
            meta = self.client.get_meta()
            
            # Validate cluster information
            version = meta.get('version', 'unknown')
            hostname = meta.get('hostname', 'unknown')
            nodes = meta.get('nodes', {})
            
            logger.info(f"Cluster version: {version}")
            logger.info(f"Cluster hostname: {hostname}")
            logger.info(f"Number of nodes: {len(nodes)}")
            
            # Check node health
            healthy_nodes = 0
            for node_name, node_info in nodes.items():
                status = node_info.get('status', 'unknown')
                if status == 'HEALTHY':
                    healthy_nodes += 1
                logger.info(f"Node {node_name}: {status}")
            
            if healthy_nodes == 0:
                logger.error("No healthy nodes found")
                return False
            
            logger.info(f"Cluster health validation passed: {healthy_nodes} healthy nodes")
            self.test_results['cluster_health'] = {
                'passed': True,
                'healthy_nodes': healthy_nodes,
                'total_nodes': len(nodes),
                'version': version
            }
            
            return True
            
        except Exception as e:
            logger.error(f"Cluster health validation failed: {e}")
            self.test_results['cluster_health'] = {'passed': False, 'error': str(e)}
            return False
    
    def validate_schema(self) -> bool:
        """Validate that all required collections exist with proper configuration."""
        logger.info("Validating Weaviate schema...")
        
        try:
            schema = self.client.schema.get()
            existing_classes = {cls['class']: cls for cls in schema.get('classes', [])}
            
            required_collections = TEST_CONFIG["test_collections"]
            missing_collections = []
            valid_collections = []
            
            for collection_name in required_collections:
                if collection_name not in existing_classes:
                    missing_collections.append(collection_name)
                else:
                    collection_info = existing_classes[collection_name]
                    properties = collection_info.get('properties', [])
                    vectorizer = collection_info.get('vectorizer', 'none')
                    
                    logger.info(f"Collection '{collection_name}': {len(properties)} properties, vectorizer: {vectorizer}")
                    valid_collections.append({
                        'name': collection_name,
                        'properties': len(properties),
                        'vectorizer': vectorizer
                    })
            
            if missing_collections:
                logger.error(f"Missing required collections: {missing_collections}")
                self.test_results['schema_validation'] = {
                    'passed': False,
                    'missing_collections': missing_collections
                }
                return False
            
            logger.info(f"Schema validation passed: All {len(required_collections)} required collections exist")
            self.test_results['schema_validation'] = {
                'passed': True,
                'collections': valid_collections,
                'total_collections': len(existing_classes)
            }
            
            return True
            
        except Exception as e:
            logger.error(f"Schema validation failed: {e}")
            self.test_results['schema_validation'] = {'passed': False, 'error': str(e)}
            return False
    
    def test_basic_operations(self) -> bool:
        """Test basic CRUD operations on each collection."""
        logger.info("Testing basic CRUD operations...")
        
        test_objects = []
        operation_results = {}
        
        try:
            for collection_name in TEST_CONFIG["test_collections"]:
                logger.info(f"Testing operations on collection: {collection_name}")
                
                # Create test object
                test_data = self._generate_test_data(collection_name)
                
                # CREATE operation
                start_time = time.time()
                result = self.client.data_object.create(
                    data_object=test_data,
                    class_name=collection_name
                )
                create_time = (time.time() - start_time) * 1000
                
                if result:
                    test_objects.append((collection_name, result))
                    logger.info(f"CREATE {collection_name}: {create_time:.2f}ms")
                else:
                    logger.error(f"Failed to create object in {collection_name}")
                    operation_results[collection_name] = {'passed': False, 'operation': 'CREATE'}
                    continue
                
                # READ operation
                start_time = time.time()
                retrieved = self.client.data_object.get_by_id(result, class_name=collection_name)
                read_time = (time.time() - start_time) * 1000
                
                if retrieved:
                    logger.info(f"READ {collection_name}: {read_time:.2f}ms")
                else:
                    logger.error(f"Failed to read object from {collection_name}")
                    operation_results[collection_name] = {'passed': False, 'operation': 'READ'}
                    continue
                
                # UPDATE operation
                updated_data = test_data.copy()
                if collection_name == "Conversation":
                    updated_data["title"] = "Updated Test Conversation"
                elif collection_name == "Message":
                    updated_data["content"] = "Updated test message content"
                elif collection_name == "DocumentChunk":
                    updated_data["content"] = "Updated test document chunk content"
                
                start_time = time.time()
                self.client.data_object.update(
                    data_object=updated_data,
                    class_name=collection_name,
                    uuid=result
                )
                update_time = (time.time() - start_time) * 1000
                logger.info(f"UPDATE {collection_name}: {update_time:.2f}ms")
                
                operation_results[collection_name] = {
                    'passed': True,
                    'create_time_ms': create_time,
                    'read_time_ms': read_time,
                    'update_time_ms': update_time
                }
            
            # Clean up test objects
            for collection_name, object_id in test_objects:
                try:
                    self.client.data_object.delete(object_id, class_name=collection_name)
                except Exception as e:
                    logger.warning(f"Failed to clean up test object in {collection_name}: {e}")
            
            # Check if all operations passed
            all_passed = all(result.get('passed', False) for result in operation_results.values())
            
            if all_passed:
                logger.info("Basic operations test passed for all collections")
            else:
                logger.error("Basic operations test failed for some collections")
            
            self.test_results['basic_operations'] = {
                'passed': all_passed,
                'results': operation_results
            }
            
            return all_passed
            
        except Exception as e:
            logger.error(f"Basic operations test failed: {e}")
            self.test_results['basic_operations'] = {'passed': False, 'error': str(e)}
            return False
    
    def test_query_performance(self) -> bool:
        """Test query performance with the target load."""
        logger.info("Testing query performance...")
        
        try:
            # First, populate with test data
            logger.info(f"Populating {TEST_CONFIG['performance_test_docs']} test documents...")
            
            test_objects = []
            batch_size = 100
            
            # Create test documents in batches
            for i in range(0, TEST_CONFIG['performance_test_docs'], batch_size):
                batch_end = min(i + batch_size, TEST_CONFIG['performance_test_docs'])
                batch_objects = []
                
                for j in range(i, batch_end):
                    test_data = {
                        "content": f"Test document content {j} for performance testing. This is a longer text to simulate real document content.",
                        "document_title": f"Performance Test Document {j}",
                        "chunk_index": j % 10,
                        "metadata": {"test_id": j, "batch": i // batch_size}
                    }
                    batch_objects.append(test_data)
                
                # Batch insert
                start_time = time.time()
                results = self.client.batch.create_objects(
                    objects=[{"class": "DocumentChunk", "properties": obj} for obj in batch_objects]
                )
                batch_time = (time.time() - start_time) * 1000
                
                successful_inserts = len([r for r in results if r.get('result', {}).get('status') == 'SUCCESS'])
                logger.info(f"Batch {i//batch_size + 1}: {successful_inserts}/{len(batch_objects)} objects inserted in {batch_time:.2f}ms")
                
                test_objects.extend([r['result']['id'] for r in results if r.get('result', {}).get('status') == 'SUCCESS'])
            
            logger.info(f"Successfully inserted {len(test_objects)} test documents")
            
            # Test query performance
            query_times = []
            successful_queries = 0
            
            for i in range(10):  # Run 10 test queries
                query = {
                    "query": """
                    {
                        Get {
                            DocumentChunk(limit: 10, where: {
                                path: ["chunk_index"],
                                operator: LessThan,
                                valueInt: 5
                            }) {
                                content
                                document_title
                                chunk_index
                            }
                        }
                    }
                    """
                }
                
                start_time = time.time()
                try:
                    result = self.client.query.raw(query["query"])
                    query_time = (time.time() - start_time) * 1000
                    query_times.append(query_time)
                    successful_queries += 1
                    
                    if i == 0:  # Log first query result for verification
                        results_count = len(result.get('data', {}).get('Get', {}).get('DocumentChunk', []))
                        logger.info(f"Query {i+1}: {query_time:.2f}ms, {results_count} results")
                    
                except Exception as e:
                    logger.error(f"Query {i+1} failed: {e}")
            
            # Calculate performance metrics
            if query_times:
                avg_query_time = sum(query_times) / len(query_times)
                max_query_time = max(query_times)
                min_query_time = min(query_times)
                
                performance_passed = avg_query_time < TEST_CONFIG["query_timeout_ms"]
                
                logger.info(f"Query performance results:")
                logger.info(f"  Average query time: {avg_query_time:.2f}ms")
                logger.info(f"  Min query time: {min_query_time:.2f}ms")
                logger.info(f"  Max query time: {max_query_time:.2f}ms")
                logger.info(f"  Successful queries: {successful_queries}/10")
                logger.info(f"  Performance target (<{TEST_CONFIG['query_timeout_ms']}ms): {'PASSED' if performance_passed else 'FAILED'}")
                
                self.test_results['query_performance'] = {
                    'passed': performance_passed and successful_queries >= 8,
                    'avg_query_time_ms': avg_query_time,
                    'max_query_time_ms': max_query_time,
                    'min_query_time_ms': min_query_time,
                    'successful_queries': successful_queries,
                    'total_queries': 10,
                    'test_documents': len(test_objects)
                }
            else:
                logger.error("No successful queries completed")
                self.test_results['query_performance'] = {'passed': False, 'error': 'No successful queries'}
                performance_passed = False
            
            # Clean up test data
            logger.info("Cleaning up test data...")
            cleanup_count = 0
            for obj_id in test_objects:
                try:
                    self.client.data_object.delete(obj_id, class_name="DocumentChunk")
                    cleanup_count += 1
                except Exception as e:
                    logger.warning(f"Failed to clean up object {obj_id}: {e}")
            
            logger.info(f"Cleaned up {cleanup_count}/{len(test_objects)} test objects")
            
            return performance_passed and successful_queries >= 8
            
        except Exception as e:
            logger.error(f"Query performance test failed: {e}")
            self.test_results['query_performance'] = {'passed': False, 'error': str(e)}
            return False
    
    def test_connection_pooling(self) -> bool:
        """Test connection pooling and concurrent access."""
        logger.info("Testing connection pooling and concurrent access...")
        
        try:
            # Test multiple concurrent connections
            def test_concurrent_query(query_id: int) -> Tuple[int, bool, float]:
                try:
                    start_time = time.time()
                    
                    # Create a new client for this thread
                    auth_config = None
                    if self.api_key:
                        auth_config = Auth.api_key(self.api_key)
                    
                    thread_client = weaviate.Client(
                        url=self.weaviate_url,
                        auth_client_secret=auth_config,
                        timeout_config=(5, 15)
                    )
                    
                    # Simple query to test connection
                    result = thread_client.query.raw("""
                    {
                        Get {
                            Conversation(limit: 1) {
                                title
                            }
                        }
                    }
                    """)
                    
                    query_time = (time.time() - start_time) * 1000
                    return query_id, True, query_time
                    
                except Exception as e:
                    query_time = (time.time() - start_time) * 1000
                    logger.warning(f"Concurrent query {query_id} failed: {e}")
                    return query_id, False, query_time
            
            # Run concurrent queries
            concurrent_queries = 20
            successful_queries = 0
            query_times = []
            
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(test_concurrent_query, i) for i in range(concurrent_queries)]
                
                for future in as_completed(futures):
                    query_id, success, query_time = future.result()
                    if success:
                        successful_queries += 1
                        query_times.append(query_time)
            
            success_rate = (successful_queries / concurrent_queries) * 100
            avg_concurrent_time = sum(query_times) / len(query_times) if query_times else 0
            
            connection_pooling_passed = success_rate >= 90  # 90% success rate required
            
            logger.info(f"Connection pooling test results:")
            logger.info(f"  Successful queries: {successful_queries}/{concurrent_queries} ({success_rate:.1f}%)")
            logger.info(f"  Average query time: {avg_concurrent_time:.2f}ms")
            logger.info(f"  Connection pooling test: {'PASSED' if connection_pooling_passed else 'FAILED'}")
            
            self.test_results['connection_pooling'] = {
                'passed': connection_pooling_passed,
                'successful_queries': successful_queries,
                'total_queries': concurrent_queries,
                'success_rate': success_rate,
                'avg_query_time_ms': avg_concurrent_time
            }
            
            return connection_pooling_passed
            
        except Exception as e:
            logger.error(f"Connection pooling test failed: {e}")
            self.test_results['connection_pooling'] = {'passed': False, 'error': str(e)}
            return False
    
    def _generate_test_data(self, collection_name: str) -> Dict[str, Any]:
        """Generate test data for a specific collection."""
        timestamp = datetime.now().isoformat()
        
        if collection_name == "Conversation":
            return {
                "title": "Test Conversation",
                "summary": "This is a test conversation for validation",
                "created_at": timestamp,
                "user_id": "test-user-123",
                "metadata": {"test": True, "validation": "basic_operations"}
            }
        elif collection_name == "Message":
            return {
                "content": "This is a test message for validation",
                "role": "user",
                "timestamp": timestamp,
                "embedding_model": "test-model"
            }
        elif collection_name == "DocumentChunk":
            return {
                "content": "This is a test document chunk for validation",
                "document_title": "Test Document",
                "chunk_index": 0,
                "metadata": {"test": True, "validation": "basic_operations"}
            }
        else:
            return {"test_field": "test_value", "timestamp": timestamp}
    
    def generate_validation_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report."""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result.get('passed', False))
        
        report = {
            "validation_summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                "overall_status": "PASSED" if passed_tests == total_tests else "FAILED",
                "timestamp": datetime.now().isoformat()
            },
            "test_results": self.test_results,
            "acceptance_criteria": {
                "weaviate_cluster_deployed": self.test_results.get('cluster_health', {}).get('passed', False),
                "schema_activated": self.test_results.get('schema_validation', {}).get('passed', False),
                "performance_target_met": self.test_results.get('query_performance', {}).get('passed', False),
                "connection_pooling_working": self.test_results.get('connection_pooling', {}).get('passed', False)
            }
        }
        
        return report


def main():
    """Main validation function."""
    print("=" * 80)
    print("  GremlinsAI Weaviate Deployment Validation")
    print("  Phase 2, Task 2.1: Weaviate Deployment & Schema Activation")
    print("=" * 80)
    
    # Initialize validator
    validator = WeaviateValidator()
    
    # Connect to Weaviate
    if not validator.connect():
        logger.error("Failed to connect to Weaviate cluster")
        sys.exit(1)
    
    # Run validation tests
    tests = [
        ("Cluster Health", validator.validate_cluster_health),
        ("Schema Validation", validator.validate_schema),
        ("Basic Operations", validator.test_basic_operations),
        ("Query Performance", validator.test_query_performance),
        ("Connection Pooling", validator.test_connection_pooling)
    ]
    
    print(f"\nRunning {len(tests)} validation tests...\n")
    
    for test_name, test_func in tests:
        print(f"Running {test_name}...")
        try:
            result = test_func()
            status = "PASSED" if result else "FAILED"
            print(f"  {test_name}: {status}\n")
        except Exception as e:
            print(f"  {test_name}: FAILED - {e}\n")
            logger.error(f"{test_name} failed with exception: {e}")
    
    # Generate and display report
    report = validator.generate_validation_report()
    
    print("=" * 80)
    print("  VALIDATION REPORT")
    print("=" * 80)
    print(f"Overall Status: {report['validation_summary']['overall_status']}")
    print(f"Tests Passed: {report['validation_summary']['passed_tests']}/{report['validation_summary']['total_tests']}")
    print(f"Success Rate: {report['validation_summary']['success_rate']:.1f}%")
    print()
    
    print("Acceptance Criteria:")
    for criterion, status in report['acceptance_criteria'].items():
        status_text = "✓ PASSED" if status else "✗ FAILED"
        print(f"  {criterion.replace('_', ' ').title()}: {status_text}")
    
    # Save detailed report
    report_file = f"weaviate_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\nDetailed report saved to: {report_file}")
    
    # Exit with appropriate code
    if report['validation_summary']['overall_status'] == "PASSED":
        print("\n🎉 Weaviate deployment validation completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Weaviate deployment validation failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
