from __future__ import annotations
from typing import Optional, Tuple, Dict, Any
from datetime import datetime
import ipaddress
import os
from pathlib import Path

from fastapi import Request
from app.database import mongo_db, redis_client
from app.services.risk_engine import canonicalize_device_fields

from app.services.geoip import lookup_asn, lookup_city, init_geoip_readers


def get_client_ip_from_headers(request: Request) -> Tuple[Optional[str], bool]:
    """Best-effort client IP extraction. Returns (ip, from_proxy)."""
    # Prefer Cloudflare header if present
    for h in ("cf-connecting-ip", "CF-Connecting-IP"):
        ip = request.headers.get(h)
        if ip:
            return ip.strip(), True
    # Then X-Forwarded-For (left-most)
    xff = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
    if xff:
        ip = xff.split(",")[0].strip()
        return ip, True
    # Then X-Real-IP
    xri = request.headers.get("x-real-ip") or request.headers.get("X-Real-IP")
    if xri:
        return xri.strip(), True
    # Fallback to client
    client = request.client
    return (client.host if client else None), False


def ip_prefix(ip: str) -> Optional[str]:
    try:
        ip_obj = ipaddress.ip_address(ip)
        if isinstance(ip_obj, ipaddress.IPv4Address):
            return str(ipaddress.ip_network(f"{ip}/24", strict=False))
        else:
            return str(ipaddress.ip_network(f"{ip}/64", strict=False))
    except Exception:
        return None


def is_private(ip: str) -> bool:
    try:
        return ipaddress.ip_address(ip).is_private
    except Exception:
        return False


async def upsert_ip(ip: str) -> Optional[str]:
    if mongo_db is None or not ip:
        return None
    coll = mongo_db.ip_addresses
    now = datetime.utcnow()
    doc = await coll.find_one({"ip": ip})
    if doc:
        # Attempt enrichment on existing doc if missing
        update_set: Dict[str, Any] = {"last_seen": now}
        try:
            if not doc.get("is_private", False):
                # Only enrich when fields are missing
                if (not doc.get("asn") or not doc.get("asn_org")) or not any(doc.get(k) for k in ("city", "region", "country")):
                    # Try Redis cache first
                    cached = None
                    if redis_client is not None:
                        try:
                            key = f"geoip:{ip}"
                            raw = await redis_client.get(key)
                            if raw:
                                import json
                                cached = json.loads(raw)
                        except Exception:
                            cached = None
                    if cached and isinstance(cached, dict):
                        if not doc.get("asn") or not doc.get("asn_org"):
                            if cached.get("asn") is not None:
                                update_set["asn"] = cached.get("asn")
                            if cached.get("asn_org") is not None:
                                update_set["asn_org"] = cached.get("asn_org")
                        if not any(doc.get(k) for k in ("city", "region", "country")):
                            for k in ["city", "region", "region_iso", "country", "country_iso"]:
                                if cached.get(k) is not None:
                                    update_set[k] = cached.get(k)
                    else:
                        init_geoip_readers()
                        asn_part = lookup_asn(ip)
                        city_data = lookup_city(ip)
                        # Privacy filter for city_data
                        filtered = {k: city_data.get(k) for k in ["city", "region", "region_iso", "country", "country_iso"] if city_data.get(k) is not None}
                        update_set.update(asn_part)
                        update_set.update(filtered)
                        # Write to Redis cache
                        if redis_client is not None:
                            try:
                                import json
                                cache_payload = {**asn_part, **filtered}
                                await redis_client.setex(f"geoip:{ip}", int(os.getenv("GEOIP_CACHE_TTL_SEC", "86400")), json.dumps(cache_payload))
                            except Exception:
                                pass
        except Exception:
            pass
        await coll.update_one({"_id": doc["_id"]}, {"$set": update_set, "$inc": {"seen_count": 1}})
        return str(doc["_id"])  # stringified ObjectId
    # New doc: enrich on insert
    enrich: Dict[str, Any] = {}
    priv = is_private(ip)
    try:
        if not priv:
            # Try Redis cache first
            cached = None
            if redis_client is not None:
                try:
                    raw = await redis_client.get(f"geoip:{ip}")
                    if raw:
                        import json
                        cached = json.loads(raw)
                except Exception:
                    cached = None
            if cached and isinstance(cached, dict):
                enrich.update({k: cached.get(k) for k in ["asn", "asn_org"] if cached.get(k) is not None})
                for k in ["city", "region", "region_iso", "country", "country_iso"]:
                    if cached.get(k) is not None:
                        enrich[k] = cached.get(k)
            else:
                init_geoip_readers()
                asn_part = lookup_asn(ip)
                city_data = lookup_city(ip)
                # Privacy filter: exclude precise lat/lon
                filtered = {k: city_data.get(k) for k in ["city", "region", "region_iso", "country", "country_iso"] if city_data.get(k) is not None}
                enrich.update(asn_part)
                enrich.update(filtered)
                # Cache
                if redis_client is not None:
                    try:
                        import json
                        cache_payload = {**asn_part, **filtered}
                        await redis_client.setex(f"geoip:{ip}", int(os.getenv("GEOIP_CACHE_TTL_SEC", "86400")), json.dumps(cache_payload))
                    except Exception:
                        pass
    except Exception:
        pass
    res = await coll.insert_one({
        "ip": ip,
        "is_private": priv,
        "first_seen": now,
        "last_seen": now,
        "seen_count": 1,
        "prefix": ip_prefix(ip),
        **{k: v for k, v in enrich.items() if v is not None},
    })
    return str(res.inserted_id)


async def upsert_device(device: Dict[str, Any], user_id: Optional[int]) -> Tuple[Optional[str], Optional[str]]:
    if mongo_db is None or not device:
        return None, None
    dev = canonicalize_device_fields(device)
    # Compute a simple device hash from canonical fields
    try:
        import hashlib, json
        core = {k: dev.get(k) for k in ["browser", "os", "screen", "timezone"] if dev.get(k)}
        h = hashlib.sha256(json.dumps(core, sort_keys=True).encode()).hexdigest()
    except Exception:
        h = None
    now = datetime.utcnow()
    coll = mongo_db.devices
    doc = await coll.find_one({"device_hash": h}) if h else None
    if doc:
        update = {"last_seen": now}
        if user_id and not doc.get("user_id"):
            update["user_id"] = user_id
        await coll.update_one({"_id": doc["_id"]}, {"$set": update, "$inc": {"seen_count": 1}})
        return str(doc["_id"]), h
    res = await coll.insert_one({
        "user_id": user_id,
        "device_hash": h,
        "device": dev,
        "first_seen": now,
        "last_seen": now,
        "seen_count": 1,
    })
    return str(res.inserted_id), h


async def link_device_ip(device_id: Optional[str], ip_id: Optional[str]) -> None:
    if mongo_db is None or not device_id or not ip_id:
        return
    now = datetime.utcnow()
    coll = mongo_db.device_ip_events
    existing = await coll.find_one({"device_id": device_id, "ip_id": ip_id})
    if existing:
        await coll.update_one({"_id": existing["_id"]}, {"$set": {"last_seen": now}, "$inc": {"seen_count": 1}})
    else:
        await coll.insert_one({
            "device_id": device_id,
            "ip_id": ip_id,
            "first_seen": now,
            "last_seen": now,
            "seen_count": 1,
        })


async def record_telemetry(request: Request, device: Dict[str, Any], user_id: Optional[int]) -> Dict[str, Any]:
    # Extract and normalize IP
    ip, _ = get_client_ip_from_headers(request)
    device_id, device_hash = await upsert_device(device or {}, user_id)
    ip_id = await upsert_ip(ip) if ip else None
    await link_device_ip(device_id, ip_id)
    return {"device_id": device_id, "ip_id": ip_id, "device_hash": device_hash}


# ------------------------------
# Known-network promotion helpers
# ------------------------------

async def update_known_network_counter(user_id: int, ip: Optional[str]) -> None:
    """Increment per-user prefix/day counters to later promote/demote known networks.
    Uses collection 'known_network_counters' with docs:
      { user_id, prefix, day: YYYY-MM-DD, first_seen, last_seen, seen_days: int }
    """
    if mongo_db is None or not user_id or not ip:
        return
    try:
        pref = ip_prefix(ip)
        if not pref:
            return
        day = datetime.utcnow().strftime('%Y-%m-%d')
        coll = mongo_db.known_network_counters
        doc = await coll.find_one({"user_id": user_id, "prefix": pref, "day": day})
        now = datetime.utcnow()
        if doc:
            await coll.update_one({"_id": doc["_id"]}, {"$set": {"last_seen": now}})
        else:
            await coll.insert_one({
                "user_id": user_id,
                "prefix": pref,
                "day": day,
                "first_seen": now,
                "last_seen": now,
            })
    except Exception:
        # Fail-open; counters are best-effort
        pass


async def promote_known_network_if_ready(user_id: int, ip: Optional[str]) -> None:
    """Promote prefix to behavior_profiles.known_networks when seen on enough distinct days.
    KNOWN_NETWORK_PROMOTION_THRESHOLD (env, default 3) within last 30 days.
    """
    if mongo_db is None or not user_id or not ip:
        return
    try:
        pref = ip_prefix(ip)
        if not pref:
            return
        threshold = int(os.getenv("KNOWN_NETWORK_PROMOTION_THRESHOLD", "3"))
        # Count distinct days in last 30 days
        from datetime import timedelta
        today = datetime.utcnow().date()
        cutoff = today - timedelta(days=30)
        cutoff_str = cutoff.strftime('%Y-%m-%d')
        coll = mongo_db.known_network_counters
        cur = coll.find({"user_id": user_id, "prefix": pref, "day": {"$gte": cutoff_str}}, {"day": 1})
        days = {doc.get("day") async for doc in cur}
        if len(days) >= threshold:
            # Promote into behavior_profiles known_networks set
            await mongo_db.behavior_profiles.update_one({"user_id": user_id}, {"$addToSet": {"known_networks": pref}}, upsert=True)
    except Exception:
        pass


async def demote_stale_known_networks(user_id: int) -> None:
    """Demote known networks not seen for KNOWN_NETWORK_DECAY_DAYS (env, default 90)."""
    if mongo_db is None or not user_id:
        return
    try:
        decay_days = int(os.getenv("KNOWN_NETWORK_DECAY_DAYS", "90"))
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(days=decay_days)
        prof = await mongo_db.behavior_profiles.find_one({"user_id": user_id}) or {}
        prefixes = prof.get("known_networks") or []
        if not prefixes:
            return
        coll = mongo_db.known_network_counters
        to_remove = []
        for pref in prefixes:
            doc = await coll.find_one({"user_id": user_id, "prefix": pref}, sort=[("last_seen", -1)])
            last_seen = doc.get("last_seen") if doc else None
            if not last_seen or last_seen < cutoff:
                to_remove.append(pref)
        if to_remove:
            await mongo_db.behavior_profiles.update_one({"user_id": user_id}, {"$pull": {"known_networks": {"$in": to_remove}}})
    except Exception:
        pass
