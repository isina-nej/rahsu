# Operation and monitoring notes

- Secret keys are injected via `.env` (never committed). Change ALL placeholders before running.
- `docker compose up --build -d` starts DB, Redis, API, Worker and web; OSRM requires a separately produced Tehran `.osrm` dataset (see `scripts/prepare_osrm.sh`).
- `docker compose --profile monitoring up -d` adds Grafana on localhost:3000, Loki/Tempo/Alloy/Prometheus on private Docker networks.
- `OPS_READ_TOKEN` is a separate read-only bearer token for the `/api/v1/admin/observability/logs` endpoint. Set an independent strong token. Do not expose internal Loki ports publicly.
- Docker socket mount to Alloy is privileged; protect host access or replace docker autodiscovery with a safer log forwarder in production.
- No auto-scaling, long-term backups, real traffic, real obstacle extraction, or production-ready alert routing is claimed in the prototype.
- Monitoring baseline still needs hardening, tested backups, operational metrics, tracing export, and dashboard alert thresholds.
- `/api/v1/health/live` is a liveness endpoint; Prometheus needs a real `/metrics` exporter before metric collection is operational.
