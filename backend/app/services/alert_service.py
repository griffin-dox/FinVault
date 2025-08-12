from typing import List, Dict, Any
from datetime import datetime

alerts: List[Dict[str, Any]] = []

def trigger_alert(event_type: str, details: str):
    alert = {
        "event_type": event_type,
        "details": details,
    }
    alerts.append(alert)
    print(f"[ALERT] {event_type}: {details}")
    # Dispatch asynchronously via Celery (best-effort)
    try:
        from app.services.tasks import dispatch_alert
        dispatch_alert.delay(event_type, details)
    except Exception as e:
        # Fallback to sync log only
        print(f"[ALERT] Celery dispatch failed: {e}")
    return alert

def get_alerts() -> List[Dict[str, Any]]:
    return alerts[-50:]  # Return last 50 alerts 