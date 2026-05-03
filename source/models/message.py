from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey
from sqlalchemy.types import DateTime
from datetime import datetime, timezone
from enum import Enum

from source.models.base import Base



class MessageRole(str, Enum):
    user      = "user"
    developer = "developer"
    assistant = "assistant"
    system    = "system"


class MessageStatus(str, Enum):
    pending    = "pending"
    ai_handled = "ai_handled"
    escalated  = "escalated"
    drafting   = "drafting"
    sent       = "sent"


class Message(Base):
    __tablename__ = "message"

    id:         Mapped[int]           = mapped_column(primary_key=True)
    user_id:    Mapped[int]           = mapped_column(ForeignKey("user.id"))
    role:       Mapped[MessageRole]   = mapped_column(default=MessageRole.user)
    status:     Mapped[MessageStatus]
    body:       Mapped[str]
    created_at: Mapped[datetime]      = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))