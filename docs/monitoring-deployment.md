# Observability: tested design, not a deployed monitoring service

Enable with `docker compose --profile monitoring up -d`. Grafana listens on 127.0.0.1:3000 for local SSH tunnel access. Automatic Grafana dashboard provisioning includes API health, request throughput, HTTP 5xx and p95. Prometheus alerting rules exist, but alert delivery to email/Telegram must be configured separately and is **not** active by default.

Instruments:
- `rahsu_http_requests_total{method,status}` counter
- `rahsu_http_duration_seconds` histogram
- optional OTLP Django traces via Alloy
- JSON log records including request and trace IDs

The /metrics endpoint must remain internal; monitoring tools have their own private network reachability. API token logs/metrics/traces readers have fixed queries and default 1-hour log lookback, max 24 hours.

## Backups

Run `bash scripts/backup_postgres.sh /secure/backup/path` on a host with Docker. This produces a PostgreSQL custom dump and SHA256, mode 0600. It is **not encrypted** by the script: encrypt at rest/offsite, define retention, and perform a restoration test into a separate disposable database before claiming backup health.

## Important limitations
- No production deployment credentials, DNS, data importer or live alert receivers are supplied.
- Prometheus alerts are only evaluated when the monitoring profile is running.
- Tracing may include URLs from HTTP instrumentation; review privacy and sanitize URL parameters.
- Current local volumes may fill; size limits/retention and disks must be assessed on actual host.
