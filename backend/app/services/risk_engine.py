from datetime import datetime, timedelta
from typing import Dict, Any, List

# Example of dynamic rules (could be loaded from DB)
default_rules = {
    "device_mismatch": 50,
    "unusual_time": 30,
    "large_amount": 40,
    "rapid_repeat": 30,
    "location_mismatch": 40,
    "high_threshold": 70,
    "medium_threshold": 40
}

# In-memory user transaction history for anomaly detection (replace with DB/cache in prod)
user_tx_history: Dict[int, List[Dict[str, Any]]] = {}


def score_transaction(transaction: Dict[str, Any], behavior_profile: Dict[str, Any], rules: Dict[str, Any] = None) -> Dict[str, Any]:
    if rules is None:
        rules = default_rules
    risk_score = 0
    reasons = []
    anomalies = []
    user_id = transaction.get("user_id")
    now = datetime.utcnow()

    # Device mismatch
    if transaction.get("device_info") != behavior_profile.get("device_fingerprint"):
        risk_score += rules["device_mismatch"]
        reasons.append("Device mismatch")
        anomalies.append("New device detected")
    # Location mismatch
    if transaction.get("location") != behavior_profile.get("location"):
        risk_score += rules["location_mismatch"]
        reasons.append("Location mismatch")
        anomalies.append("New location detected")
    # Unusual time
    hour = now.hour
    if hour < 8 or hour > 20:
        risk_score += rules["unusual_time"]
        reasons.append("Unusual transaction time")
    # Large amount (outlier)
    if transaction.get("amount", 0) > rules["large_amount"]:
        risk_score += rules["large_amount"]
        reasons.append("Large transaction amount")
        anomalies.append("Outlier transaction amount")
    # Rapid repeat (multiple txns in short time)
    history = user_tx_history.get(user_id, [])
    recent = [t for t in history if (now - t["created_at"]).total_seconds() < 60]
    if len(recent) >= 3:
        risk_score += rules["rapid_repeat"]
        reasons.append("Rapid repeat transactions")
        anomalies.append("Rapid repeat detected")
    # Save txn to history
    history.append({"created_at": now, **transaction})
    user_tx_history[user_id] = history[-10:]  # keep last 10
    # Final risk level
    if risk_score >= rules["high_threshold"]:
        level = "high"
    elif risk_score >= rules["medium_threshold"]:
        level = "medium"
    else:
        level = "low"
    return {
        "risk_score": risk_score,
        "level": level,
        "reasons": reasons,
        "anomalies": anomalies
    } 