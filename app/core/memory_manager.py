# app/core/memory_manager.py
"""
Memory management system for agent learning and context retention.

This module provides:
- Memory extraction from conversations
- Key fact identification and storage
- User preference learning
- Conversation summarization
- Memory-aware context management
"""

import re
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict

from app.core.llm_manager import ConversationContext

logger = logging.getLogger(__name__)


@dataclass
class MemoryItem:
    """Individual memory item with metadata."""
    content: str
    type: str  # 'preference', 'fact', 'context'
    confidence: float  # 0.0 to 1.0
    timestamp: str
    source_turn: int
    keywords: List[str]


class MemoryExtractor:
    """Extract key information and preferences from conversations."""
    
    def __init__(self):
        # Patterns for identifying user preferences
        self.preference_patterns = [
            r"I (?:prefer|like|love|enjoy|want|need) (.+)",
            r"My favorite (.+) is (.+)",
            r"I (?:don't|do not) like (.+)",
            r"I (?:always|usually|often) (.+)",
            r"I (?:never|rarely|seldom) (.+)",
            r"I am (?:a|an) (.+)",
            r"I work (?:as|in|at) (.+)",
            r"My (?:job|role|position) is (.+)",
            r"I live in (.+)",
            r"I speak (.+)",
            r"I use (.+) (?:programming language|framework|tool)",
        ]
        
        # Patterns for identifying important facts
        self.fact_patterns = [
            r"(?:The|This|That) (.+) is (.+)",
            r"(.+) (?:means|refers to|is defined as) (.+)",
            r"(?:Remember|Note) that (.+)",
            r"(?:Important|Key|Critical): (.+)",
            r"(.+) (?:works|functions) by (.+)",
        ]
        
        # Keywords that indicate important information
        self.importance_keywords = [
            'important', 'critical', 'key', 'essential', 'vital', 'crucial',
            'remember', 'note', 'warning', 'caution', 'alert',
            'prefer', 'like', 'love', 'hate', 'dislike', 'favorite',
            'always', 'never', 'usually', 'often', 'rarely', 'seldom'
        ]
    
    def extract_preferences(self, message: str, turn_number: int) -> List[MemoryItem]:
        """Extract user preferences from a message."""
        preferences = []
        message_lower = message.lower()
        
        for pattern in self.preference_patterns:
            matches = re.finditer(pattern, message_lower, re.IGNORECASE)
            for match in matches:
                content = match.group(0)
                keywords = self._extract_keywords(content)
                confidence = self._calculate_confidence(content, 'preference')
                
                preference = MemoryItem(
                    content=content,
                    type='preference',
                    confidence=confidence,
                    timestamp=datetime.utcnow().isoformat(),
                    source_turn=turn_number,
                    keywords=keywords
                )
                preferences.append(preference)
        
        return preferences
    
    def extract_facts(self, message: str, turn_number: int) -> List[MemoryItem]:
        """Extract important facts from a message."""
        facts = []
        message_lower = message.lower()
        
        for pattern in self.fact_patterns:
            matches = re.finditer(pattern, message_lower, re.IGNORECASE)
            for match in matches:
                content = match.group(0)
                keywords = self._extract_keywords(content)
                confidence = self._calculate_confidence(content, 'fact')
                
                fact = MemoryItem(
                    content=content,
                    type='fact',
                    confidence=confidence,
                    timestamp=datetime.utcnow().isoformat(),
                    source_turn=turn_number,
                    keywords=keywords
                )
                facts.append(fact)
        
        return facts
    
    def extract_context_clues(self, message: str, turn_number: int) -> List[MemoryItem]:
        """Extract contextual information that might be useful later."""
        context_items = []
        
        # Look for sentences with importance keywords
        sentences = re.split(r'[.!?]+', message)
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            sentence_lower = sentence.lower()
            importance_score = sum(1 for keyword in self.importance_keywords 
                                 if keyword in sentence_lower)
            
            if importance_score > 0:
                keywords = self._extract_keywords(sentence)
                confidence = min(0.9, importance_score * 0.3)
                
                context_item = MemoryItem(
                    content=sentence,
                    type='context',
                    confidence=confidence,
                    timestamp=datetime.utcnow().isoformat(),
                    source_turn=turn_number,
                    keywords=keywords
                )
                context_items.append(context_item)
        
        return context_items
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text for semantic search."""
        # Simple keyword extraction - remove common words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those'
        }
        
        words = re.findall(r'\b\w+\b', text.lower())
        keywords = [word for word in words if len(word) > 2 and word not in stop_words]
        return keywords[:10]  # Limit to top 10 keywords
    
    def _calculate_confidence(self, content: str, memory_type: str) -> float:
        """Calculate confidence score for a memory item."""
        base_confidence = 0.5
        
        # Boost confidence for explicit statements
        explicit_indicators = ['i prefer', 'i like', 'i love', 'i hate', 'i always', 'i never']
        if any(indicator in content.lower() for indicator in explicit_indicators):
            base_confidence += 0.3
        
        # Boost confidence for definitive statements
        definitive_indicators = ['is', 'are', 'means', 'refers to']
        if any(indicator in content.lower() for indicator in definitive_indicators):
            base_confidence += 0.2
        
        # Adjust based on memory type
        if memory_type == 'preference':
            base_confidence += 0.1
        elif memory_type == 'fact':
            base_confidence += 0.05
        
        return min(1.0, base_confidence)


class MemorySummarizer:
    """Create concise summaries of conversations and memory items."""
    
    def summarize_conversation(self, messages: List[Dict[str, Any]]) -> str:
        """Create a concise summary of the conversation."""
        if not messages:
            return ""
        
        # Extract key topics and themes
        all_content = []
        for msg in messages:
            if msg.get('role') == 'user':
                all_content.append(f"User: {msg.get('content', '')}")
            elif msg.get('role') == 'assistant':
                all_content.append(f"Assistant: {msg.get('content', '')}")
        
        # Simple summarization - take key sentences
        combined_text = " ".join(all_content)
        sentences = re.split(r'[.!?]+', combined_text)
        
        # Filter for important sentences
        important_sentences = []
        importance_keywords = [
            'prefer', 'like', 'need', 'want', 'important', 'key', 'remember',
            'problem', 'solution', 'help', 'question', 'answer'
        ]
        
        for sentence in sentences[:20]:  # Limit to first 20 sentences
            sentence = sentence.strip()
            if len(sentence) > 10:
                sentence_lower = sentence.lower()
                if any(keyword in sentence_lower for keyword in importance_keywords):
                    important_sentences.append(sentence)
        
        # Create summary
        if important_sentences:
            summary = ". ".join(important_sentences[:5])  # Top 5 important sentences
            return summary[:500] + "..." if len(summary) > 500 else summary
        else:
            # Fallback: use first few sentences
            first_sentences = [s.strip() for s in sentences[:3] if s.strip()]
            summary = ". ".join(first_sentences)
            return summary[:300] + "..." if len(summary) > 300 else summary
    
    def summarize_memory_items(self, memory_items: List[MemoryItem]) -> Dict[str, Any]:
        """Create a structured summary of memory items."""
        summary = {
            'total_items': len(memory_items),
            'preferences': [],
            'facts': [],
            'context': [],
            'top_keywords': []
        }
        
        # Group by type
        for item in memory_items:
            if item.type == 'preference':
                summary['preferences'].append({
                    'content': item.content,
                    'confidence': item.confidence
                })
            elif item.type == 'fact':
                summary['facts'].append({
                    'content': item.content,
                    'confidence': item.confidence
                })
            elif item.type == 'context':
                summary['context'].append({
                    'content': item.content,
                    'confidence': item.confidence
                })
        
        # Extract top keywords
        all_keywords = []
        for item in memory_items:
            all_keywords.extend(item.keywords)
        
        keyword_counts = {}
        for keyword in all_keywords:
            keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
        
        summary['top_keywords'] = sorted(keyword_counts.items(), 
                                       key=lambda x: x[1], reverse=True)[:10]
        
        return summary


class MemoryManager:
    """Coordinate memory operations and integration with ConversationContext."""
    
    def __init__(self):
        self.extractor = MemoryExtractor()
        self.summarizer = MemorySummarizer()
    
    def process_conversation_turn(self, context: ConversationContext, 
                                turn_number: int) -> ConversationContext:
        """Process a conversation turn and extract memory information."""
        if not context.messages:
            return context
        
        # Get the latest user message
        latest_message = None
        for msg in reversed(context.messages):
            if msg.get('role') == 'user':
                latest_message = msg
                break
        
        if not latest_message:
            return context
        
        message_content = latest_message.get('content', '')
        
        # Extract memory items
        preferences = self.extractor.extract_preferences(message_content, turn_number)
        facts = self.extractor.extract_facts(message_content, turn_number)
        context_clues = self.extractor.extract_context_clues(message_content, turn_number)
        
        # Update context with new memory items
        self._update_context_memory(context, preferences, facts, context_clues)
        
        # Update conversation summary
        context.interaction_summary = self.summarizer.summarize_conversation(context.messages)
        
        # Update memory keywords
        all_memory_items = preferences + facts + context_clues
        all_keywords = []
        for item in all_memory_items:
            all_keywords.extend(item.keywords)
        
        # Merge with existing keywords
        existing_keywords = set(context.memory_keywords)
        new_keywords = set(all_keywords)
        context.memory_keywords = list(existing_keywords.union(new_keywords))[:50]  # Limit to 50
        
        # Update timestamp
        context.memory_last_updated = datetime.utcnow().isoformat()
        
        return context
    
    def _update_context_memory(self, context: ConversationContext,
                             preferences: List[MemoryItem],
                             facts: List[MemoryItem],
                             context_clues: List[MemoryItem]):
        """Update context with extracted memory items."""
        # Update preferences
        for pref in preferences:
            pref_key = f"pref_{len(context.user_preferences)}"
            context.user_preferences[pref_key] = {
                'content': pref.content,
                'confidence': pref.confidence,
                'timestamp': pref.timestamp,
                'keywords': pref.keywords
            }
        
        # Update facts (maintain as list with metadata)
        for fact in facts:
            fact_dict = asdict(fact)
            context.key_facts.append(fact_dict)
        
        # Update context clues (add to facts with lower priority)
        for clue in context_clues:
            if clue.confidence > 0.5:  # Only store high-confidence context
                clue_dict = asdict(clue)
                context.key_facts.append(clue_dict)
        
        # Limit memory size to prevent unbounded growth
        if len(context.key_facts) > 100:
            # Keep only the most confident and recent facts
            context.key_facts.sort(key=lambda x: (x['confidence'], x['timestamp']), reverse=True)
            context.key_facts = context.key_facts[:100]
    
    def get_memory_context_for_prompt(self, context: ConversationContext) -> str:
        """Generate memory context string for inclusion in prompts."""
        if not context.user_preferences and not context.key_facts:
            return ""
        
        memory_parts = []
        
        # Add user preferences
        if context.user_preferences:
            memory_parts.append("User Preferences:")
            for pref_key, pref_data in context.user_preferences.items():
                if pref_data['confidence'] > 0.6:  # Only include high-confidence preferences
                    memory_parts.append(f"- {pref_data['content']}")
        
        # Add key facts
        if context.key_facts:
            high_confidence_facts = [f for f in context.key_facts if f['confidence'] > 0.6]
            if high_confidence_facts:
                memory_parts.append("\nKey Information:")
                for fact in high_confidence_facts[:10]:  # Limit to top 10 facts
                    memory_parts.append(f"- {fact['content']}")
        
        # Add conversation summary
        if context.interaction_summary:
            memory_parts.append(f"\nConversation Summary: {context.interaction_summary}")
        
        return "\n".join(memory_parts)
