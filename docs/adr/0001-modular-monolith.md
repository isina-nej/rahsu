# ADR-0001 — Modular monolith with external routing and observability

Status: accepted for initial research MVP

Context: The Tehran Pride project needs reproducible model experiments, geospatial data and a protected operations interface with manageable hosting costs.

Decision:
- Django/DRF modular monolith for business APIs and permissions
- Pure Python `domain/` for mathematical models
- PostGIS for geospatial records
- OSRM as a provider adapter, replaceable by alternative routing engines
- React+MapLibre for the map UI
- OpenTelemetry, Loki, Tempo, Prometheus and Grafana for diagnostics

Consequences:
- Faster tests and simple deploys compared with per-feature microservices.
- Hard module boundaries required to avoid a big-ball-of-mud.
- No truth claims about missing Tehran obstacle, traffic, or fuel calibration datasets.
- Split out independent services only after measured performance needs.
