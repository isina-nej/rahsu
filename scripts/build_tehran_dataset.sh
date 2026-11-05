#!/usr/bin/env bash
# One-command reproducible Tehran OSM + OSRM preparation (operator-run).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PBF="${IRAN_PBF:-$ROOT/data/downloads/iran-latest.osm.pbf}"
if [[ "${SKIP_IRAN_DOWNLOAD:-0}" != "1" ]]; then
  bash scripts/download_iran_osm.sh "$PBF"
fi
[[ -s "$PBF" ]] || { echo "Missing verified OSM input: $PBF" >&2; exit 2; }
command -v osmium >/dev/null || { echo "Install osmium-tool first." >&2; exit 2; }
command -v docker >/dev/null || { echo "Install Docker first." >&2; exit 2; }
bash scripts/prepare_tehran_data.sh "$PBF"
bash scripts/prepare_osrm.sh data/osrm/tehran.osm.pbf
echo "Tehran OSRM graph and OSM obstacle GeoJSON are prepared."
echo "Start Django/PostGIS and import obstacles as described in docs/data-pipeline.md."
