# Operator runbook: activate real Tehran data and run live smoke

For a **dedicated Rahsu host**, never reuse another project's database,
Redis or operating system services.

Prerequisites: Docker Compose, osmium, official checked Geofabrik extract,
sufficient RAM/SSD for OSRM, `.env` with unique secrets and an
operator-reviewed storage/backup plan.

```bash
bash scripts/build_tehran_dataset.sh
cp .env.example .env
# edit .env using a secure editor; never commit it
bash scripts/activate_tehran.sh
```

The activation script starts PostGIS and Redis, runs migrations, seeds
the published Pride reference, imports real GeoJSON obstacles, starts the
OSRM graph and web/API/worker, and executes a **live HTTP smoke test**.
The test queries fixed Tehran coordinates and verifies real route geometry,
litre estimates, explicit uncertainty warnings and topology evidence. It
fails if OSRM is unavailable or the API has no real routes. No mock routes
are served in production. The script can be rerun and the importer preserves
approved corrections.

Run manually after preparing data, not in standard CI (the OSM dataset and
Docker services are intentionally absent in CI). HTTPS, MFA, independent
backups/restoration, immutable image pinning and operator access controls
must be completed before public production exposure. Do not claim
scientific fuel accuracy without measured Pride holdout validation.

## OSRM reproducibility

The map preparation container and `docker compose` route-serving container
now consume the same `OSRM_IMAGE` SHA256-pinned reference (default:
`ghcr.io/project-osrm/osrm-backend:v26.10.0-debian@sha256:55dbfd47d984c2cacd64e32901b4321c86b5ec761438e69aa053dc78698a786f`). This is a known registry-published v26.10 Debian image. Do not
use `:latest` during production graph rebuilds: the graph format can change.
Operators may override `OSRM_IMAGE` with another verified digest, but both
preparation and runtime must use it together and rebuilding may be necessary.

The protected production preflight rejects unpinned OSRM images.
