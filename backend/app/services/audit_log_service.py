from app.models.audit_log import AuditLog
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

async def log_audit_event(db: AsyncSession, user_id: int, action: str, details: str = None):
    log = AuditLog(
        user_id=user_id,
        action=action,
        details=details,
        timestamp=datetime.utcnow()
    )
    db.add(log)
    await db.commit()
    return log

async def log_login_attempt(db: AsyncSession, user_id: int, location: str, status: str, details: str = None):
    action = f"login_{status}"
    log = AuditLog(
        user_id=user_id,
        action=action,
        details=details or location,
        timestamp=datetime.utcnow()
    )
    db.add(log)
    await db.commit()
    return log 