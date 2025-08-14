from __future__ import annotations
from typing import Dict, Any, Optional
from pathlib import Path
import os

# Lazy-initialized readers
_ASN_READER = None
_CITY_READER = None


def _candidate_data_dirs() -> list[Path]:
    dirs: list[Path] = []
    try:
        # .../backend/app/services/geoip.py -> repo root is parents[3]
        repo_root = Path(__file__).resolve().parents[3]
        dirs.append(repo_root / "data")               # FinVault/data
        dirs.append(repo_root / "backend" / "data")   # FinVault/backend/data
    except Exception:
        pass
    return dirs


def init_geoip_readers() -> None:
    global _ASN_READER, _CITY_READER
    if _ASN_READER is not None or _CITY_READER is not None:
        return
    asn_path = os.getenv("GEOIP2_ASN_DB")
    city_path = os.getenv("GEOIP2_CITY_DB")
    if not asn_path or not city_path:
        for d in _candidate_data_dirs():
            if not asn_path:
                p = d / "GeoLite2-ASN.mmdb"
                if p.exists():
                    asn_path = str(p)
            if not city_path:
                p = d / "GeoLite2-City.mmdb"
                if p.exists():
                    city_path = str(p)
    try:
        if asn_path and Path(asn_path).exists():
            import maxminddb  # type: ignore
            _ASN_READER = maxminddb.open_database(asn_path)
    except Exception:
        _ASN_READER = None
    try:
        if city_path and Path(city_path).exists():
            import maxminddb  # type: ignore
            _CITY_READER = maxminddb.open_database(city_path)
    except Exception:
        _CITY_READER = None


def lookup_asn(ip: str) -> Dict[str, Any]:
    init_geoip_readers()
    if not ip or _ASN_READER is None:
        return {}
    try:
        rec = _ASN_READER.get(ip) or {}
        return {
            "asn": rec.get("autonomous_system_number"),
            "asn_org": rec.get("autonomous_system_organization"),
        }
    except Exception:
        return {}


def lookup_city(ip: str) -> Dict[str, Any]:
    init_geoip_readers()
    if not ip or _CITY_READER is None:
        return {}
    try:
        rec = _CITY_READER.get(ip) or {}
        city_name = ((rec.get("city") or {}).get("names") or {}).get("en")
        country = ((rec.get("country") or {}).get("names") or {}).get("en")
        country_iso = (rec.get("country") or {}).get("iso_code")
        subs = rec.get("subdivisions") or []
        region = None
        region_iso = None
        if subs:
            region = ((subs[0].get("names") or {}).get("en"))
            region_iso = subs[0].get("iso_code")
        loc = rec.get("location") or {}
        lat = loc.get("latitude")
        lon = loc.get("longitude")
        return {
            "city": city_name,
            "region": region,
            "region_iso": region_iso,
            "country": country,
            "country_iso": country_iso,
            "latitude": lat,
            "longitude": lon,
        }
    except Exception:
        return {}


def geoip_lookup(ip: str) -> Dict[str, Any]:
    out = {}
    if not ip:
        return out
    out.update(lookup_asn(ip))
    out.update(lookup_city(ip))
    return out
