from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from app.models.user import Base
from datetime import datetime, timezone

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)
    action = Column(String, nullable=False)
    details = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), nullable=False) 