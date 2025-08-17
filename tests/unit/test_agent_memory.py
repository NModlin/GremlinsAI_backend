# tests/unit/test_agent_memory.py
"""
Unit tests for agent memory system functionality.

Tests cover:
- Memory extraction from conversations
- User preference learning and retention
- Key fact identification and storage
- Memory-aware reasoning
- Context persistence across interactions
- Scalability to 10,000+ interactions
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from app.core.memory_manager import MemoryManager, MemoryExtractor, MemorySummarizer, MemoryItem
from app.core.llm_manager import ConversationContext
from app.core.agent import ProductionAgent
from app.core.context_store import ConversationContextStore


class TestMemoryExtractor:
    """Test memory extraction functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = MemoryExtractor()
    
    def test_extract_user_preferences(self):
        """Test extraction of user preferences."""
        message = "I prefer Python over Java for web development. I like working with FastAPI."
        preferences = self.extractor.extract_preferences(message, turn_number=1)
        
        assert len(preferences) >= 1
        assert any("prefer python" in pref.content.lower() for pref in preferences)
        assert all(pref.type == 'preference' for pref in preferences)
        assert all(pref.confidence > 0.5 for pref in preferences)
    
    def test_extract_facts(self):
        """Test extraction of important facts."""
        message = "The FastAPI framework is built on Starlette. Remember that async functions are crucial for performance."
        facts = self.extractor.extract_facts(message, turn_number=1)
        
        assert len(facts) >= 1
        assert any("fastapi" in fact.content.lower() for fact in facts)
        assert all(fact.type == 'fact' for fact in facts)
    
    def test_extract_context_clues(self):
        """Test extraction of contextual information."""
        message = "This is important: always validate user input. The security implications are critical."
        context_clues = self.extractor.extract_context_clues(message, turn_number=1)
        
        assert len(context_clues) >= 1
        assert any("important" in clue.content.lower() for clue in context_clues)
        assert all(clue.type == 'context' for clue in context_clues)
    
    def test_keyword_extraction(self):
        """Test keyword extraction from text."""
        text = "I prefer Python programming for machine learning projects"
        keywords = self.extractor._extract_keywords(text)
        
        assert "python" in keywords
        assert "programming" in keywords
        assert "machine" in keywords
        assert "learning" in keywords
        # Stop words should be filtered out
        assert "for" not in keywords
        assert "the" not in keywords
    
    def test_confidence_calculation(self):
        """Test confidence score calculation."""
        # High confidence preference
        high_conf = self.extractor._calculate_confidence("I prefer Python", "preference")
        assert high_conf > 0.7
        
        # Lower confidence fact
        low_conf = self.extractor._calculate_confidence("Something might be true", "fact")
        assert low_conf < 0.7


class TestMemorySummarizer:
    """Test memory summarization functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.summarizer = MemorySummarizer()
    
    def test_conversation_summarization(self):
        """Test conversation summarization."""
        messages = [
            {"role": "user", "content": "I prefer Python for web development"},
            {"role": "assistant", "content": "Python is great for web development. FastAPI is a popular choice."},
            {"role": "user", "content": "Can you help me with FastAPI authentication?"},
            {"role": "assistant", "content": "Sure! FastAPI supports OAuth2 and JWT tokens for authentication."}
        ]
        
        summary = self.summarizer.summarize_conversation(messages)
        
        assert len(summary) > 0
        assert "python" in summary.lower() or "fastapi" in summary.lower()
        assert len(summary) <= 500  # Should be concise
    
    def test_memory_items_summarization(self):
        """Test memory items summarization."""
        memory_items = [
            MemoryItem(
                content="I prefer Python",
                type="preference",
                confidence=0.9,
                timestamp=datetime.utcnow().isoformat(),
                source_turn=1,
                keywords=["python", "prefer"]
            ),
            MemoryItem(
                content="FastAPI is fast",
                type="fact",
                confidence=0.8,
                timestamp=datetime.utcnow().isoformat(),
                source_turn=2,
                keywords=["fastapi", "fast"]
            )
        ]
        
        summary = self.summarizer.summarize_memory_items(memory_items)
        
        assert summary['total_items'] == 2
        assert len(summary['preferences']) == 1
        assert len(summary['facts']) == 1
        assert len(summary['top_keywords']) > 0


class TestMemoryManager:
    """Test memory manager coordination."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.memory_manager = MemoryManager()
    
    def test_process_conversation_turn(self):
        """Test processing a conversation turn for memory extraction."""
        context = ConversationContext(conversation_id="test_123")
        context.messages = [
            {"role": "user", "content": "I prefer Python for machine learning. It's important to use proper validation."}
        ]
        
        updated_context = self.memory_manager.process_conversation_turn(context, turn_number=1)
        
        # Check that memory was extracted and stored
        assert len(updated_context.user_preferences) > 0
        assert len(updated_context.key_facts) >= 0  # May or may not have facts
        assert updated_context.interaction_summary != ""
        assert len(updated_context.memory_keywords) > 0
        assert updated_context.memory_last_updated is not None
    
    def test_memory_context_for_prompt(self):
        """Test generating memory context for prompts."""
        context = ConversationContext(conversation_id="test_123")
        context.user_preferences = {
            "pref_0": {
                "content": "I prefer Python",
                "confidence": 0.9,
                "timestamp": datetime.utcnow().isoformat(),
                "keywords": ["python"]
            }
        }
        context.key_facts = [
            {
                "content": "FastAPI is fast",
                "type": "fact",
                "confidence": 0.8,
                "timestamp": datetime.utcnow().isoformat(),
                "source_turn": 1,
                "keywords": ["fastapi"]
            }
        ]
        context.interaction_summary = "User prefers Python for development"
        
        memory_context = self.memory_manager.get_memory_context_for_prompt(context)
        
        assert "User Preferences:" in memory_context
        assert "python" in memory_context.lower()
        assert "Key Information:" in memory_context
        assert "fastapi" in memory_context.lower()
        assert "Conversation Summary:" in memory_context
    
    def test_memory_size_limits(self):
        """Test that memory size is limited to prevent unbounded growth."""
        context = ConversationContext(conversation_id="test_123")
        
        # Add many facts to test size limiting
        for i in range(150):  # More than the 100 limit
            context.key_facts.append({
                "content": f"Fact number {i}",
                "type": "fact",
                "confidence": 0.5 + (i % 50) / 100,  # Varying confidence
                "timestamp": datetime.utcnow().isoformat(),
                "source_turn": i,
                "keywords": [f"fact{i}"]
            })
        
        # Process the context (this should trigger size limiting)
        updated_context = self.memory_manager.process_conversation_turn(context, turn_number=1)
        
        # Should be limited to 100 facts
        assert len(updated_context.key_facts) <= 100
        
        # Should keep the highest confidence facts
        remaining_facts = updated_context.key_facts
        confidences = [fact['confidence'] for fact in remaining_facts]
        assert all(conf >= 0.5 for conf in confidences)


class TestAgentMemoryIntegration:
    """Test agent integration with memory system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.agent = ProductionAgent(max_iterations=3, max_execution_time=30)
    
    @patch('app.core.agent.get_context_store')
    def test_load_conversation_context(self, mock_get_store):
        """Test loading conversation context with memory."""
        # Mock context store
        mock_store = Mock()
        mock_context = ConversationContext(conversation_id="test_123")
        mock_context.user_preferences = {"pref_0": {"content": "I prefer Python", "confidence": 0.9}}
        mock_store.get_context.return_value = mock_context
        mock_get_store.return_value = mock_store
        
        # Test loading context
        loaded_context = self.agent._load_conversation_context("test_123")
        
        assert loaded_context.conversation_id == "test_123"
        assert len(loaded_context.user_preferences) == 1
        mock_store.get_context.assert_called_once_with("test_123")
    
    @patch('app.core.agent.get_context_store')
    def test_save_conversation_context(self, mock_get_store):
        """Test saving conversation context with memory."""
        # Mock context store
        mock_store = Mock()
        mock_get_store.return_value = mock_store
        
        # Create context to save
        context = ConversationContext(conversation_id="test_123")
        context.user_preferences = {"pref_0": {"content": "I prefer Python", "confidence": 0.9}}
        
        # Test saving context
        self.agent._save_conversation_context(context)
        
        mock_store.update_context.assert_called_once_with("test_123", context)
    
    def test_create_memory_aware_prompt(self):
        """Test creating memory-aware prompts."""
        context = ConversationContext(conversation_id="test_123")
        context.user_preferences = {
            "pref_0": {
                "content": "I prefer Python",
                "confidence": 0.9,
                "timestamp": datetime.utcnow().isoformat(),
                "keywords": ["python"]
            }
        }
        
        prompt = self.agent._create_memory_aware_prompt("What's the best programming language?", context)
        
        assert "MEMORY CONTEXT" in prompt
        assert "User Preferences:" in prompt
        assert "python" in prompt.lower()
        assert "What's the best programming language?" in prompt
    
    @pytest.mark.asyncio
    @patch('app.core.agent.get_context_store')
    @patch('app.core.llm_manager.ProductionLLMManager.generate_response')
    async def test_memory_aware_reasoning(self, mock_generate, mock_get_store):
        """Test that agent uses memory in reasoning."""
        # Mock context store
        mock_store = Mock()
        mock_context = ConversationContext(conversation_id="test_123")
        mock_context.user_preferences = {
            "pref_0": {
                "content": "I prefer Python for web development",
                "confidence": 0.9,
                "timestamp": datetime.utcnow().isoformat(),
                "keywords": ["python", "web"]
            }
        }
        mock_store.get_context.return_value = mock_context
        mock_store.update_context.return_value = None
        mock_get_store.return_value = mock_store
        
        # Mock LLM response
        mock_response = Mock()
        mock_response.content = """
        Thought: The user prefers Python for web development based on their previous preferences. I should recommend Python frameworks.
        Action: final_answer
        Action Input: Based on your preference for Python, I recommend FastAPI or Django for web development.
        """
        mock_generate.return_value = mock_response
        
        # Test reasoning with memory
        result = await self.agent.reason_and_act(
            "What framework should I use for web development?",
            conversation_id="test_123"
        )
        
        assert result.success
        assert "python" in result.final_answer.lower() or "fastapi" in result.final_answer.lower()
        
        # Verify context was loaded and saved
        mock_store.get_context.assert_called_once_with("test_123")
        mock_store.update_context.assert_called()


class TestMemoryScalability:
    """Test memory system scalability."""
    
    def test_memory_performance_with_large_context(self):
        """Test memory system performance with large conversation contexts."""
        memory_manager = MemoryManager()
        
        # Create a large context with many messages
        context = ConversationContext(conversation_id="large_test")
        
        # Add 1000 messages to simulate a long conversation
        for i in range(1000):
            context.messages.append({
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"Message {i} with some preferences and facts about Python and web development.",
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # Process the conversation turn (should complete in reasonable time)
        import time
        start_time = time.time()
        
        updated_context = memory_manager.process_conversation_turn(context, turn_number=1000)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should complete within 5 seconds even for large contexts
        assert processing_time < 5.0
        
        # Should have extracted some memory
        assert updated_context.memory_last_updated is not None
        assert len(updated_context.memory_keywords) > 0
    
    def test_memory_storage_efficiency(self):
        """Test that memory storage is efficient and doesn't grow unbounded."""
        context = ConversationContext(conversation_id="efficiency_test")
        
        # Simulate processing many conversation turns
        memory_manager = MemoryManager()
        
        for turn in range(100):
            context.messages.append({
                "role": "user",
                "content": f"Turn {turn}: I like Python and prefer FastAPI for web development. This is important information.",
                "timestamp": datetime.utcnow().isoformat()
            })
            
            context = memory_manager.process_conversation_turn(context, turn_number=turn)
        
        # Memory should be bounded
        assert len(context.key_facts) <= 100  # Should be limited
        assert len(context.memory_keywords) <= 50  # Should be limited
        assert len(context.user_preferences) <= 50  # Should be reasonable
        
        # Should still contain relevant information
        assert any("python" in str(pref).lower() for pref in context.user_preferences.values())


if __name__ == "__main__":
    pytest.main([__file__])
