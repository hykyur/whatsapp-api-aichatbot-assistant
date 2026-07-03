from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import DateTime
from sqlalchemy import ForeignKey

from datetime import datetime, timezone
from enum import Enum

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    phone: Mapped[str | None] = mapped_column(nullable=True, unique=True, index=True)
    openai_token: Mapped[str | None] = mapped_column(nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class MessageRole(str, Enum):
    user = "user"
    developer = "developer"
    assistant = "assistant"
    system = "system"

class MessageStatus(str, Enum):
    pending = "pending"
    ai_handled = "ai_handled"
    escalated = "escalated"
    drafting = "drafting"
    sent = "sent"

class Message(Base):
    __tablename__ = "message"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    role: Mapped[MessageRole] = mapped_column(default=MessageRole.user)
    status: Mapped[MessageStatus]
    body: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))