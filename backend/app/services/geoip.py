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
        raw = _ASN_READER.get(ip)
        rec: Dict[str, Any] = raw if isinstance(raw, dict) else {}
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
        raw = _CITY_READER.get(ip)
        rec: Dict[str, Any] = raw if isinstance(raw, dict) else {}

        city_name: Optional[str] = None
        city_val = rec.get("city")
        if isinstance(city_val, dict):
            names = city_val.get("names")
            if isinstance(names, dict):
                en_name = names.get("en")
                if isinstance(en_name, str):
                    city_name = en_name

        country: Optional[str] = None
        country_iso: Optional[str] = None
        country_val = rec.get("country")
        if isinstance(country_val, dict):
            c_names = country_val.get("names")
            if isinstance(c_names, dict):
                en_country = c_names.get("en")
                if isinstance(en_country, str):
                    country = en_country
            iso_val = country_val.get("iso_code")
            if isinstance(iso_val, str):
                country_iso = iso_val

        region: Optional[str] = None
        region_iso: Optional[str] = None
        subs_val = rec.get("subdivisions")
        if isinstance(subs_val, list) and subs_val:
            first = subs_val[0]
            if isinstance(first, dict):
                s_names = first.get("names")
                if isinstance(s_names, dict):
                    en_region = s_names.get("en")
                    if isinstance(en_region, str):
                        region = en_region
                iso = first.get("iso_code")
                if isinstance(iso, str):
                    region_iso = iso

        lat: Optional[float] = None
        lon: Optional[float] = None
        loc_val = rec.get("location")
        if isinstance(loc_val, dict):
            lat_val = loc_val.get("latitude")
            lon_val = loc_val.get("longitude")
            if isinstance(lat_val, (int, float)):
                lat = float(lat_val)
            if isinstance(lon_val, (int, float)):
                lon = float(lon_val)

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
