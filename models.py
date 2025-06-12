from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MessageStatus(str, Enum):
    """Message status enumeration"""

    UNREAD = "unread"
    READ = "read"


class Message:
    """Internal message representation"""

    def __init__(
        self,
        recipient: str,
        content: str,
        sender: Optional[str] = None,
        message_id: Optional[UUID] = None,
        timestamp: Optional[datetime] = None,
        status: MessageStatus = MessageStatus.UNREAD,
    ):
        self.id = message_id or uuid4()
        self.recipient = recipient
        self.content = content
        self.sender = sender
        self.timestamp = timestamp or datetime.now(timezone.utc)
        self.status = status

    def mark_as_read(self):
        """Mark message as read"""
        self.status = MessageStatus.READ

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary"""
        return {
            "id": str(self.id),
            "recipient": self.recipient,
            "content": self.content,
            "sender": self.sender,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status.value,
        }


class MessageCreate(BaseModel):
    """Request model for creating a new message"""

    recipient: str = Field(
        ...,
        description="Recipient identifier (email, phone, username, etc.)",
        min_length=1,
        max_length=255,
    )
    content: str = Field(
        ..., description="Message content (plain text)", min_length=1, max_length=10000
    )
    sender: Optional[str] = Field(
        None, description="Sender identifier (optional)", max_length=255
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "recipient": "user@example.com",
                "content": "Hello, this is a test message!",
                "sender": "admin@example.com",
            }
        }
    )

    @field_validator("recipient", mode="before")
    @classmethod
    def validate_recipient(cls, v):
        if not v or not v.strip():
            raise ValueError("Recipient cannot be empty")
        return v.strip()

    @field_validator("content", mode="before")
    @classmethod
    def validate_content(cls, v):
        if not v or not v.strip():
            raise ValueError("Message content cannot be empty")
        return v.strip()

    @field_validator("sender", mode="before")
    @classmethod
    def validate_sender(cls, v):
        if v:
            return v.strip()
        return v


class MessageResponse(BaseModel):
    """Response model for message data"""

    id: UUID = Field(..., description="Unique message identifier")
    recipient: str = Field(..., description="Message recipient")
    content: str = Field(..., description="Message content")
    sender: Optional[str] = Field(None, description="Message sender")
    timestamp: datetime = Field(..., description="Message creation timestamp")
    status: MessageStatus = Field(..., description="Message status")

    @classmethod
    def from_message(cls, message: Message) -> "MessageResponse":
        """Create response model from internal message object"""
        return cls(
            id=message.id,
            recipient=message.recipient,
            content=message.content,
            sender=message.sender,
            timestamp=message.timestamp,
            status=message.status,
        )


class BaseMessagesResponse(BaseModel):
    """Response model for all messages"""

    messages: List[MessageResponse] = Field(..., description="List of messages")


class MessagesResponseNew(BaseMessagesResponse):
    """Response model for all messages"""

    recipient: str = Field(..., description="Recipient identifier")
    total: int = Field(..., description="Total number of messages for recipient")


class MessagesResponsePaginated(BaseMessagesResponse):
    """Response model for all messages"""

    messages: List[MessageResponse] = Field(..., description="List of messages")
    total: int = Field(..., description="Total number of messages for recipient")
    start: Optional[int] = Field(None, description="Start index for pagination")
    limit: Optional[int] = Field(None, description="Limit for pagination")


class MessagesResponseRecipientPaginated(MessagesResponsePaginated):
    """Response model for all messages with a specific recipient"""

    recipient: str = Field(..., description="Recipient identifier")


class DeleteResponse(BaseModel):
    """Response model for delete operations"""

    deleted_count: int = Field(..., description="Number of messages deleted")
    message_ids: List[UUID] = Field(..., description="IDs of deleted messages")
    timestamp: datetime = Field(..., description="Deletion timestamp")


class DeleteMultipleRequest(BaseModel):
    """Request model for deleting multiple messages"""

    message_ids: List[UUID] = Field(
        ..., description="List of message IDs to delete", min_length=1, max_length=100
    )


class ErrorResponse(BaseModel):
    """Standard error response model"""

    detail: str = Field(..., description="Error description")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
