from sqlmodel import SQLModel, Field
from datetime import datetime
from enum import Enum
from user import User

# The MessageRole class is written according to the EasyInputMessage type from OpenAI API documentation, ref: https://developers.openai.com/api/reference/resources/responses#(resource)%20responses%20%3E%20(model)%20easy_input_message%20%3E%20(schema)

class MessageRole(str, Enum):
    user      = "user"
    developer = "developer"
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
