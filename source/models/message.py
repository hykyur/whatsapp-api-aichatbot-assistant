from sqlmodel import Field, SQLModel, create_engine
from datetime import datetime
from enum import Enum


load_dotenv()

class MessageRole(str, Enum):
    user      = "user"   
    assistant = "assistant"

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
    status: MessageStatus = MessageRole.pending
    created_at: datetime = Field(default_factory=datetime.utcnow)
