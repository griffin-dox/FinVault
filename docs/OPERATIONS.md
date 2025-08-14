# Operations

## Health & Monitoring

- GET /health returns backend status
- Consider adding Mongo/Redis checks and exporting Prometheus metrics (future)

## Data Retention

- Geo events TTL 30 days (`geo_events`)
- Aggregated tiles 180 days (`geo_tiles_agg`)

## Cleanup

- See `docs/CLEANUP_CHECKLIST.md` and `docs/OPERATIONS_DATA_WIPE.md`

## Incident Response

- See `docs/SECURITY.md`
