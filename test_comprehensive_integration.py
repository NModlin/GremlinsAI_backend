#!/usr/bin/env python3
"""
Comprehensive end-to-end integration testing for Phase 1 and Phase 2.
This script tests all functionality and integration between phases.
"""

import sys
import os
import asyncio
import requests
import json
import time
import subprocess
from typing import Optional, Dict, Any

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

class ComprehensiveTestSuite:
    """Comprehensive test suite for Phase 1 and Phase 2 integration."""
    
    def __init__(self):
        self.server_process: Optional[subprocess.Popen] = None
        self.base_url = "http://127.0.0.1:8000"
        self.test_conversation_id: Optional[str] = None
        self.test_results = {
            "phase1": {"passed": 0, "failed": 0, "tests": []},
            "phase2": {"passed": 0, "failed": 0, "tests": []},
            "integration": {"passed": 0, "failed": 0, "tests": []}
        }
    
    def log_test(self, phase: str, test_name: str, passed: bool, details: str = ""):
        """Log test result."""
        self.test_results[phase]["tests"].append({
            "name": test_name,
            "passed": passed,
            "details": details
        })
        if passed:
            self.test_results[phase]["passed"] += 1
            print(f"✅ {test_name}")
        else:
            self.test_results[phase]["failed"] += 1
            print(f"❌ {test_name}: {details}")
    
    async def test_phase1_imports(self):
        """Test Phase 1 imports and basic functionality."""
        try:
            from app.core.tools import duckduckgo_search
            from app.core.agent import agent_graph_app
            from app.api.v1.endpoints.agent import router
            from app.main import app
            self.log_test("phase1", "Phase 1 imports", True)
            return True
        except Exception as e:
            self.log_test("phase1", "Phase 1 imports", False, str(e))
            return False
    
    async def test_phase1_agent_functionality(self):
        """Test Phase 1 agent core functionality."""
        try:
            from app.core.agent import agent_graph_app
            from langchain_core.messages import HumanMessage
            
            # Test agent execution
            human_message = HumanMessage(content="What is machine learning?")
            inputs = {"messages": [human_message]}
            
            final_state = {}
            for s in agent_graph_app.stream(inputs):
                final_state.update(s)
            
            # Verify agent outcome
            if "agent_outcome" in final_state:
                outcome = final_state["agent_outcome"]
                if hasattr(outcome, 'return_values'):
                    self.log_test("phase1", "Agent core functionality", True)
                    return True
            
            self.log_test("phase1", "Agent core functionality", False, "No valid agent outcome")
            return False
            
        except Exception as e:
            self.log_test("phase1", "Agent core functionality", False, str(e))
            return False
    
    async def test_phase2_imports(self):
        """Test Phase 2 imports and database setup."""
        try:
            from app.database.database import get_db, AsyncSessionLocal, ensure_data_directory
            from app.database.models import Conversation, Message
            from app.services.chat_history import ChatHistoryService
            from app.api.v1.schemas.chat_history import ConversationCreate
            
            # Ensure database setup
            ensure_data_directory()
            
            self.log_test("phase2", "Phase 2 imports and database setup", True)
            return True
        except Exception as e:
            self.log_test("phase2", "Phase 2 imports and database setup", False, str(e))
            return False
    
    async def test_phase2_database_operations(self):
        """Test Phase 2 database CRUD operations."""
        try:
            from app.database.database import AsyncSessionLocal
            from app.services.chat_history import ChatHistoryService
            
            async with AsyncSessionLocal() as db:
                # Create conversation
                conversation = await ChatHistoryService.create_conversation(
                    db=db,
                    title="Integration Test Conversation",
                    initial_message="Testing database operations"
                )
                
                # Store for later tests
                self.test_conversation_id = conversation.id
                
                # Add message
                message = await ChatHistoryService.add_message(
                    db=db,
                    conversation_id=conversation.id,
                    role="assistant",
                    content="Database operations working correctly"
                )
                
                # Retrieve conversation
                retrieved = await ChatHistoryService.get_conversation(
                    db=db,
                    conversation_id=conversation.id,
                    include_messages=True
                )
                
                # Verify data integrity
                if (retrieved and 
                    retrieved.title == "Integration Test Conversation" and
                    len(retrieved.messages) >= 2):
                    self.log_test("phase2", "Database CRUD operations", True)
                    return True
                else:
                    self.log_test("phase2", "Database CRUD operations", False, "Data integrity check failed")
                    return False
                    
        except Exception as e:
            self.log_test("phase2", "Database CRUD operations", False, str(e))
            return False
    
    def start_server(self):
        """Start the FastAPI server for API testing."""
        try:
            self.server_process = subprocess.Popen([
                sys.executable, "-m", "uvicorn", 
                "app.main:app", 
                "--host", "127.0.0.1", 
                "--port", "8000"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Wait for server to start
            time.sleep(5)
            
            # Test server is responding
            response = requests.get(f"{self.base_url}/")
            if response.status_code == 200:
                self.log_test("integration", "Server startup", True)
                return True
            else:
                self.log_test("integration", "Server startup", False, f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("integration", "Server startup", False, str(e))
            return False
    
    def stop_server(self):
        """Stop the FastAPI server."""
        if self.server_process:
            self.server_process.terminate()
            self.server_process.wait()
    
    def test_phase1_api_endpoints(self):
        """Test Phase 1 API endpoints."""
        try:
            # Test root endpoint
            response = requests.get(f"{self.base_url}/")
            if response.status_code != 200:
                self.log_test("phase1", "Root endpoint", False, f"Status: {response.status_code}")
                return False
            
            root_data = response.json()
            if "message" in root_data:
                self.log_test("phase1", "Root endpoint", True)
            else:
                self.log_test("phase1", "Root endpoint", False, "Invalid response format")
                return False
            
            # Test original agent invoke endpoint
            agent_payload = {"input": "What is artificial intelligence?"}
            response = requests.post(
                f"{self.base_url}/api/v1/agent/invoke",
                json=agent_payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                agent_data = response.json()
                if "output" in agent_data:
                    self.log_test("phase1", "Agent invoke endpoint", True)
                    return True
                else:
                    self.log_test("phase1", "Agent invoke endpoint", False, "Invalid response format")
                    return False
            else:
                self.log_test("phase1", "Agent invoke endpoint", False, f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("phase1", "API endpoints", False, str(e))
            return False
    
    def test_phase2_api_endpoints(self):
        """Test Phase 2 API endpoints."""
        try:
            # Test conversation creation
            conv_payload = {
                "title": "API Test Conversation",
                "initial_message": "Testing Phase 2 API"
            }
            
            response = requests.post(
                f"{self.base_url}/api/v1/history/conversations",
                json=conv_payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code != 201:
                self.log_test("phase2", "Conversation creation API", False, f"Status: {response.status_code}")
                return False
            
            conversation = response.json()
            conversation_id = conversation["id"]
            self.log_test("phase2", "Conversation creation API", True)
            
            # Test conversation retrieval
            response = requests.get(f"{self.base_url}/api/v1/history/conversations/{conversation_id}")
            if response.status_code != 200:
                self.log_test("phase2", "Conversation retrieval API", False, f"Status: {response.status_code}")
                return False
            
            self.log_test("phase2", "Conversation retrieval API", True)
            
            # Test message addition
            msg_payload = {
                "conversation_id": conversation_id,
                "role": "user",
                "content": "API test message"
            }
            
            response = requests.post(
                f"{self.base_url}/api/v1/history/messages",
                json=msg_payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code != 201:
                self.log_test("phase2", "Message creation API", False, f"Status: {response.status_code}")
                return False
            
            self.log_test("phase2", "Message creation API", True)
            
            # Test conversation listing
            response = requests.get(f"{self.base_url}/api/v1/history/conversations")
            if response.status_code != 200:
                self.log_test("phase2", "Conversation listing API", False, f"Status: {response.status_code}")
                return False
            
            conv_list = response.json()
            if "conversations" in conv_list and len(conv_list["conversations"]) > 0:
                self.log_test("phase2", "Conversation listing API", True)
            else:
                self.log_test("phase2", "Conversation listing API", False, "No conversations returned")
                return False
            
            return True

        except Exception as e:
            self.log_test("phase2", "API endpoints", False, str(e))
            return False

    def test_integration_agent_chat(self):
        """Test integration between Phase 1 agent and Phase 2 chat history."""
        try:
            # Test new agent chat endpoint (Phase 2)
            chat_payload = {
                "input": "What is machine learning?",
                "save_conversation": True
            }

            response = requests.post(
                f"{self.base_url}/api/v1/agent/chat",
                json=chat_payload,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code != 200:
                self.log_test("integration", "Agent chat endpoint", False, f"Status: {response.status_code}")
                return False

            chat_response = response.json()
            if "conversation_id" not in chat_response:
                self.log_test("integration", "Agent chat endpoint", False, "No conversation_id in response")
                return False

            conversation_id = chat_response["conversation_id"]
            self.log_test("integration", "Agent chat endpoint", True)

            # Test follow-up with context
            followup_payload = {
                "input": "Can you explain that in simpler terms?",
                "conversation_id": conversation_id,
                "save_conversation": True
            }

            response = requests.post(
                f"{self.base_url}/api/v1/agent/chat",
                json=followup_payload,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code != 200:
                self.log_test("integration", "Agent context follow-up", False, f"Status: {response.status_code}")
                return False

            followup_response = response.json()
            if followup_response.get("context_used", False):
                self.log_test("integration", "Agent context follow-up", True)
            else:
                self.log_test("integration", "Agent context follow-up", False, "Context not used")
                return False

            # Verify conversation was saved
            response = requests.get(f"{self.base_url}/api/v1/history/conversations/{conversation_id}")
            if response.status_code != 200:
                self.log_test("integration", "Conversation persistence", False, f"Status: {response.status_code}")
                return False

            conversation = response.json()
            if len(conversation.get("messages", [])) >= 4:  # 2 user + 2 assistant messages
                self.log_test("integration", "Conversation persistence", True)
            else:
                self.log_test("integration", "Conversation persistence", False, "Messages not saved correctly")
                return False

            return True

        except Exception as e:
            self.log_test("integration", "Agent chat integration", False, str(e))
            return False

    def test_backward_compatibility(self):
        """Test that Phase 1 functionality still works with Phase 2."""
        try:
            # Test original agent endpoint still works
            original_payload = {"input": "Test backward compatibility"}
            response = requests.post(
                f"{self.base_url}/api/v1/agent/invoke",
                json=original_payload,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code != 200:
                self.log_test("integration", "Backward compatibility", False, f"Status: {response.status_code}")
                return False

            response_data = response.json()
            if "output" in response_data:
                self.log_test("integration", "Backward compatibility", True)
                return True
            else:
                self.log_test("integration", "Backward compatibility", False, "Invalid response format")
                return False

        except Exception as e:
            self.log_test("integration", "Backward compatibility", False, str(e))
            return False

    def test_error_handling(self):
        """Test error handling across both phases."""
        try:
            # Test invalid conversation ID
            response = requests.get(f"{self.base_url}/api/v1/history/conversations/invalid-id")
            if response.status_code == 404:
                self.log_test("integration", "Error handling - Invalid conversation", True)
            else:
                self.log_test("integration", "Error handling - Invalid conversation", False, f"Expected 404, got {response.status_code}")
                return False

            # Test invalid message payload
            invalid_msg = {
                "conversation_id": "invalid-id",
                "role": "user",
                "content": "Test message"
            }

            response = requests.post(
                f"{self.base_url}/api/v1/history/messages",
                json=invalid_msg,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 404:
                self.log_test("integration", "Error handling - Invalid message", True)
            else:
                self.log_test("integration", "Error handling - Invalid message", False, f"Expected 404, got {response.status_code}")
                return False

            return True

        except Exception as e:
            self.log_test("integration", "Error handling", False, str(e))
            return False

    def print_summary(self):
        """Print comprehensive test summary."""
        print("\n" + "="*80)
        print("🏁 COMPREHENSIVE TEST RESULTS SUMMARY")
        print("="*80)

        total_passed = 0
        total_failed = 0

        for phase, results in self.test_results.items():
            passed = results["passed"]
            failed = results["failed"]
            total = passed + failed

            total_passed += passed
            total_failed += failed

            print(f"\n📊 {phase.upper()} RESULTS:")
            print(f"   ✅ Passed: {passed}/{total}")
            print(f"   ❌ Failed: {failed}/{total}")

            if failed > 0:
                print(f"   Failed tests:")
                for test in results["tests"]:
                    if not test["passed"]:
                        print(f"      - {test['name']}: {test['details']}")

        print(f"\n🎯 OVERALL RESULTS:")
        print(f"   ✅ Total Passed: {total_passed}")
        print(f"   ❌ Total Failed: {total_failed}")
        print(f"   📈 Success Rate: {(total_passed/(total_passed+total_failed)*100):.1f}%")

        if total_failed == 0:
            print(f"\n🎉 ALL TESTS PASSED! Both phases are fully functional and integrated.")
        else:
            print(f"\n⚠️  Some tests failed. Please review the issues above.")

        return total_failed == 0

async def main():
    """Run comprehensive integration tests."""
    print("🚀 Starting Comprehensive Integration Testing")
    print("Testing Phase 1, Phase 2, and their integration")
    print("="*80)

    test_suite = ComprehensiveTestSuite()

    try:
        # Phase 1 Tests
        print("\n🔧 PHASE 1 TESTING")
        print("-" * 40)

        await test_suite.test_phase1_imports()
        await test_suite.test_phase1_agent_functionality()

        # Phase 2 Tests
        print("\n💾 PHASE 2 TESTING")
        print("-" * 40)

        await test_suite.test_phase2_imports()
        await test_suite.test_phase2_database_operations()

        # Start server for API tests
        print("\n🌐 API INTEGRATION TESTING")
        print("-" * 40)

        if not test_suite.start_server():
            print("❌ Failed to start server. Skipping API tests.")
            return False

        try:
            # Phase 1 API Tests
            test_suite.test_phase1_api_endpoints()

            # Phase 2 API Tests
            test_suite.test_phase2_api_endpoints()

            # Integration Tests
            print("\n🔗 INTEGRATION TESTING")
            print("-" * 40)

            test_suite.test_integration_agent_chat()
            test_suite.test_backward_compatibility()
            test_suite.test_error_handling()

        finally:
            test_suite.stop_server()

        # Print comprehensive summary
        success = test_suite.print_summary()
        return success

    except Exception as e:
        print(f"\n❌ Critical error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
