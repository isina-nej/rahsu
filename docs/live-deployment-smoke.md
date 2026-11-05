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
