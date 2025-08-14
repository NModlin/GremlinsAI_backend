# app/services/chat_history.py
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_
from sqlalchemy.orm import selectinload
import json
import uuid
from datetime import datetime

from app.database.models import Conversation, Message
from app.database.database import AsyncSessionLocal


class ChatHistoryService:
    """Service for managing chat conversations and messages."""

    @staticmethod
    async def create_conversation(
        db: AsyncSession,
        title: Optional[str] = None,
        initial_message: Optional[str] = None
    ) -> Conversation:
        """Create a new conversation."""
        conversation = Conversation(
            id=str(uuid.uuid4()),
            title=title or "New Conversation",
            is_active=True
        )
        
        db.add(conversation)
        await db.flush()  # Get the ID without committing
        
        # Add initial message if provided
        if initial_message:
            await ChatHistoryService.add_message(
                db=db,
                conversation_id=conversation.id,
                role="user",
                content=initial_message
            )
        
        await db.commit()
        await db.refresh(conversation)
        return conversation

    @staticmethod
    async def get_conversation(
        db: AsyncSession,
        conversation_id: str,
        include_messages: bool = True
    ) -> Optional[Conversation]:
        """Get a conversation by ID."""
        query = select(Conversation).where(Conversation.id == conversation_id)
        
        if include_messages:
            query = query.options(selectinload(Conversation.messages))
        
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_conversations(
        db: AsyncSession,
        limit: int = 50,
        offset: int = 0,
        active_only: bool = True
    ) -> List[Conversation]:
        """Get a list of conversations."""
        query = select(Conversation)
        
        if active_only:
            query = query.where(Conversation.is_active == True)
        
        query = query.order_by(desc(Conversation.updated_at)).limit(limit).offset(offset)
        
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def update_conversation(
        db: AsyncSession,
        conversation_id: str,
        title: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Optional[Conversation]:
        """Update a conversation."""
        conversation = await ChatHistoryService.get_conversation(
            db, conversation_id, include_messages=False
        )
        
        if not conversation:
            return None
        
        if title is not None:
            conversation.title = title
        
        if is_active is not None:
            conversation.is_active = is_active
        
        await db.commit()
        await db.refresh(conversation)
        return conversation

    @staticmethod
    async def delete_conversation(
        db: AsyncSession,
        conversation_id: str,
        soft_delete: bool = True
    ) -> bool:
        """Delete a conversation (soft delete by default)."""
        conversation = await ChatHistoryService.get_conversation(
            db, conversation_id, include_messages=False
        )
        
        if not conversation:
            return False
        
        if soft_delete:
            conversation.is_active = False
            await db.commit()
        else:
            await db.delete(conversation)
            await db.commit()
        
        return True

    @staticmethod
    async def add_message(
        db: AsyncSession,
        conversation_id: str,
        role: str,
        content: str,
        tool_calls: Optional[Dict[str, Any]] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Message]:
        """Add a message to a conversation."""
        # Verify conversation exists
        conversation = await ChatHistoryService.get_conversation(
            db, conversation_id, include_messages=False
        )
        
        if not conversation:
            return None
        
        message = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role=role,
            content=content,
            tool_calls=json.dumps(tool_calls) if tool_calls else None,
            extra_data=json.dumps(extra_data) if extra_data else None
        )
        
        db.add(message)
        
        # Update conversation's updated_at timestamp
        conversation.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(message)
        return message

    @staticmethod
    async def get_messages(
        db: AsyncSession,
        conversation_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Message]:
        """Get messages for a conversation."""
        query = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
            .limit(limit)
            .offset(offset)
        )
        
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_conversation_context(
        db: AsyncSession,
        conversation_id: str,
        max_messages: int = 20
    ) -> List[Dict[str, Any]]:
        """Get conversation context for AI agents."""
        messages = await ChatHistoryService.get_messages(
            db, conversation_id, limit=max_messages
        )
        
        context = []
        for message in messages:
            msg_dict = {
                "role": message.role,
                "content": message.content,
                "created_at": message.created_at.isoformat()
            }
            
            if message.tool_calls:
                try:
                    msg_dict["tool_calls"] = json.loads(message.tool_calls)
                except json.JSONDecodeError:
                    pass
            
            if message.extra_data:
                try:
                    msg_dict["extra_data"] = json.loads(message.extra_data)
                except json.JSONDecodeError:
                    pass
            
            context.append(msg_dict)
        
        return context
