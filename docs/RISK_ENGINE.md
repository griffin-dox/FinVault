# Risk Engine

Location: `backend/app/services/risk_engine.py`

## Overview

The risk engine provides real-time fraud detection and risk scoring for authentication and transactions. It combines multiple signals including device fingerprinting, behavioral analytics, geolocation, and network analysis to assign risk scores.

## Signals

- **Device**: Browser brand + major version, OS family, screen resolution (±100px tolerance), timezone
- **Geo**: Browser geolocation with accuracy; fallback to IP city/region/country when accuracy > 500m or missing
- **Behavior**: Typing and mouse dynamics vs per-user baselines
- **Networks**: Deny/allow lists, known networks per user
- **Location Analytics**: Real-time location clustering and fraud pattern detection

## Risk Scoring Thresholds

- **Low Risk**: ≤ 40 points
- **Medium Risk**: 41–60 points
- **High Risk**: > 60 points

## Advanced Features

### Carrier ASN-aware Weighting

- Environment variable: `CARRIER_ASN_LIST`
- When current IP ASN is in this list, IP-based nudges are down-weighted (factor 0.3)

### City-level Fallback

- When browser geo accuracy > 500m or missing:
  - Same city: +0 points
  - Same region: +3 points
  - Same country, different region: +7 points
  - Different country or no baseline: +10–15 points

### Known Networks

- Promotion after `KNOWN_NETWORK_PROMOTION_THRESHOLD` distinct days in last 30 days
- Demotion after `KNOWN_NETWORK_DECAY_DAYS` without sightings

### Heatmap Analytics

The risk engine powers advanced heatmap visualization features:

- **Transaction Risk Heatmap**: Visualizes high-risk transaction locations
- **Login Activity Heatmap**: Shows authentication patterns and anomalies
- **User Activity Heatmap**: Tracks user behavior across locations
- **Location Clustering**: Groups nearby activities for pattern analysis

## Configuration

```bash
# Risk thresholds
CARRIER_ASN_LIST=AS55836,AS45609,AS55410,AS55824
KNOWN_NETWORK_PROMOTION_THRESHOLD=3
KNOWN_NETWORK_DECAY_DAYS=90
GEOIP_CACHE_TTL_SEC=86400

# GeoIP databases
GEOIP2_ASN_DB=backend/data/GeoLite2-ASN.mmdb
GEOIP2_CITY_DB=backend/data/GeoLite2-City.mmdb
```

## Extending the Risk Engine

- Add new features under `app/services/`, keep routers thin
- Gate risky changes behind environment flags when needed
- Use the heatmap endpoints for visualization and monitoring
