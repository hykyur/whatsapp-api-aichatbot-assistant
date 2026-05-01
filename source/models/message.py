from sqlmodel import SQLModel, Field
from datetime import datetime
from enum import Enum
from user import User

class MessageRole(str, Enum):
    user      = "user"  
    admin     = "admin" 
    assistant = "assistant"
    system    = "system"

class MessageStatus (str, Enum):
    pending       = "pending"
    ai_handled    = "ai_handled"
    escalated     = "escalated"
    drafting      = "drafting"
    sent          = "sent"

class Message(SQLModel, table = true):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    role: MessageRole
    body: str
    status: MessageStatus
    created_at: datetime = Field(default_factory=datetime.utcnow)
