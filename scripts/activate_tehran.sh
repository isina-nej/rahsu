#!/usr/bin/env bash
# Operator-only local staging activation: do not run against another application's DB.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
test -f .env || { echo "Create private .env (cp .env.example .env) and rotate secrets." >&2; exit 2; }
# An MLD graph is a *set* of .osrm.* artifacts, not necessarily a
# standalone nonempty tehran.osrm base file.
for artifact in data/osrm/tehran.osrm.partition data/osrm/tehran.osrm.cells; do
  [[ -s "$artifact" ]] || {
    echo "Missing MLD graph artifact: $artifact; run scripts/build_tehran_dataset.sh." >&2
    exit 2
  }
done
test -s data/osm/tehran-obstacles.geojson || { echo "Missing actual Tehran OSM obstacle export." >&2; exit 2; }
python3 scripts/preflight.py --env .env --mode staging
docker compose config --quiet
docker compose up -d db redis
docker compose run --rm api python manage.py migrate --noinput
docker compose run --rm api python manage.py seed_pride
docker compose run --rm -v "$ROOT/data/osm:/tehran-osm:ro" api \
  python manage.py import_osm_geojson /tehran-osm/tehran-obstacles.geojson
docker compose --profile routing up -d osrm
docker compose up -d api worker web
# Wait for actual API/OSRM readiness instead of racing Docker startup.
for attempt in $(seq 1 15); do
  if python3 scripts/smoke_tehran.py --api http://127.0.0.1:8000; then
    echo "Research stack running locally. HTTPS and scientific validation are separate."
    exit 0
  fi
  echo "Live smoke not yet successful (attempt $attempt/15)." >&2
  if [[ "$attempt" -lt 15 ]]; then sleep 3; fi
done
echo "Tehran live smoke failed. Inspect docker compose logs; no readiness claimed." >&2
exit 1
