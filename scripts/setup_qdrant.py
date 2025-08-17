#!/usr/bin/env python3
"""
Qdrant Vector Database Setup Script for GremlinsAI

This script helps set up Qdrant vector database using Docker for enhanced
RAG capabilities and semantic search functionality.
"""

import subprocess
import sys
import time
import requests
from pathlib import Path

def check_docker():
    """Check if Docker is installed and running."""
    try:
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ Docker is not installed")
            return False
        
        print(f"✅ Docker found: {result.stdout.strip()}")
        
        # Check if Docker daemon is running
        result = subprocess.run(['docker', 'ps'], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ Docker daemon is not running")
            print("Please start Docker Desktop and try again")
            return False
        
        print("✅ Docker daemon is running")
        return True
        
    except FileNotFoundError:
        print("❌ Docker is not installed")
        return False

def check_qdrant_running():
    """Check if Qdrant is already running."""
    try:
        result = subprocess.run(['docker', 'ps'], capture_output=True, text=True)
        if 'qdrant' in result.stdout:
            print("✅ Qdrant container is already running")
            return True
        return False
    except Exception:
        return False

def start_qdrant():
    """Start Qdrant using Docker."""
    print("🚀 Starting Qdrant vector database...")
    
    # Check if container exists but is stopped
    result = subprocess.run(['docker', 'ps', '-a'], capture_output=True, text=True)
    if 'qdrant' in result.stdout:
        print("📦 Found existing Qdrant container, starting it...")
        result = subprocess.run(['docker', 'start', 'qdrant'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Qdrant container started successfully")
            return True
        else:
            print(f"❌ Failed to start Qdrant container: {result.stderr}")
            return False
    
    # Create new container
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
        print("✅ Qdrant container created and started successfully")
        return True
    else:
        print(f"❌ Failed to create Qdrant container: {result.stderr}")
        return False

def wait_for_qdrant():
    """Wait for Qdrant to be ready."""
    print("⏳ Waiting for Qdrant to be ready...")
    
    for i in range(30):  # Wait up to 30 seconds
        try:
            response = requests.get("http://localhost:6333/health", timeout=2)
            if response.status_code == 200:
                print("✅ Qdrant is ready!")
                return True
        except requests.exceptions.RequestException:
            pass
        
        time.sleep(1)
        print(f"   Waiting... ({i+1}/30)")
    
    print("❌ Qdrant did not become ready in time")
    return False

def test_qdrant_connection():
    """Test Qdrant connection and create test collection."""
    try:
        from qdrant_client import QdrantClient
        
        print("🔗 Testing Qdrant connection...")
        client = QdrantClient(host="localhost", port=6333)
        
        # Get collections to test connection
        collections = client.get_collections()
        print(f"✅ Connected to Qdrant successfully")
        print(f"   Current collections: {len(collections.collections)}")
        
        return True
        
    except ImportError:
        print("❌ qdrant-client not installed")
        print("   Run: pip install qdrant-client")
        return False
    except Exception as e:
        print(f"❌ Failed to connect to Qdrant: {e}")
        return False

def show_usage_info():
    """Show information about using Qdrant with GremlinsAI."""
    print("\n" + "="*60)
    print("🎉 Qdrant Setup Complete!")
    print("="*60)
    print()
    print("Qdrant is now running and ready for use with GremlinsAI.")
    print()
    print("📊 Access Points:")
    print("   • REST API: http://localhost:6333")
    print("   • Web UI: http://localhost:6333/dashboard")
    print("   • gRPC: localhost:6334")
    print()
    print("🔧 Configuration:")
    print("   Your .env file is already configured with:")
    print("   • QDRANT_HOST=localhost")
    print("   • QDRANT_PORT=6333")
    print("   • QDRANT_COLLECTION=gremlins_documents")
    print()
    print("🚀 Next Steps:")
    print("   1. Restart your GremlinsAI backend to connect to Qdrant")
    print("   2. Upload documents to enable semantic search")
    print("   3. Use RAG-enhanced queries for better responses")
    print()
    print("🛑 To stop Qdrant:")
    print("   docker stop qdrant")
    print()
    print("🗑️ To remove Qdrant (and all data):")
    print("   docker stop qdrant && docker rm qdrant")
    print("   docker volume rm qdrant_storage")

def main():
    """Main setup function."""
    print("🔧 GremlinsAI Qdrant Setup")
    print("="*40)
    print()
    
    # Check prerequisites
    if not check_docker():
        print("\n❌ Setup failed: Docker is required")
        print("\nPlease install Docker Desktop and try again:")
        print("https://www.docker.com/products/docker-desktop/")
        sys.exit(1)
    
    # Check if already running
    if check_qdrant_running():
        if test_qdrant_connection():
            show_usage_info()
            return
    
    # Start Qdrant
    if not start_qdrant():
        print("\n❌ Setup failed: Could not start Qdrant")
        sys.exit(1)
    
    # Wait for it to be ready
    if not wait_for_qdrant():
        print("\n❌ Setup failed: Qdrant did not start properly")
        sys.exit(1)
    
    # Test connection
    if not test_qdrant_connection():
        print("\n⚠️ Qdrant is running but connection test failed")
        print("You may need to install qdrant-client:")
        print("pip install qdrant-client")
    
    show_usage_info()

if __name__ == "__main__":
    main()
