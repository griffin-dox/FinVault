from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from app.models.user import Base

class Session(Base):
    __tablename__ = "sessions"
    session_id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    jwt_token = Column(String, nullable=False)
    device_info = Column(String, nullable=True)
    login_time = Column(DateTime, nullable=False) 