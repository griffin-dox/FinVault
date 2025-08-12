from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple, Optional
import os
import ipaddress

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

# ----------------------
# Login Risk Evaluation
# ----------------------

LOW_THRESHOLD = 40
MEDIUM_THRESHOLD = int(os.environ.get("RISK_THRESHOLD_MEDIUM", "40"))
HIGH_THRESHOLD = int(os.environ.get("RISK_THRESHOLD_HIGH", "60"))

def _ip_in_prefixes(ip: Optional[str], prefixes: List[str]) -> bool:
    if not ip:
        return False
    try:
        ip_obj = ipaddress.ip_address(ip)
    except ValueError:
        return False
    for pref in prefixes:
        try:
            net = ipaddress.ip_network(pref.strip(), strict=False)
            if ip_obj in net:
                return True
        except ValueError:
            # Ignore invalid prefixes
            continue
    return False

def _normalize_metrics(metrics: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    m = metrics or {}
    return {
        "device": m.get("device") or {},
        "geo": m.get("geo") or {},
        "ip": m.get("ip") or None,
    }

def _haversine(lat1: Optional[float], lon1: Optional[float], lat2: Optional[float], lon2: Optional[float]) -> float:
    if None in [lat1, lon1, lat2, lon2]:
        return float('inf')
    # convert decimal degrees to radians
    from math import radians, cos, sin, asin, sqrt
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371
    return c * r

def device_penalty(current: Dict[str, Any], profile: Dict[str, Any]) -> Tuple[int, List[str]]:
    reasons: List[str] = []
    penalty = 0
    fields = ['browser', 'os', 'screen', 'timezone']
    for k in fields:
        if current.get(k) and profile.get(k) and current.get(k) != profile.get(k):
            reasons.append(f"Device {k} mismatch: {current.get(k)} vs {profile.get(k)}")
            penalty += 20
    return penalty, reasons

def geo_penalty(current: Dict[str, Any], profile: Dict[str, Any]) -> Tuple[int, List[str]]:
    """Adaptive geolocation penalty using browser-reported accuracy.
    - Tolerance (meters) = clamp(max(accuracy, 100), 100, 500)
    - If accuracy > 500 m (very imprecise), fall back to IP/network checks (handled by caller) and add a base penalty.
    - Distances computed in km; convert to meters for comparison.
    """
    reasons: List[str] = []
    penalty = 0
    lat1, lon1 = current.get('latitude'), current.get('longitude')
    lat2, lon2 = profile.get('latitude'), profile.get('longitude')
    accuracy = current.get('accuracy')  # meters
    # Fallback/low-precision handling
    if isinstance(accuracy, (int, float)) and accuracy > 500:
        reasons.append("Geo accuracy too low (>500m); relying on IP/network")
        penalty += 10
        return penalty, reasons
    if lat1 and lon1 and lat2 and lon2:
        dist_km = _haversine(lat1, lon1, lat2, lon2)
        dist_m = dist_km * 1000.0
        tol_m = 100.0
        if isinstance(accuracy, (int, float)):
            tol_m = max(100.0, min(500.0, float(accuracy)))
        # Penalty scaled by how much we exceed tolerance
        if dist_m > tol_m:
            over = dist_m - tol_m
            # 10 points base + up to 20 points scaled (cap at ~2km over)
            add = 10 + min(20, over / 100.0)
            penalty += int(add)
            reasons.append(f"Geo differs by {dist_km:.2f} km (> tol {int(tol_m)}m)")
    return penalty, reasons

def typing_penalty(current: Dict[str, Any], profile: Dict[str, Any]) -> Tuple[int, List[str]]:
    """Typing penalty using per-user baselines if available.
    Falls back to absolute thresholds if baselines absent.
    Baseline fields expected under profile['baselines']['typing']:
      wpm_mean, wpm_std, err_mean, err_std, timing_mean, timing_std
    """
    penalty = 0
    reasons: List[str] = []
    cur = current or {}
    prof = profile or {}
    baselines = (prof.get('baselines') or {}).get('typing', {})

    wpm = float(cur.get('wpm', 0))
    err = float(cur.get('errorRate', 0))
    cur_timings = cur.get('keystrokeTimings', [])

    def zscore(val, mean, std):
        if mean is None or std is None or std <= 1e-6:
            return None
        return abs((val - mean) / std)

    # WPM
    wpm_mean = baselines.get('wpm_mean')
    wpm_std = baselines.get('wpm_std')
    z_wpm = zscore(wpm, wpm_mean, wpm_std)
    if z_wpm is not None:
        if z_wpm > 3:
            penalty += 25; reasons.append(f"Typing speed z={z_wpm:.1f}")
        elif z_wpm > 2:
            penalty += 15; reasons.append(f"Typing speed z={z_wpm:.1f}")
        elif z_wpm > 1.5:
            penalty += 8; reasons.append(f"Typing speed z={z_wpm:.1f}")
    else:
        # Fallback to absolute diffs vs stored raw
        wpm_diff = abs(wpm - float((prof.get('typing_pattern') or {}).get('wpm', 0)))
        if wpm_diff > 30:
            penalty += 30
        elif wpm_diff > 20:
            penalty += 20
        elif wpm_diff > 10:
            penalty += 10
        if wpm_diff > 10:
            reasons.append(f"Typing speed differs by {wpm_diff:.1f} WPM")

    # Error rate
    err_mean = baselines.get('err_mean')
    err_std = baselines.get('err_std')
    z_err = zscore(err, err_mean, err_std)
    if z_err is not None:
        if z_err > 3:
            penalty += 20; reasons.append(f"Error rate z={z_err:.1f}")
        elif z_err > 2:
            penalty += 12; reasons.append(f"Error rate z={z_err:.1f}")
        elif z_err > 1.5:
            penalty += 6; reasons.append(f"Error rate z={z_err:.1f}")
    else:
        error_diff = abs(err - float((prof.get('typing_pattern') or {}).get('errorRate', 0)))
        if error_diff > 0.2:
            penalty += 20
        elif error_diff > 0.1:
            penalty += 10
        if error_diff > 0.1:
            reasons.append(f"Error rate differs by {error_diff:.2f}")

    # Keystroke timings
    prof_timings = (prof.get('typing_pattern') or {}).get('keystrokeTimings', [])
    timing_mean = baselines.get('timing_mean')
    timing_std = baselines.get('timing_std')
    if cur_timings and (timing_mean is not None and timing_std is not None and timing_std > 1e-6):
        cur_mean = sum(cur_timings)/len(cur_timings)
        z_t = abs((cur_mean - timing_mean)/timing_std)
        if z_t > 3:
            penalty += 20; reasons.append(f"Timing mean z={z_t:.1f}")
        elif z_t > 2:
            penalty += 12; reasons.append(f"Timing mean z={z_t:.1f}")
        elif z_t > 1.5:
            penalty += 6; reasons.append(f"Timing mean z={z_t:.1f}")
    elif cur_timings and prof_timings:
        cur_mean = sum(cur_timings)/len(cur_timings)
        prof_mean = sum(prof_timings)/len(prof_timings)
        timing_diff = abs(cur_mean - prof_mean)
        if timing_diff > 200:
            penalty += 25
        elif timing_diff > 100:
            penalty += 15
        elif timing_diff > 50:
            penalty += 5
        if timing_diff > 50:
            reasons.append(f"Keystroke timing mean differs by {timing_diff:.0f}ms")
    return penalty, reasons

def mouse_penalty(current: Dict[str, Any], profile: Dict[str, Any]) -> Tuple[int, List[str]]:
    """Mouse/touch penalty using per-user baselines if available.
    Baselines under profile['baselines']['pointer']:
      path_len_mean/std, clicks_mean/std
    """
    penalty = 0
    reasons: List[str] = []
    cur = current or {}
    prof = profile or {}
    baselines = (prof.get('baselines') or {}).get('pointer', {})

    cur_path = cur.get('path', [])
    prof_path = (prof.get('mouse_dynamics') or {}).get('path', [])

    def z(val, mean, std):
        if mean is None or std is None or std <= 1e-6:
            return None
        return abs((val - mean)/std)

    if cur_path:
        cur_len = len(cur_path)
        z_len = z(cur_len, baselines.get('path_len_mean'), baselines.get('path_len_std'))
        if z_len is not None:
            if z_len > 3: penalty += 12; reasons.append(f"Path len z={z_len:.1f}")
            elif z_len > 2: penalty += 7; reasons.append(f"Path len z={z_len:.1f}")
        elif prof_path:
            diff = abs(cur_len - len(prof_path))
            if diff > 50: penalty += 15
            elif diff > 10: penalty += 5
            if diff > 10: reasons.append(f"Mouse/touch path length differs by {diff} points")

    cur_clicks = cur.get('clicks', 0)
    prof_clicks = (prof.get('mouse_dynamics') or {}).get('clicks', 0)
    z_clicks = z(cur_clicks, baselines.get('clicks_mean'), baselines.get('clicks_std'))
    if z_clicks is not None:
        if z_clicks > 3: penalty += 10; reasons.append(f"Clicks z={z_clicks:.1f}")
        elif z_clicks > 2: penalty += 6; reasons.append(f"Clicks z={z_clicks:.1f}")
    else:
        click_diff = abs(cur_clicks - prof_clicks)
        if click_diff > 5: penalty += 10
        elif click_diff > 2: penalty += 5
        if click_diff > 2: reasons.append(f"Click/tap count differs by {click_diff}")
    return penalty, reasons

def score_login(behavioral_challenge: Optional[Dict[str, Any]], metrics: Optional[Dict[str, Any]], profile: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    reasons: List[str] = []
    risk_score = 0
    profile = profile or {}
    m = _normalize_metrics(metrics)
    geo = m["geo"]
    device = m["device"]
    ip = m["ip"]

    # Baseline penalties for missing/weak signals
    if not profile:
        reasons.append("No behavior profile on file")
        risk_score += 20
    if not behavioral_challenge:
        reasons.append("No behavioral challenge provided")
        risk_score += 15
    if not geo or geo.get('fallback', True):
        reasons.append("No reliable geolocation (fallback or missing)")
        risk_score += 25
    if not device or len(device) == 0:
        reasons.append("No device fingerprint provided")
        risk_score += 20

    # Behavioral penalties
    if behavioral_challenge and behavioral_challenge.get('type') == 'typing':
        pen, r = typing_penalty(behavioral_challenge.get('data') or {}, profile.get('typing_pattern', {}) or {})
        reasons += r
        risk_score += pen
    if behavioral_challenge and behavioral_challenge.get('type') in ['mouse', 'touch']:
        pen, r = mouse_penalty(behavioral_challenge.get('data') or {}, profile.get('mouse_dynamics', {}) or {})
        reasons += r
        risk_score += pen

    # Device checks
    core_device_fields = ['browser', 'os', 'screen', 'timezone']
    unknowns = [k for k in core_device_fields if not device.get(k)]
    if unknowns:
        reasons.append(f"Missing device fields: {', '.join(unknowns)}")
        risk_score += 10
    # Device mismatch vs profile
    if profile.get('device_fingerprint') and device:
        d_pen, d_reasons = device_penalty(device, profile.get('device_fingerprint') or {})
        reasons += d_reasons
        risk_score += d_pen

    # Geo checks - compare against profile when available
    if profile.get('geo') and geo:
        g_pen, g_reasons = geo_penalty(geo, profile.get('geo') or {})
        reasons += g_reasons
        risk_score += g_pen
    # Minimal IP/geo presence penalty
    if ip in [None, '', 'unknown']:
        reasons.append("IP missing or unknown")
        risk_score += 5
    deny = os.environ.get('DENYLIST_IP_PREFIXES', '')
    allow = os.environ.get('ALLOWLIST_IP_PREFIXES', '')
    denylist = [p.strip() for p in deny.split(',') if p.strip()]
    allowlist = [p.strip() for p in allow.split(',') if p.strip()]
    if denylist and _ip_in_prefixes(ip, denylist):
        reasons.append("IP is in denylist range")
        risk_score += 25
    if allowlist and not _ip_in_prefixes(ip, allowlist):
        # Not strictly a penalty, but slight nudge if outside familiar networks
        risk_score += 5

    # Known networks from user profile
    known_networks = set(profile.get('known_networks', []) or [])
    if ip and known_networks:
        if _ip_in_prefixes(ip, list(known_networks)):
            reasons.append("IP matches user's known network")
            risk_score = max(0, risk_score - 7)
        else:
            risk_score += 3

    # Escalation by missing critical signals count
    missing = 0
    if not profile:
        missing += 1
    if not behavioral_challenge:
        missing += 1
    if not device:
        missing += 1
    if not geo or geo.get('fallback', True):
        missing += 1
    if missing >= 2:
        risk_score = max(risk_score, 45)
    if missing >= 3:
        risk_score = max(risk_score, 65)

    risk_score = min(risk_score, 100)
    # Light consideration of passive telemetry if available (scroll/dwell)
    # These are intentionally low weight to avoid false positives.
    scroll = (metrics or {}).get('scroll_max_pct')
    dwell = (metrics or {}).get('dwell_ms')
    try:
        if isinstance(scroll, (int, float)) and scroll < 10:
            risk_score += 2; reasons.append("Low scroll depth")
        if isinstance(dwell, (int, float)) and dwell < 2000:
            risk_score += 2; reasons.append("Very short dwell time")
    except Exception:
        pass
    if risk_score > HIGH_THRESHOLD:
        level = "high"
    elif risk_score > MEDIUM_THRESHOLD:
        level = "medium"
    else:
        level = "low"

    return {
        "risk_score": risk_score,
        "level": level,
        "reasons": reasons,
        "missing_signals": missing,
    }


def score_session(telemetry: Dict[str, Any], profile: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Score in-session telemetry periodically.
    Expected telemetry keys: device, geo, ip, idle_jitter_ms, pointer_speed_std, nav_bf_usage
    """
    profile = profile or {}
    reasons: List[str] = []
    risk = 0
    m = {
        "device": telemetry.get("device") or {},
        "geo": telemetry.get("geo") or {},
        "ip": telemetry.get("ip") or None,
    }
    # Device/Geo consistency
    if profile.get('device_fingerprint') and m['device']:
        d_pen, d_r = device_penalty(m['device'], profile.get('device_fingerprint') or {})
        reasons += d_r
        risk += d_pen // 2  # softer in-session weight
    if profile.get('geo') and m['geo']:
        g_pen, g_r = geo_penalty(m['geo'], profile.get('geo') or {})
        reasons += g_r
        risk += g_pen // 2

    # IP/Networks
    ip = m['ip']
    if ip in [None, '', 'unknown']:
        reasons.append("IP missing or unknown (session)")
        risk += 3
    else:
        known_networks = set(profile.get('known_networks', []) or [])
        if known_networks and not _ip_in_prefixes(ip, list(known_networks)):
            risk += 3

    # Idle/pointer anomalies
    idle_jitter = telemetry.get('idle_jitter_ms')
    if isinstance(idle_jitter, (int, float)) and idle_jitter > 3000:
        reasons.append("High idle jitter")
        risk += 5
    pointer_std = telemetry.get('pointer_speed_std')
    if isinstance(pointer_std, (int, float)) and pointer_std > 1.5:
        reasons.append("Unstable pointer speed")
        risk += 5
    # Navigation anomalies (suspicious BF usage)
    nav_bf = telemetry.get('nav_bf_usage')
    if isinstance(nav_bf, (int, float)) and nav_bf > 5:
        reasons.append("High back/forward usage")
        risk += 3

    risk = min(100, max(0, risk))
    if risk > HIGH_THRESHOLD:
        level = "high"
    elif risk > MEDIUM_THRESHOLD:
        level = "medium"
    else:
        level = "low"
    return {"risk_score": risk, "level": level, "reasons": reasons}
