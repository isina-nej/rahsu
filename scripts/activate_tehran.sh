#!/usr/bin/env bash
# Operator-only local staging activation: do not run against another application's DB.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
test -f .env || { echo "Create private .env (cp .env.example .env) and rotate secrets." >&2; exit 2; }
test -s data/osrm/tehran.osrm || { echo "Missing Tehran OSRM graph. Run scripts/build_tehran_dataset.sh first." >&2; exit 2; }
test -s data/osm/tehran-obstacles.geojson || { echo "Missing actual Tehran OSM obstacle export." >&2; exit 2; }
docker compose config --quiet
docker compose up -d db redis
docker compose run --rm api python manage.py migrate --noinput
docker compose run --rm api python manage.py seed_pride
docker compose run --rm -v "$ROOT/data/osm:/tehran-osm:ro" api \
  python manage.py import_osm_geojson /tehran-osm/tehran-obstacles.geojson
docker compose --profile routing up -d osrm
docker compose up -d api worker web
python3 scripts/smoke_tehran.py --api http://127.0.0.1:8000
echo "Research stack running locally. Monitoring profile and HTTPS remain opt-in."
