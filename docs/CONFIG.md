# Configuration

This document lists environment variables and settings used by FinVault.

## Core

- ENVIRONMENT: development | production
- JWT_SECRET: 32+ char secret
- POSTGRES_URI: SQLAlchemy async URL (postgresql+asyncpg://...)
- MONGODB_URI: Motor URL (mongodb://host:port) or Atlas SRV
- REDIS_URI: redis://host:port/db

## Security

- COOKIE_SECURE: 1 in production
- TRUSTED_HOSTS: comma-separated hosts
- CORS_ALLOW_ORIGINS: comma-separated origins

## Risk & Telemetry

- CARRIER_ASN_LIST: comma-separated ASNs to treat as mobile/carrier networks
- KNOWN_NETWORK_PROMOTION_THRESHOLD: distinct-day count within last 30 days to promote a prefix
- KNOWN_NETWORK_DECAY_DAYS: demote prefixes not seen for this many days
- GEOIP_CACHE_TTL_SEC: Redis TTL for IP enrichment cache

## GeoIP

- GEOIP2_ASN_DB: path to GeoLite2-ASN.mmdb (optional; autodetected in data/)
- GEOIP2_CITY_DB: path to GeoLite2-City.mmdb (optional; autodetected in data/)

Place the mmdb files under `data/` (repo root) or `backend/data/` for auto-detection.
