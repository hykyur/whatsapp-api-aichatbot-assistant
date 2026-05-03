from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from sqlalchemy.types import DateTime
from source.models.base import Base

class User(Base):
    __tablename__ = "user"

    id:         Mapped[int]             = mapped_column(primary_key = True)
    name:       Mapped[str]
    phone:      Mapped[str | None]      = mapped_column(nullable = True, unique = True, index = True)
    created_at: Mapped[datetime]        = mapped_column(DateTime(timezone=True), default = lambda: datetime.now(timezone.utc))
