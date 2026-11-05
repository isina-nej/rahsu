# Remote observability (secured API)

The server API provides read-only, allowlisted access to telemetry without exposing Grafana, Loki, Prometheus or Tempo directly:

- `GET /api/v1/admin/observability/logs?service=api&level=error&limit=50&start=...&end=...` (max 24-hour window, UTC)
- `GET /api/v1/admin/observability/metrics/summary` (four fixed PromQL measurements)
- `GET /api/v1/admin/observability/traces/{32_hex_trace_id}`

Authenticate with an active staff session or `Authorization: Bearer <OPS_READ_TOKEN>`. The token must be 32 characters or longer. Restrict this token to approved administrators. All queries use fixed service/level allowlists, no arbitrary LogQL/PromQL. Successful accesses are logged without user query content or tokens.

Deploy telemetry backends only on an internal Compose network and terminate HTTPS at a trusted proxy. API requests without the token return 401; a staff session provides access through Django's normal authentication. Audit log records are not, by themselves, complete forensic evidence.

Prometheus metrics are visible at `/metrics/` from the internal API container and should never be forwarded through a public ingress. Protect Grafana with a strong password and MFA where feasible; database backups and periodic restore drills are required. Configure contact routing for alerts separately; no email/SMS alert delivery is enabled by default.

## Auditing access to remote monitoring

Operations API reads (including denied requests) are recorded as minimal
metadata: category, HTTP status, staff identity if authenticated, request ID and
timestamp. Neither bearer token nor IP, URLs, query text, raw location or
response payload is stored. `/api/v1/admin/observability/audit` lists the last
100 accesses to authenticated staff only, not operations service tokens.

Operations API uses an independent 120/hour per-client throttle. Audit inserts
are best-effort during database outages, with an explicit
`ops.audit.write_failed` structured log message on failure.

Before public production exposure, require MFA via a trusted identity proxy;
these database audit rows are not immutable/WORM evidence.
