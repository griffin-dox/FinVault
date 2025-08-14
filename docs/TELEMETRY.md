# Telemetry & GeoIP

## Pipeline

- Client sends device metrics to POST /telemetry/device
- Server extracts IP from headers and request.client
- Upserts `ip_addresses` and `devices`, links `device_ip_events`
- Enrichment: MaxMind ASN + City (via local mmdb)
  - Redis cache `geoip:<ip>` (TTL: `GEOIP_CACHE_TTL_SEC`)
  - Privacy: only store city/region/country (no IP lat/lon)

## Collections

- ip_addresses: ip, is_private, prefix, city/region/country, asn/asn_org, counters
- devices: device_hash, normalized fingerprint, counters
- device_ip_events: linkage with counters
- known_network_counters: per user/prefix per day sightings

## Analytics

- GET /telemetry/known-networks/summary?days=30
- GET /telemetry/known-networks/decay-report

## GeoIP Setup

- Place `GeoLite2-ASN.mmdb` and `GeoLite2-City.mmdb` in `data/` (repo root) or `backend/data/`.
- Optionally set `GEOIP2_ASN_DB` and `GEOIP2_CITY_DB` for explicit paths.
