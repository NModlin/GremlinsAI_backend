#!/usr/bin/env python3
"""
Test script for Phase 1 implementation.
This script tests the basic agent functionality without starting the full server.
"""

import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_imports():
    """Test that all modules can be imported successfully."""
    try:
        from app.core.tools import duckduckgo_search
        from app.core.agent import agent_graph_app
        from app.api.v1.endpoints.agent import router
        from app.main import app
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_agent_basic():
    """Test basic agent functionality."""
    try:
        from app.core.agent import agent_graph_app
        from langchain_core.messages import HumanMessage

        # Test with a simple input
        human_message = HumanMessage(content="What is artificial intelligence?")
        inputs = {"messages": [human_message]}

        print("🧪 Testing agent with input: 'What is artificial intelligence?'")

        final_state = {}
        for s in agent_graph_app.stream(inputs):
            final_state.update(s)
            print(f"📊 Agent state update: {list(s.keys())}")

        print("✅ Agent execution completed")
        print(f"📋 Final state keys: {list(final_state.keys())}")

        # Check if we got a proper response
        if 'agent_outcome' in final_state:
            outcome = final_state['agent_outcome']
            if hasattr(outcome, 'return_values'):
                print(f"🎯 Agent response: {outcome.return_values.get('output', 'No output')[:100]}...")

        return True

    except Exception as e:
        print(f"❌ Agent test error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("🚀 Starting Phase 1 Tests")
    print("=" * 50)
    
    # Test imports
    if not test_imports():
        print("❌ Import tests failed")
        return False
    
    print()
    
    # Test agent functionality
    if not test_agent_basic():
        print("❌ Agent tests failed")
        return False
    
    print()
    print("🎉 All Phase 1 tests passed!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
