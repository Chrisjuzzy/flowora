from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from database import Base
from datetime import datetime

class UserAPIKey(Base):
    __tablename__ = "user_api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    provider = Column(String, index=True)  # "openai", "mistral", "anthropic"
    encrypted_key = Column(String)  # In a real app, use encryption. Here we simulate.
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime, nullable=True)
