#!/usr/bin/env python3
"""Simple script to check if the application is running."""

import asyncio
import httpx
import sys


async def check_app():
    """Check if the application is running."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get('http://localhost:8000/')
            print(f"Application status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"API Version: {data.get('version', 'N/A')}")
                print("✅ Application is running")
                return True
            else:
                print("❌ Application returned error status")
                return False
    except Exception as e:
        print(f"❌ Cannot connect to application: {e}")
        print("Please start the application with: python -m uvicorn app.main:app --reload")
        return False


if __name__ == "__main__":
    result = asyncio.run(check_app())
    sys.exit(0 if result else 1)
