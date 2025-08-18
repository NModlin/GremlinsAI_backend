#!/usr/bin/env python3
"""
GremlinsAI Weaviate Schema Activation Script
Phase 2, Task 2.1: Weaviate Deployment & Schema Activation

This script activates the predefined Weaviate schema for GremlinsAI,
creating all necessary collections with proper vectorizer configurations
and properties as specified in prometheus.md.

The script is idempotent and can be run multiple times safely.
"""

import os
import sys
import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'app'))

try:
    import weaviate
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
        logging.FileHandler('weaviate_schema_activation.log')
    ]
)
logger = logging.getLogger(__name__)

# Weaviate Schema Definition from prometheus.md
WEAVIATE_SCHEMA = {
    "Conversation": {
        "vectorizer": "text2vec-transformers",
        "properties": {
            "title": {"dataType": ["text"]},
            "summary": {"dataType": ["text"]},
            "created_at": {"dataType": ["date"]},
            "user_id": {"dataType": ["text"]},
            "metadata": {"dataType": ["object"]}
        }
    },
    "Message": {
        "vectorizer": "text2vec-transformers",
        "properties": {
            "content": {"dataType": ["text"]},
            "role": {"dataType": ["text"]},
            "timestamp": {"dataType": ["date"]},
            "embedding_model": {"dataType": ["text"]}
        }
    },
    "DocumentChunk": {
        "vectorizer": "text2vec-transformers",
        "properties": {
            "content": {"dataType": ["text"]},
            "document_title": {"dataType": ["text"]},
            "chunk_index": {"dataType": ["int"]},
            "metadata": {"dataType": ["object"]}
        }
    }
}

# Extended schema for full GremlinsAI functionality
EXTENDED_SCHEMA = {
    "Document": {
        "vectorizer": "text2vec-transformers",
        "properties": {
            "title": {"dataType": ["text"]},
            "content": {"dataType": ["text"]},
            "content_type": {"dataType": ["text"]},
            "file_path": {"dataType": ["text"]},
            "file_size": {"dataType": ["int"]},
            "created_at": {"dataType": ["date"]},
            "updated_at": {"dataType": ["date"]},
            "is_active": {"dataType": ["boolean"]},
            "metadata": {"dataType": ["object"]}
        }
    },
    "AgentInteraction": {
        "vectorizer": "text2vec-transformers",
        "properties": {
            "agent_name": {"dataType": ["text"]},
            "interaction_type": {"dataType": ["text"]},
            "input_data": {"dataType": ["text"]},
            "output_data": {"dataType": ["text"]},
            "success": {"dataType": ["boolean"]},
            "execution_time": {"dataType": ["number"]},
            "conversation_id": {"dataType": ["text"]},
            "created_at": {"dataType": ["date"]},
            "metadata": {"dataType": ["object"]}
        }
    }
}


class WeaviateSchemaActivator:
    """Handles Weaviate schema activation for GremlinsAI."""
    
    def __init__(self, weaviate_url: str = None, api_key: str = None):
        """
        Initialize the schema activator.
        
        Args:
            weaviate_url: Weaviate server URL
            api_key: API key for authentication
        """
        self.weaviate_url = weaviate_url or os.getenv('WEAVIATE_URL', 'http://localhost:8080')
        self.api_key = api_key or os.getenv('WEAVIATE_API_KEY')
        self.client = None
        
        logger.info(f"Initializing Weaviate Schema Activator")
        logger.info(f"Weaviate URL: {self.weaviate_url}")
        logger.info(f"API Key configured: {'Yes' if self.api_key else 'No'}")
    
    def connect(self) -> bool:
        """
        Establish connection to Weaviate cluster using REST API.

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            logger.info("Connecting to Weaviate cluster...")

            # Test connection using REST API
            headers = {}
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'
                logger.info("Using API key authentication")
            else:
                logger.warning("No API key provided - using anonymous access")

            # Test connection with ready endpoint
            response = requests.get(f"{self.weaviate_url}/v1/.well-known/ready",
                                  headers=headers, timeout=10)

            if response.status_code == 200 and response.json().get('ready', False):
                logger.info("Successfully connected to Weaviate cluster")

                # Get cluster information
                meta_response = requests.get(f"{self.weaviate_url}/v1/meta",
                                           headers=headers, timeout=10)
                if meta_response.status_code == 200:
                    meta = meta_response.json()
                    logger.info(f"Weaviate version: {meta.get('version', 'unknown')}")
                    logger.info(f"Cluster hostname: {meta.get('hostname', 'unknown')}")

                self.headers = headers  # Store headers for future requests
                return True
            else:
                logger.error(f"Weaviate cluster is not ready. Status: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Failed to connect to Weaviate: {e}")
            return False
    
    def collection_exists(self, collection_name: str) -> bool:
        """
        Check if a collection already exists.

        Args:
            collection_name: Name of the collection to check

        Returns:
            bool: True if collection exists, False otherwise
        """
        try:
            response = requests.get(f"{self.weaviate_url}/v1/schema",
                                  headers=self.headers, timeout=10)
            if response.status_code == 200:
                schema = response.json()
                existing_classes = [cls['class'] for cls in schema.get('classes', [])]
                return collection_name in existing_classes
            return False
        except Exception as e:
            logger.error(f"Error checking collection existence: {e}")
            return False
    
    def create_collection(self, collection_name: str, collection_config: Dict[str, Any]) -> bool:
        """
        Create a single collection with the specified configuration.

        Args:
            collection_name: Name of the collection to create
            collection_config: Collection configuration dictionary

        Returns:
            bool: True if creation successful, False otherwise
        """
        try:
            logger.info(f"Creating collection: {collection_name}")

            # Check if collection already exists
            if self.collection_exists(collection_name):
                logger.info(f"Collection '{collection_name}' already exists - skipping")
                return True

            # Build properties list
            properties = []
            for prop_name, prop_config in collection_config["properties"].items():
                # Convert dataType format to Weaviate schema format
                data_types = prop_config["dataType"]

                property_def = {
                    "name": prop_name,
                    "dataType": data_types,
                    "description": f"{collection_name} {prop_name} property"
                }
                properties.append(property_def)

            # Create the collection schema
            collection_schema = {
                "class": collection_name,
                "description": f"GremlinsAI {collection_name} collection for semantic search and retrieval",
                "properties": properties,
                "vectorizer": collection_config.get("vectorizer", "text2vec-transformers")
            }

            # Add vectorizer configuration if using transformers
            if collection_schema["vectorizer"] == "text2vec-transformers":
                collection_schema["moduleConfig"] = {
                    "text2vec-transformers": {
                        "model": "sentence-transformers/all-MiniLM-L6-v2",
                        "vectorizeClassName": False
                    }
                }

            # Send POST request to create collection
            response = requests.post(
                f"{self.weaviate_url}/v1/schema",
                headers={**self.headers, 'Content-Type': 'application/json'},
                json=collection_schema,
                timeout=30
            )

            if response.status_code == 200:
                logger.info(f"Successfully created collection: {collection_name}")
                return True
            else:
                logger.error(f"Failed to create collection '{collection_name}': {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Failed to create collection '{collection_name}': {e}")
            return False
    
    def activate_core_schema(self) -> bool:
        """
        Activate the core Weaviate schema as defined in prometheus.md.
        
        Returns:
            bool: True if all collections created successfully, False otherwise
        """
        logger.info("Activating core Weaviate schema...")
        
        success_count = 0
        total_collections = len(WEAVIATE_SCHEMA)
        
        for collection_name, collection_config in WEAVIATE_SCHEMA.items():
            if self.create_collection(collection_name, collection_config):
                success_count += 1
            else:
                logger.error(f"Failed to create core collection: {collection_name}")
        
        if success_count == total_collections:
            logger.info(f"Successfully activated all {total_collections} core collections")
            return True
        else:
            logger.error(f"Only {success_count}/{total_collections} core collections created successfully")
            return False
    
    def activate_extended_schema(self) -> bool:
        """
        Activate the extended Weaviate schema for full GremlinsAI functionality.
        
        Returns:
            bool: True if all collections created successfully, False otherwise
        """
        logger.info("Activating extended Weaviate schema...")
        
        success_count = 0
        total_collections = len(EXTENDED_SCHEMA)
        
        for collection_name, collection_config in EXTENDED_SCHEMA.items():
            if self.create_collection(collection_name, collection_config):
                success_count += 1
            else:
                logger.error(f"Failed to create extended collection: {collection_name}")
        
        if success_count == total_collections:
            logger.info(f"Successfully activated all {total_collections} extended collections")
            return True
        else:
            logger.warning(f"Only {success_count}/{total_collections} extended collections created successfully")
            return success_count > 0  # Partial success is acceptable for extended schema
    
    def verify_schema(self) -> bool:
        """
        Verify that all required collections exist and are properly configured.

        Returns:
            bool: True if schema verification successful, False otherwise
        """
        logger.info("Verifying Weaviate schema...")

        try:
            response = requests.get(f"{self.weaviate_url}/v1/schema",
                                  headers=self.headers, timeout=10)

            if response.status_code != 200:
                logger.error(f"Failed to get schema: {response.status_code}")
                return False

            schema = response.json()
            existing_classes = [cls['class'] for cls in schema.get('classes', [])]

            # Check core collections
            missing_core = []
            for collection_name in WEAVIATE_SCHEMA.keys():
                if collection_name not in existing_classes:
                    missing_core.append(collection_name)

            if missing_core:
                logger.error(f"Missing core collections: {missing_core}")
                return False

            logger.info("All core collections verified successfully")

            # Check extended collections (optional)
            missing_extended = []
            for collection_name in EXTENDED_SCHEMA.keys():
                if collection_name not in existing_classes:
                    missing_extended.append(collection_name)

            if missing_extended:
                logger.warning(f"Missing extended collections: {missing_extended}")
            else:
                logger.info("All extended collections verified successfully")

            # Display schema summary
            logger.info(f"Total collections in schema: {len(existing_classes)}")
            for class_info in schema.get('classes', []):
                class_name = class_info['class']
                prop_count = len(class_info.get('properties', []))
                vectorizer = class_info.get('vectorizer', 'unknown')
                logger.info(f"  - {class_name}: {prop_count} properties, vectorizer: {vectorizer}")

            return True

        except Exception as e:
            logger.error(f"Schema verification failed: {e}")
            return False
    
    def get_cluster_health(self) -> Dict[str, Any]:
        """
        Get cluster health information.

        Returns:
            Dict containing cluster health metrics
        """
        try:
            # Get cluster metadata
            meta_response = requests.get(f"{self.weaviate_url}/v1/meta",
                                       headers=self.headers, timeout=10)

            # Get schema information
            schema_response = requests.get(f"{self.weaviate_url}/v1/schema",
                                         headers=self.headers, timeout=10)

            # Check readiness
            ready_response = requests.get(f"{self.weaviate_url}/v1/.well-known/ready",
                                        headers=self.headers, timeout=10)

            cluster_ready = (ready_response.status_code == 200 and
                           ready_response.json().get('ready', False))

            meta = meta_response.json() if meta_response.status_code == 200 else {}
            schema = schema_response.json() if schema_response.status_code == 200 else {}

            # Get node information
            nodes = meta.get('nodes', {})
            node_count = len(nodes)

            # Get collection count
            collection_count = len(schema.get('classes', []))

            health_info = {
                "cluster_ready": cluster_ready,
                "node_count": node_count,
                "collection_count": collection_count,
                "version": meta.get('version', 'unknown'),
                "hostname": meta.get('hostname', 'unknown'),
                "timestamp": datetime.now().isoformat()
            }

            return health_info

        except Exception as e:
            logger.error(f"Failed to get cluster health: {e}")
            return {"error": str(e)}


def main():
    """Main function to activate Weaviate schema."""
    print("=" * 70)
    print("  GremlinsAI Weaviate Schema Activation")
    print("  Phase 2, Task 2.1: Weaviate Deployment & Schema Activation")
    print("=" * 70)
    
    # Initialize schema activator
    activator = WeaviateSchemaActivator()
    
    # Connect to Weaviate
    if not activator.connect():
        logger.error("Failed to connect to Weaviate cluster")
        sys.exit(1)
    
    # Get initial cluster health
    health = activator.get_cluster_health()
    logger.info(f"Cluster health: {health}")
    
    # Activate core schema
    if not activator.activate_core_schema():
        logger.error("Failed to activate core schema")
        sys.exit(1)
    
    # Activate extended schema (optional)
    activator.activate_extended_schema()
    
    # Verify schema
    if not activator.verify_schema():
        logger.error("Schema verification failed")
        sys.exit(1)
    
    # Final health check
    final_health = activator.get_cluster_health()
    logger.info(f"Final cluster state: {final_health}")
    
    print("\n" + "=" * 70)
    print("  Schema Activation Completed Successfully!")
    print("=" * 70)
    print(f"  Collections created: {final_health.get('collection_count', 'unknown')}")
    print(f"  Cluster nodes: {final_health.get('node_count', 'unknown')}")
    print(f"  Weaviate version: {final_health.get('version', 'unknown')}")
    print("=" * 70)
    print("\nNext steps:")
    print("  1. Run validation script: python scripts/validate_weaviate_deployment.py")
    print("  2. Configure application to use Weaviate endpoints")
    print("  3. Begin data migration from SQLite to Weaviate")


if __name__ == "__main__":
    main()
