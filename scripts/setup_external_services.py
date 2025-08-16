#!/usr/bin/env python3
"""
External Services Setup Script for GremlinsAI Backend

This script helps set up and configure external services required for production:
- Qdrant Vector Database
- Redis Server

It provides multiple setup options and fallback configurations.
"""

import os
import sys
import time
import subprocess
import platform
from pathlib import Path

def print_header(title):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)

def print_step(step, description):
    """Print a formatted step."""
    print(f"\n🔧 Step {step}: {description}")
    print("-" * 40)

def check_docker():
    """Check if Docker is available and running."""
    try:
        result = subprocess.run(['docker', '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Docker is installed")
            
            # Check if Docker daemon is running
            result = subprocess.run(['docker', 'ps'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print("✅ Docker daemon is running")
                return True
            else:
                print("❌ Docker daemon is not running")
                return False
        else:
            print("❌ Docker is not installed")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("❌ Docker is not available")
        return False

def setup_qdrant_docker():
    """Set up Qdrant using Docker."""
    print("Setting up Qdrant with Docker...")
    
    try:
        # Check if Qdrant container already exists
        result = subprocess.run(['docker', 'ps', '-a', '--filter', 'name=qdrant'], 
                              capture_output=True, text=True)
        
        if 'qdrant' in result.stdout:
            print("📦 Qdrant container already exists")
            
            # Check if it's running
            result = subprocess.run(['docker', 'ps', '--filter', 'name=qdrant'], 
                                  capture_output=True, text=True)
            
            if 'qdrant' in result.stdout:
                print("✅ Qdrant is already running")
                return True
            else:
                print("🔄 Starting existing Qdrant container...")
                result = subprocess.run(['docker', 'start', 'qdrant'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    print("✅ Qdrant started successfully")
                    return True
                else:
                    print(f"❌ Failed to start Qdrant: {result.stderr}")
                    return False
        else:
            print("📦 Creating new Qdrant container...")
            cmd = [
                'docker', 'run', '-d',
                '--name', 'qdrant',
                '-p', '6333:6333',
                '-p', '6334:6334',
                '-v', 'qdrant_storage:/qdrant/storage',
                'qdrant/qdrant:latest'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Qdrant container created and started")
                print("🔄 Waiting for Qdrant to be ready...")
                time.sleep(5)
                return True
            else:
                print(f"❌ Failed to create Qdrant container: {result.stderr}")
                return False
                
    except Exception as e:
        print(f"❌ Error setting up Qdrant: {e}")
        return False

def setup_redis_docker():
    """Set up Redis using Docker."""
    print("Setting up Redis with Docker...")
    
    try:
        # Check if Redis container already exists
        result = subprocess.run(['docker', 'ps', '-a', '--filter', 'name=redis'], 
                              capture_output=True, text=True)
        
        if 'redis' in result.stdout:
            print("📦 Redis container already exists")
            
            # Check if it's running
            result = subprocess.run(['docker', 'ps', '--filter', 'name=redis'], 
                                  capture_output=True, text=True)
            
            if 'redis' in result.stdout:
                print("✅ Redis is already running")
                return True
            else:
                print("🔄 Starting existing Redis container...")
                result = subprocess.run(['docker', 'start', 'redis'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    print("✅ Redis started successfully")
                    return True
                else:
                    print(f"❌ Failed to start Redis: {result.stderr}")
                    return False
        else:
            print("📦 Creating new Redis container...")
            cmd = [
                'docker', 'run', '-d',
                '--name', 'redis',
                '-p', '6379:6379',
                'redis:latest',
                'redis-server', '--appendonly', 'yes'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Redis container created and started")
                return True
            else:
                print(f"❌ Failed to create Redis container: {result.stderr}")
                return False
                
    except Exception as e:
        print(f"❌ Error setting up Redis: {e}")
        return False

def test_qdrant_connection():
    """Test Qdrant connection and create collection."""
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams
        
        print("🔍 Testing Qdrant connection...")
        client = QdrantClient(host="localhost", port=6333)
        
        # Test connection
        collections = client.get_collections()
        print("✅ Qdrant connection successful")
        
        # Create collection if it doesn't exist
        collection_name = "gremlinsai_collection"
        collection_names = [col.name for col in collections.collections]
        
        if collection_name not in collection_names:
            print(f"📝 Creating collection: {collection_name}")
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE)
            )
            print("✅ Collection created successfully")
        else:
            print(f"✅ Collection '{collection_name}' already exists")
            
        return True
        
    except Exception as e:
        print(f"❌ Qdrant connection failed: {e}")
        return False

def test_redis_connection():
    """Test Redis connection."""
    try:
        import redis
        
        print("🔍 Testing Redis connection...")
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        
        # Test connection
        r.ping()
        print("✅ Redis connection successful")
        
        # Test basic operations
        r.set('test_key', 'test_value')
        value = r.get('test_key')
        if value == 'test_value':
            print("✅ Redis read/write operations working")
            r.delete('test_key')
        
        return True
        
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False

def create_env_config():
    """Create or update .env file with service configurations."""
    env_file = Path('.env')
    
    # Read existing .env if it exists
    env_content = ""
    if env_file.exists():
        with open(env_file, 'r') as f:
            env_content = f.read()
    
    # Add service configurations if not present
    services_config = """
# External Services Configuration
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION_NAME=gremlinsai_collection

REDIS_URL=redis://localhost:6379
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
"""
    
    if "QDRANT_HOST" not in env_content:
        env_content += services_config
        
        with open(env_file, 'w') as f:
            f.write(env_content)
        
        print("✅ Updated .env file with service configurations")
    else:
        print("✅ Service configurations already present in .env")

def main():
    """Main setup function."""
    print_header("GremlinsAI External Services Setup")
    
    print("This script will set up external services required for production:")
    print("• Qdrant Vector Database (for document embeddings and semantic search)")
    print("• Redis Server (for background task processing and caching)")
    
    # Check system requirements
    print_step(1, "Checking System Requirements")
    docker_available = check_docker()
    
    if not docker_available:
        print("\n⚠️  Docker is not available. Please install Docker Desktop and try again.")
        print("   Download from: https://www.docker.com/products/docker-desktop")
        print("\n   Alternative: You can install Redis and Qdrant manually:")
        print("   • Redis: https://redis.io/download")
        print("   • Qdrant: https://qdrant.tech/documentation/guides/installation/")
        return False
    
    # Setup services
    print_step(2, "Setting Up Qdrant Vector Database")
    qdrant_success = setup_qdrant_docker()
    
    print_step(3, "Setting Up Redis Server")
    redis_success = setup_redis_docker()
    
    # Test connections
    print_step(4, "Testing Service Connections")
    
    if qdrant_success:
        qdrant_working = test_qdrant_connection()
    else:
        qdrant_working = False
        
    if redis_success:
        redis_working = test_redis_connection()
    else:
        redis_working = False
    
    # Update configuration
    print_step(5, "Updating Configuration")
    create_env_config()
    
    # Summary
    print_header("Setup Summary")
    print(f"Qdrant Vector Database: {'✅ READY' if qdrant_working else '❌ FAILED'}")
    print(f"Redis Server:           {'✅ READY' if redis_working else '❌ FAILED'}")
    
    if qdrant_working and redis_working:
        print("\n🎉 All external services are ready for production!")
        print("\nNext steps:")
        print("• Start the GremlinsAI backend: uvicorn app.main:app --reload")
        print("• Test document upload and semantic search")
        print("• Start Celery workers for background tasks")
        return True
    else:
        print("\n⚠️  Some services failed to set up. Check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
