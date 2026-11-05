#!/usr/bin/env bash
# Explicit user-run extraction from a locally downloaded licensed Geofabrik Iran PBF.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PBF="${1:?Usage: scripts/prepare_tehran_data.sh /path/to/iran-latest.osm.pbf}"
test -f "$PBF" || { echo "Input .osm.pbf not found" >&2; exit 1; }
command -v osmium >/dev/null || { echo "Install osmium-tool first" >&2; exit 1; }
mkdir -p data/osrm data/osm
echo "Preparing Tehran complete-ways extract..."
osmium extract --strategy=complete_ways --bbox=51.05,35.45,51.75,35.95 \
  "$PBF" --output=data/osrm/tehran.osm.pbf --overwrite
echo "Filtering tagged obstacle nodes..."
osmium tags-filter data/osrm/tehran.osm.pbf \
  n/highway=traffic_signals n/highway=stop n/highway=crossing \
  n/traffic_calming --output=data/osm/tehran-obstacle-nodes.osm.pbf --overwrite
osmium export data/osm/tehran-obstacle-nodes.osm.pbf \
  --output=data/osm/tehran-obstacles.geojson --output-format=geojson --overwrite
sha256sum data/osrm/tehran.osm.pbf data/osm/tehran-obstacles.geojson \
  > data/osm/tehran-import.sha256
echo "Prepared network and obstacle dataset. Import GeoJSON with management command."
echo "Run scripts/prepare_osrm.sh data/osrm/tehran.osm.pbf to build graph."
