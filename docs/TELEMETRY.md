# Telemetry & GeoIP

## Overview

The telemetry system collects device and location data to power fraud detection, risk scoring, and advanced analytics. It includes real-time heatmap visualization and location-based pattern analysis.

## Authentication Integration

### Registration & Onboarding Flow

1. **User registers** → magic link sent for email verification
2. **Email verified** → onboarding required to establish baseline
3. **Onboarding collects** behavioral patterns, device fingerprint, geolocation
4. **Baseline established** in MongoDB behavior_profiles collection

### Login Process

1. **Client collects** device fingerprint, geolocation, behavioral data
2. **Pre-login telemetry** sent to establish baseline comparison
3. **Risk engine analyzes** all signals against stored profile
4. **Post-login updates** occur only on successful low-risk logins

### Behavioral Learning Process

- **EWMA Updates**: Typing speed, error rates, mouse dynamics on low-risk logins
- **Baseline Stabilization**: After 5 consecutive low-risk logins
- **No Learning**: From medium/high risk or failed step-ups
- **Profile Updates**: Stored in MongoDB behavior_profiles collection

### Step-up Verification

- **Medium risk detected** → additional verification required
- **Multiple options**: Magic link, security questions, ambient auth, WebAuthn
- **Successful step-up** → access granted, risk set to low
- **No profile learning** from step-up verifications

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
- **behavior_profiles**: User behavioral baselines and patterns
- **geo_events**: Location history for heatmap analytics

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
