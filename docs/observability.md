# Remote observability (secured API)

The server API provides read-only, allowlisted access to telemetry without exposing Grafana, Loki, Prometheus or Tempo directly:

- `GET /api/v1/admin/observability/logs?service=api&level=error&limit=50&start=...&end=...` (max 24-hour window, UTC)
- `GET /api/v1/admin/observability/metrics/summary` (four fixed PromQL measurements)
- `GET /api/v1/admin/observability/traces/{32_hex_trace_id}`

Authenticate with an active staff session or `Authorization: Bearer <OPS_READ_TOKEN>`. The token must be 32 characters or longer. Restrict this token to approved administrators. All queries use fixed service/level allowlists, no arbitrary LogQL/PromQL. Successful accesses are logged without user query content or tokens.

Deploy telemetry backends only on an internal Compose network and terminate HTTPS at a trusted proxy. API requests without the token return 401; a staff session provides access through Django's normal authentication. Audit log records are not, by themselves, complete forensic evidence.

Prometheus metrics are visible at `/metrics/` from the internal API container and should never be forwarded through a public ingress. Protect Grafana with a strong password and MFA where feasible; database backups and periodic restore drills are required. Configure contact routing for alerts separately; no email/SMS alert delivery is enabled by default.
