from app.models.audit_log import AuditLog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from datetime import datetime
import inspect

async def log_audit_event(db, user_id: int, action: str, details: str | None = None):
    log = AuditLog(
        user_id=user_id,
        action=action,
        details=details,
        timestamp=datetime.utcnow()
    )
    db.add(log)
    
    # Check if it's an async session
    if isinstance(db, AsyncSession):
        await db.commit()
    else:
        db.commit()
    
    return log

async def log_login_attempt(db, user_id: int | None, location: str, status: str, details: str | None = None):
    action = f"login_{status}"
    combined_details = details if details else location
    if details and location and details != location:
        combined_details = f"{details}. Location: {location}"
    
    log = AuditLog(
        user_id=user_id,
        action=action,
        details=combined_details,
        timestamp=datetime.utcnow()
    )
    db.add(log)
    
    # Check if it's an async session
    if isinstance(db, AsyncSession):
        await db.commit()
    else:
        db.commit()
    
    return log

async def log_transaction(db, user_id: int, transaction_id: int, action: str, details: str | None = None):
    log = AuditLog(
        user_id=user_id,
        action=f"transaction_{action}",
        details=f"Transaction ID: {transaction_id}. {details or ''}",
        timestamp=datetime.utcnow()
    )
    db.add(log)
    
    # Check if it's an async session
    if isinstance(db, AsyncSession):
        await db.commit()
    else:
        db.commit()
    
    return log

async def log_admin_action(db, user_id: int, action: str, details: str | None = None):
    log = AuditLog(
        user_id=user_id,
        action=f"admin_{action}",
        details=details,
        timestamp=datetime.utcnow()
    )
    db.add(log)
    
    # Check if it's an async session
    if isinstance(db, AsyncSession):
        await db.commit()
    else:
        db.commit()
    
    return log 