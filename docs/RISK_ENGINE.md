# Risk Engine

Location: `backend/app/services/risk_engine.py`

## Overview

The risk engine provides real-time fraud detection and risk scoring for authentication and transactions. It combines multiple signals including device fingerprinting, behavioral analytics, geolocation, and network analysis to assign risk scores.

## Authentication Flow

### 1. Registration & Email Verification

1. **User registers** with email, name, phone, country
2. **Magic link sent** to email for verification
3. **Email verification** using magic link token
4. **Onboarding required** to establish behavioral baseline

### 2. Primary Login Process

1. **User enters identifier** (email/phone/name)
2. **Behavioral challenge** collected (typing/mouse/touch patterns)
3. **Device telemetry** gathered (browser, OS, screen, timezone, geolocation)
4. **Risk assessment** evaluates all signals against user profile
5. **Three outcomes** based on risk score:
   - **Low Risk (≤40)**: Direct login success + profile learning
   - **Medium Risk (41-60)**: Step-up verification required
   - **High Risk (>60)**: Login blocked

### 3. Step-up Verification (Medium Risk)

When medium risk is detected, user can choose from:

- **Magic Link**: Email verification for step-up
- **Security Question**: Answer pre-configured security question
- **Ambient Authentication**: Device/environment verification
- **WebAuthn**: If previously registered

### 4. Behavioral Learning

- **EWMA Updates**: Only on successful low-risk logins
- **Baseline Stabilization**: After 5 consecutive low-risk logins
- **No Learning**: From medium/high risk or failed step-ups
- **Profile Updates**: Typing speed, error rates, mouse dynamics, device patterns

### 5. WebAuthn Integration

- **Passwordless Option**: Available for enrolled users
- **Registration**: Separate from main login flow
- **Authentication**: Alternative to behavioral challenges

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

## Behavioral Analysis

### Typing Patterns

- **WPM (Words Per Minute)**: Z-score analysis vs user baseline
- **Error Rate**: Deviation from expected typing accuracy
- **Keystroke Timing**: Inter-keypress timing patterns
- **Adaptive baselines** using Exponential Weighted Moving Average (EWMA)

### Mouse/Touch Dynamics

- **Path Length**: Total movement distance during interaction
- **Click Patterns**: Click frequency and timing
- **Movement Velocity**: Cursor/touch movement speed analysis

### Device Fingerprinting

- **Browser Analysis**: Brand, version, and feature detection
- **OS Detection**: Operating system family identification
- **Screen Properties**: Resolution with tolerance for minor variations
- **Timezone Validation**: Geographic consistency checking

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
