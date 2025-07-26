from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
import enum
from datetime import datetime

Base = declarative_base()

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
    target_account = Column(String, nullable=False)
    device_info = Column(String, nullable=True)
    location = Column(String, nullable=True)
    intent = Column(String, nullable=True)
    risk_score = Column(Float, nullable=True)
    status = Column(Enum(TransactionStatus), default=TransactionStatus.pending, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False) 