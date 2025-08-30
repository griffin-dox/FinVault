# Telemetry & GeoIP

## Overview

The telemetry system collects device and location data to power fraud detection, risk scoring, and advanced analytics. It includes real-time heatmap visualization and location-based pattern analysis.

## Data Pipeline

- Client sends device metrics to POST /telemetry/device
- Server extracts IP from headers and request.client
- Upserts `ip_addresses` and `devices`, links `device_ip_events`
- Enrichment: MaxMind ASN + City (via local mmdb)
  - Redis cache `geoip:<ip>` (TTL: `GEOIP_CACHE_TTL_SEC`)
  - Privacy: only store city/region/country (no IP lat/lon)

## Collections

- **ip_addresses**: IP, is_private, prefix, city/region/country, ASN/ASN_org, counters
- **devices**: Device_hash, normalized fingerprint, counters
- **device_ip_events**: Linkage with counters and timestamps
- **known_network_counters**: Per user/prefix per day sightings

## Analytics Endpoints

- GET /telemetry/known-networks/summary?days=30
- GET /telemetry/known-networks/decay-report

## Heatmap Features

### Transaction Risk Heatmap

- Endpoint: GET /admin/heatmap-data
- Visualizes high-risk transaction locations
- Color-coded by risk level and transaction volume

### Login Activity Heatmap

- Endpoint: GET /admin/login-heatmap
- Shows authentication patterns across locations
- Highlights unusual login locations and times

### User Activity Heatmap

- Endpoint: GET /admin/user-activity-heatmap
- Tracks individual user behavior patterns
- Supports time-based filtering and analysis

### Location Clustering

- Groups nearby activities for pattern detection
- Reduces noise in densely populated areas
- Improves fraud pattern recognition

## GeoIP Setup

- Place `GeoLite2-ASN.mmdb` and `GeoLite2-City.mmdb` in `data/` (repo root) or `backend/data/`
- Optionally set `GEOIP2_ASN_DB` and `GEOIP2_CITY_DB` for explicit paths
- Automatic detection with fallback to online services

## Privacy Considerations

- Precise lat/lon coordinates are never stored
- Only city/region/country level location data retained
- IP addresses hashed before storage
- Data retention policies configurable per environment
