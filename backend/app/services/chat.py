"""Chat service connecting API layer to Core AI Runtime."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from backend.app.ai.contracts import ChatMessage, GenerationRequest, RuntimeContext
from backend.app.ai.runtime import CoreAIRuntime
from backend.app.core.config import get_settings
from backend.app.core.errors import ResourceNotFoundError, UnauthorizedAccessError, ValidationError
from backend.app.core.idempotency import check_idempotency_key
from backend.app.db.models import Agent, Conversation, Message

settings = get_settings()


class ChatService:
    """Service for managing conversations and messages."""

    def __init__(self, db: Session, runtime: CoreAIRuntime):
        self.db = db
        self.runtime = runtime

    def get_or_create_conversation(
        self,
        client_id: str,
        agent_id: str,
        conversation_id: Optional[str] = None,
        user_identifier: Optional[str] = None,
    ) -> Conversation:
        """
        Get existing conversation or create a new one.
        
        Validates:
        - Agent exists and belongs to client
        - If conversation_id provided, it exists and belongs to client
        """
        # Validate agent belongs to client
        agent = (
            self.db.query(Agent)
            .filter(Agent.id == agent_id, Agent.client_id == client_id)
            .first()
        )
        
        if not agent:
            raise ResourceNotFoundError("Agent", agent_id)
        
        if not agent.is_active:
            raise ValidationError(f"Agent {agent_id} is not active")
        
        # Get or create conversation
        if conversation_id:
            conversation = (
                self.db.query(Conversation)
                .filter(Conversation.id == conversation_id)
                .first()
            )
            
            if not conversation:
                raise ResourceNotFoundError("Conversation", conversation_id)
            
            # Verify conversation belongs to client
            if conversation.client_id != client_id:
                raise UnauthorizedAccessError("Conversation")
            
            # Verify conversation belongs to correct agent
            if conversation.agent_id != agent_id:
                raise ValidationError(
                    f"Conversation {conversation_id} belongs to different agent"
                )
            
            return conversation
        
        # Create new conversation
        new_conversation = Conversation(
            id=str(uuid.uuid4()),
            client_id=client_id,
            agent_id=agent_id,
            user_identifier=user_identifier,
        )
        self.db.add(new_conversation)
        self.db.commit()
        self.db.refresh(new_conversation)
        
        return new_conversation

    def get_conversation_history(
        self,
        conversation: Conversation,
        limit: Optional[int] = None,
    ) -> list[ChatMessage]:
        """
        Get conversation history as ChatMessage list.
        
        Args:
            conversation: The conversation object
            limit: Maximum number of recent messages to include
        """
        if limit is None:
            limit = settings.max_conversation_history
        
        messages = (
            self.db.query(Message)
            .filter(Message.conversation_id == conversation.id)
            .order_by(Message.created_at.desc())
            .limit(limit)
            .all()
        )
        
        # Reverse to get chronological order
        messages.reverse()
        
        return [
            ChatMessage(role=msg.role, content=msg.content)
            for msg in messages
        ]

    async def process_message(
        self,
        client_id: str,
        agent_id: str,
        message_content: str,
        conversation_id: Optional[str] = None,
        user_identifier: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> tuple[Conversation, Message]:
        """
        Process a user message and generate AI response.
        
        Returns:
            Tuple of (conversation, assistant_message)
        """
        # Validate message length
        if len(message_content) > settings.max_message_length:
            raise ValidationError(
                f"Message exceeds maximum length of {settings.max_message_length} characters"
            )
        
        # Check idempotency
        if idempotency_key:
            existing_message = check_idempotency_key(self.db, idempotency_key)
            if existing_message:
                # Return existing conversation and message
                conversation = (
                    self.db.query(Conversation)
                    .filter(Conversation.id == existing_message.conversation_id)
                    .first()
                )
                return conversation, existing_message
        
        # Get or create conversation
        conversation = self.get_or_create_conversation(
            client_id=client_id,
            agent_id=agent_id,
            conversation_id=conversation_id,
            user_identifier=user_identifier,
        )
        
        # Get agent for system prompt
        agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
        
        # Save user message
        user_message = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation.id,
            role="user",
            content=message_content,
            idempotency_key=idempotency_key,
        )
        self.db.add(user_message)
        self.db.commit()
        
        # Build messages for AI runtime
        messages = []
        
        # Add system prompt if exists
        if agent.system_prompt:
            messages.append(ChatMessage(role="system", content=agent.system_prompt))
        
        # Add conversation history
        history = self.get_conversation_history(conversation)
        messages.extend(history)
        
        # Add new user message
        messages.append(ChatMessage(role="user", content=message_content))
        
        # Create generation request with tenant context
        generation_request = GenerationRequest(
            context=RuntimeContext(
                tenant_id=client_id,
                agent_id=agent_id,
            ),
            messages=messages,
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        
        # Call Core AI Runtime (LangGraph)
        try:
            result = await self.runtime.generate(generation_request)
        except Exception as e:
            # Log error but don't expose internal details
            raise ValidationError(f"Failed to generate response: {str(e)}")
        
        # Save assistant message
        assistant_message = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation.id,
            role="assistant",
            content=result.content,
        )
        self.db.add(assistant_message)
        
        # Update conversation timestamp
        conversation.updated_at = datetime.now(timezone.utc)
        
        self.db.commit()
        self.db.refresh(assistant_message)
        
        return conversation, assistant_message

    def get_conversation(
        self,
        client_id: str,
        conversation_id: str,
    ) -> Conversation:
        """
        Get a conversation by ID with tenant isolation.
        
        Raises:
            ResourceNotFoundError: If conversation doesn't exist
            UnauthorizedAccessError: If conversation belongs to different client
        """
        conversation = (
            self.db.query(Conversation)
            .filter(Conversation.id == conversation_id)
            .first()
        )
        
        if not conversation:
            raise ResourceNotFoundError("Conversation", conversation_id)
        
        if conversation.client_id != client_id:
            raise UnauthorizedAccessError("Conversation")
        
        return conversation

    def get_conversation_messages(
        self,
        client_id: str,
        conversation_id: str,
    ) -> list[Message]:
        """
        Get all messages in a conversation with tenant isolation.
        """
        # Verify access first
        conversation = self.get_conversation(client_id, conversation_id)
        
        messages = (
            self.db.query(Message)
            .filter(Message.conversation_id == conversation.id)
            .order_by(Message.created_at.asc())
            .all()
        )
        
        return messages
