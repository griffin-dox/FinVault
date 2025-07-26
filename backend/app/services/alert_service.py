from typing import List, Dict, Any
from datetime import datetime

alerts: List[Dict[str, Any]] = []

def trigger_alert(event_type: str, details: str):
    alert = {
        "event_type": event_type,
        "details": details,
        "timestamp": datetime.utcnow().isoformat()
    }
    alerts.append(alert)
    print(f"[ALERT] {event_type}: {details}")
    return alert

def get_alerts() -> List[Dict[str, Any]]:
    return alerts[-50:]  # Return last 50 alerts 