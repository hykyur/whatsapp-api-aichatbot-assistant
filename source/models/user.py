from sqlmodel import Field, SQLModel
from datetime import datetime

class User(SQLModel, table=true):
    id: int | Field(default=None, primary_key=True)
    name: str
    phone: str = Field(unique=True, index=True)
    message_count: int
    created_at: datetime = Field(default_factory=datetime.utcnow)

