# Risk Engine

Location: `backend/app/services/risk_engine.py`

## Signals

- Device: browser brand + major version, OS family, screen with ±100px tolerance, timezone
- Geo: browser geolocation with accuracy; fallback to IP city/region/country when accuracy > 500m or missing
- Behavior: typing and mouse dynamics vs per-user baselines
- Networks: deny/allow lists, known networks per user

## Thresholds

- low ≤ 40, medium 41–60, high > 60

## Carrier ASN-aware weighting

- Env: `CARRIER_ASN_LIST`
- When current IP ASN is in this list, IP-based nudges are down-weighted (factor 0.3).

## City-level fallback

- When browser geo accuracy > 500m or missing:
  - same city: +0
  - same region: +3
  - same country, different region: +7
  - different country or no baseline: +10–15

## Known networks

- Promotion after `KNOWN_NETWORK_PROMOTION_THRESHOLD` distinct days in last 30 days
- Demotion after `KNOWN_NETWORK_DECAY_DAYS` without sightings

## Extending

- Add new features under services, keep routers thin
- Gate risky changes behind env flags when needed
