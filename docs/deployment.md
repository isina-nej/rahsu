# Deployment strategy

## Continuous Integration
CI runs syntax/lint checks, domain tests, frontend build, Docker Compose validation and a PostGIS migration job. Green CI does **not** imply scientific accuracy of fuel estimates.

## Continuous Delivery
The `Publish OCI Images` workflow runs on a version tag (`v*`) or manual dispatch and publishes immutable-SHA images to GHCR. It does **not** deploy to production, which would require a reviewed environment, HTTPS domain, secrets, database backup and actual Tehran OSRM dataset.

## Local startup

```bash
cp .env.example .env
# replace all placeholder passwords and secrets
docker compose up -d --build
docker compose exec api python manage.py migrate
docker compose exec api python manage.py seed_pride
```

Routing depends on a privately provisioned OSRM graph at `data/osrm/tehran.osrm`, with the `routing` profile enabled. Monitoring stack is an opt-in `monitoring` profile. No production deployment has been executed or verified.

## Operational security

- Keep PostGIS, Redis, OSRM, Loki, Tempo and Prometheus on private networks.
- Do not expose the admin endpoint or observation data without MFA and access controls.
- Rotate secrets; back up the database and run restore drills; disable debug.
- Use a trusted licensed tile provider and OSM attribution.
- Pin image digests and dependency lockfiles before production promotion.
