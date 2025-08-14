from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple, Optional
import os
import ipaddress
import re

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
        # Optional IP enrichments (populated by caller if available)
        "ip_asn": m.get("ip_asn"),
        "ip_asn_org": m.get("ip_asn_org"),
        "ip_city": m.get("ip_city"),
        "ip_region": m.get("ip_region"),
        "ip_country": m.get("ip_country"),
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
    """Compare device fingerprints with tolerant rules.
    Rules:
    - browser: compare brand and major version; if same brand and |major diff|<=1 -> no penalty; different brand -> 20; else small 5.
    - os: compare family (Windows/macOS/Linux/Android/iOS); same family -> no penalty; else 15.
    - screen: tolerate ±100px on width/height; if within tolerance -> no penalty; else if same class (mobile/tablet/desktop) -> 5; else 15.
    - timezone: keep strict compare for now.
    """
    reasons: List[str] = []
    penalty = 0

    cur = current or {}
    prof = profile or {}

    # Browser
    cb, cv = _parse_browser(cur.get('browser'))
    pb, pv = _parse_browser(prof.get('browser'))
    if cb and pb:
        if cb != pb:
            penalty += 20
            reasons.append(f"Device browser brand mismatch: {cb} vs {pb}")
        else:
            # Same brand; compare major version
            if cv is not None and pv is not None:
                if abs(cv - pv) > 1:
                    penalty += 5
                    reasons.append(f"Device browser version differs: {cv} vs {pv}")
    elif cur.get('browser') and prof.get('browser') and cur.get('browser') != prof.get('browser'):
        penalty += 10
        reasons.append("Device browser differs (unparsed)")

    # OS
    co = _canonical_os(cur.get('os'))
    po = _canonical_os(prof.get('os'))
    if co and po and co != po:
        penalty += 15
        reasons.append(f"Device os family mismatch: {co} vs {po}")

    # Screen (tolerant)
    cs = cur.get('screen')
    ps = prof.get('screen')
    if cs and ps:
        cwh = _parse_screen(cs)
        pwh = _parse_screen(ps)
        if cwh and pwh:
            if not _screen_within_tolerance(cwh, pwh, tolerance_px=100):
                ccls = _screen_class(cwh)
                pcls = _screen_class(pwh)
                if ccls == pcls:
                    penalty += 5
                    reasons.append(f"Screen size changed within same class ({ccls})")
                else:
                    penalty += 15
                    reasons.append(f"Screen class changed: {ccls} -> {pcls}")
        elif cs != ps:
            # Fallback textual compare
            penalty += 5
            reasons.append("Screen differs")

    # Timezone (strict)
    if cur.get('timezone') and prof.get('timezone') and cur.get('timezone') != prof.get('timezone'):
        penalty += 10
        reasons.append(f"Device timezone mismatch: {cur.get('timezone')} vs {prof.get('timezone')}")

    return penalty, reasons

# ----------------------
# Device normalization helpers
# ----------------------

_BROWSER_BRANDS = [
    'chrome', 'chromium', 'edge', 'edg', 'safari', 'firefox', 'fx', 'opera', 'opr', 'brave'
]

def _parse_browser(value: Optional[str]) -> Tuple[Optional[str], Optional[int]]:
    """Parse browser into (brand, major_version). Accepts UA or 'Chrome 119'."""
    if not value:
        return None, None
    s = str(value)
    low = s.lower()
    # If looks like 'Name 123'
    m = re.match(r"([A-Za-z]+)\s+(\d+)", s)
    if m:
        return m.group(1).lower(), int(m.group(2))
    # Try to extract from UA
    # Order matters: Chrome before Safari (to avoid Mobile Safari on iOS reporting Safari)
    if 'chrome' in low or 'crios' in low:
        ver = _ua_version(low, ['chrome/', 'crios/'])
        return 'chrome', ver
    if 'edg' in low:
        ver = _ua_version(low, ['edg/'])
        return 'edge', ver
    if 'firefox' in low or 'fx' in low:
        ver = _ua_version(low, ['firefox/'])
        return 'firefox', ver
    if 'safari' in low and 'chrome' not in low:
        ver = _ua_version(low, ['version/'])
        return 'safari', ver
    if 'opr/' in low or 'opera' in low:
        ver = _ua_version(low, ['opr/', 'opera/'])
        return 'opera', ver
    return None, None

def _ua_version(ua: str, needles: List[str]) -> Optional[int]:
    for n in needles:
        if n in ua:
            try:
                seg = ua.split(n, 1)[1]
                num = re.match(r"(\d+)", seg)
                return int(num.group(1)) if num else None
            except Exception:
                return None
    return None

def _canonical_os(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    s = str(value).lower()
    if any(k in s for k in ['win', 'windows']):
        return 'windows'
    if any(k in s for k in ['mac', 'darwin', 'os x', 'macos']):
        return 'macos'
    if 'android' in s:
        return 'android'
    if any(k in s for k in ['ios', 'iphone', 'ipad']):
        return 'ios'
    if any(k in s for k in ['linux', 'ubuntu', 'debian', 'arch']):
        return 'linux'
    return s.strip()

def _parse_screen(value: Any) -> Optional[Tuple[int, int]]:
    """Parse screen into (width, height). Accepts '1920x1080' or dict with width/height."""
    if value is None:
        return None
    try:
        if isinstance(value, str):
            m = re.match(r"\s*(\d+)\s*[xX]\s*(\d+)\s*", value)
            if m:
                return int(m.group(1)), int(m.group(2))
        if isinstance(value, dict):
            w = value.get('width') or value.get('w')
            h = value.get('height') or value.get('h')
            if isinstance(w, (int, float)) and isinstance(h, (int, float)):
                return int(w), int(h)
    except Exception:
        return None
    return None

def _screen_within_tolerance(a: Tuple[int, int], b: Tuple[int, int], tolerance_px: int = 100) -> bool:
    return abs(a[0]-b[0]) <= tolerance_px and abs(a[1]-b[1]) <= tolerance_px

def _screen_class(wh: Tuple[int, int]) -> str:
    w, h = sorted(wh)  # ensure w<=h for classification
    # Very rough classes; tweak as needed
    if w <= 480 and h <= 960:
        return 'mobile-small'
    if w <= 820 and h <= 1366:
        return 'mobile' if w < 600 else 'tablet'
    return 'desktop'

def canonicalize_device_fields(device: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of device with normalized browser/os and screen string normalized to 'WxH'."""
    d = dict(device or {})
    b, v = _parse_browser(d.get('browser'))
    if b:
        d['browser'] = f"{b.capitalize()} {v}" if v is not None else b.capitalize()
    o = _canonical_os(d.get('os'))
    if o:
        d['os'] = o
    s = _parse_screen(d.get('screen'))
    if s:
        d['screen'] = f"{s[0]}x{s[1]}"
    return d

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

def _city_fallback_penalty(cur: Dict[str, Any], prof: Dict[str, Any]) -> Tuple[int, List[str]]:
    """City-level fallback when precise browser geolocation is missing.
    Rules:
    - if no IP geo info: +15
    - if same country and same city: +0
    - if same country and same region: +3
    - if same country, different region: +7
    - if different country: +10
    """
    reasons: List[str] = []
    if not cur:
        reasons.append("No IP geo info for fallback")
        return 15, reasons
    c_city = (cur.get("city") or "").strip().lower()
    c_region = (cur.get("region") or "").strip().lower()
    c_country = (cur.get("country") or "").strip().lower()
    p_city = (prof.get("city") or "").strip().lower()
    p_region = (prof.get("region") or "").strip().lower()
    p_country = (prof.get("country") or "").strip().lower()
    if not p_country:
        # No baseline to compare
        reasons.append("No baseline IP geo; applying default fallback")
        return 15, reasons
    if c_country != p_country:
        reasons.append("IP geo country differs")
        return 10, reasons
    # same country
    if c_city and p_city and c_city == p_city:
        reasons.append("IP geo city matches baseline")
        return 0, reasons
    if c_region and p_region and c_region == p_region:
        reasons.append("IP geo region matches baseline")
        return 3, reasons
    reasons.append("IP geo region differs within country")
    return 7, reasons

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
    # Optional IP enrichments
    ip_asn = m.get("ip_asn")
    ip_asn_org = (m.get("ip_asn_org") or "").strip()
    ip_city = m.get("ip_city")
    ip_region = m.get("ip_region")
    ip_country = m.get("ip_country")

    # Determine ASN-based IP weighting factor
    ip_weight_factor = 1.0
    try:
        asn_str = None
        if isinstance(ip_asn, int):
            asn_str = f"AS{ip_asn}"
        elif isinstance(ip_asn, str) and ip_asn.strip():
            s = ip_asn.strip().upper()
            asn_str = s if s.startswith("AS") else f"AS{s}"
        # Default includes large Indian mobile carriers; override via env CARRIER_ASN_LIST
        carriers_env = os.environ.get("CARRIER_ASN_LIST", "AS55836,AS45609,AS55410,AS55824")
        carriers = {c.strip().upper() for c in carriers_env.split(',') if c.strip()}
        if asn_str and asn_str.upper() in carriers:
            ip_weight_factor = 0.3
    except Exception:
        pass

    # Baseline penalties for missing/weak signals
    if not profile:
        reasons.append("No behavior profile on file")
        risk_score += 20
    if not behavioral_challenge:
        reasons.append("No behavioral challenge provided")
        risk_score += 15
    if not geo or geo.get('fallback', True):
        reasons.append("No reliable geolocation (fallback or missing)")
        # Apply city-level IP geo fallback if both sides have info
        cur_ip_geo = {"city": ip_city, "region": ip_region, "country": ip_country}
        prof_ip_geo = profile.get('ip_geo') or {}
        c_pen, c_reasons = _city_fallback_penalty(cur_ip_geo, prof_ip_geo)
        reasons += [f"Geo fallback: {r}" for r in c_reasons]
        risk_score += c_pen
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
        # Normalize both sides lightly before comparison to reduce false positives
        d_pen, d_reasons = device_penalty(canonicalize_device_fields(device), canonicalize_device_fields(profile.get('device_fingerprint') or {}))
        reasons += d_reasons
        risk_score += d_pen

    # Geo checks - compare against profile when available
    if profile.get('geo') and geo:
        g_pen, g_reasons = geo_penalty(geo, profile.get('geo') or {})
        reasons += g_reasons
        risk_score += g_pen
        # If low-accuracy browser geo (>500m), apply city-level fallback adjustment
        try:
            acc = geo.get('accuracy')
            if isinstance(acc, (int, float)) and acc > 500:
                cur_ip_geo2 = {"city": ip_city, "region": ip_region, "country": ip_country}
                prof_ip_geo2 = profile.get('ip_geo') or {}
                c_pen2, c_reasons2 = _city_fallback_penalty(cur_ip_geo2, prof_ip_geo2)
                # geo_penalty already added a base 10, replace with city-level if larger
                adj = max(0, c_pen2 - 10)
                if adj:
                    reasons += [f"Geo fallback: {r}" for r in c_reasons2]
                    risk_score += adj
        except Exception:
            pass
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
        add = int(round(5 * ip_weight_factor))
        risk_score += add

    # Known networks from user profile
    known_networks = set(profile.get('known_networks', []) or [])
    if ip and known_networks:
        if _ip_in_prefixes(ip, list(known_networks)):
            reasons.append("IP matches user's known network")
            risk_score = max(0, risk_score - 7)
        else:
            add = int(round(3 * ip_weight_factor))
            risk_score += add

    # Note ASN-related downweighting for transparency
    try:
        if ip_weight_factor < 1.0:
            reasons.append("Carrier/mobile ASN detected; down-weighted IP-based checks")
    except Exception:
        pass

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
        # Optional enrichments for consistency with login scoring
        "ip_asn": telemetry.get("ip_asn"),
        "ip_asn_org": telemetry.get("ip_asn_org"),
        "ip_city": telemetry.get("ip_city"),
        "ip_region": telemetry.get("ip_region"),
        "ip_country": telemetry.get("ip_country"),
    }
    # Device/Geo consistency
    if profile.get('device_fingerprint') and m['device']:
        d_pen, d_r = device_penalty(canonicalize_device_fields(m['device']), canonicalize_device_fields(profile.get('device_fingerprint') or {}))
        reasons += d_r
        risk += d_pen // 2  # softer in-session weight
    if profile.get('geo') and m['geo']:
        g_pen, g_r = geo_penalty(m['geo'], profile.get('geo') or {})
        reasons += g_r
        risk += g_pen // 2
        # City-level fallback if low accuracy
        try:
            acc = m['geo'].get('accuracy')
            if isinstance(acc, (int, float)) and acc > 500:
                cur_ip_geo = {"city": m.get("ip_city"), "region": m.get("ip_region"), "country": m.get("ip_country")}
                prof_ip_geo = profile.get('ip_geo') or {}
                c_pen, c_r = _city_fallback_penalty(cur_ip_geo, prof_ip_geo)
                # half weight in-session; subtract base 10 already added by geo_penalty
                adj = max(0, c_pen - 10)
                if adj:
                    reasons += [f"Geo fallback: {r}" for r in c_r]
                    risk += adj // 2
        except Exception:
            pass

    # IP/Networks
    ip = m['ip']
    # ASN-aware IP weighting
    ip_weight_factor = 1.0
    try:
        asn_str = None
        ip_asn = m.get('ip_asn')
        if isinstance(ip_asn, int):
            asn_str = f"AS{ip_asn}"
        elif isinstance(ip_asn, str) and ip_asn.strip():
            s = ip_asn.strip().upper()
            asn_str = s if s.startswith("AS") else f"AS{s}"
        carriers_env = os.environ.get("CARRIER_ASN_LIST", "AS55836,AS45609,AS55410,AS55824")
        carriers = {c.strip().upper() for c in carriers_env.split(',') if c.strip()}
        if asn_str and asn_str.upper() in carriers:
            ip_weight_factor = 0.3
    except Exception:
        pass
    if ip in [None, '', 'unknown']:
        reasons.append("IP missing or unknown (session)")
        risk += 3
    else:
        known_networks = set(profile.get('known_networks', []) or [])
        if known_networks and not _ip_in_prefixes(ip, list(known_networks)):
            risk += int(round(3 * ip_weight_factor))
        # Allow/Deny lists influence
        deny = os.environ.get('DENYLIST_IP_PREFIXES', '')
        allow = os.environ.get('ALLOWLIST_IP_PREFIXES', '')
        denylist = [p.strip() for p in deny.split(',') if p.strip()]
        allowlist = [p.strip() for p in allow.split(',') if p.strip()]
        try:
            if denylist and _ip_in_prefixes(ip, denylist):
                reasons.append("IP in denylist range (session)")
                risk += 20  # slightly lower weight in-session
            if allowlist and not _ip_in_prefixes(ip, allowlist):
                risk += int(round(3 * ip_weight_factor))
        except Exception:
            pass

    try:
        if ip_weight_factor < 1.0:
            reasons.append("Carrier/mobile ASN detected; down-weighted IP checks (session)")
    except Exception:
        pass

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
