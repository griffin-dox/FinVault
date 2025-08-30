from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Enum
from app.models.user import Base
import enum
from datetime import datetime

class TransactionStatus(enum.Enum):
    pending = "pending"
    allowed = "allowed"
    challenged = "challenged"
    blocked = "blocked"

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)
    target_account = Column(String, nullable=True)
    recipient = Column(String, nullable=True)
    device_info = Column(String, nullable=True)
    location = Column(String, nullable=True)
    intent = Column(String, nullable=True)
    description = Column(String, nullable=True)
    risk_score = Column(Float, nullable=True)
    status = Column(String, default=TransactionStatus.pending.value, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False) 