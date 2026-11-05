#!/usr/bin/env bash
set -euo pipefail
# Offline preparation: obtain a licensed OSM PBF extract of Tehran yourself.
# Usage: scripts/prepare_osrm.sh /path/to/tehran.osm.pbf
PBF=${1:?Provide Tehran .osm.pbf}; test -f "$PBF"
mkdir -p data/osrm
if [[ "$(realpath "$PBF")" != "$(realpath -m data/osrm/tehran.osm.pbf)" ]]; then
  cp "$PBF" data/osrm/tehran.osm.pbf
fi
IMAGE=ghcr.io/project-osrm/osrm-backend:latest
# Containerized OSRM must be pinned to a verified digest for production use.
docker run --rm -v "$PWD/data/osrm:/data" "$IMAGE" osrm-extract -p /opt/car.lua /data/tehran.osm.pbf
docker run --rm -v "$PWD/data/osrm:/data" "$IMAGE" osrm-partition /data/tehran.osrm
docker run --rm -v "$PWD/data/osrm:/data" "$IMAGE" osrm-customize /data/tehran.osrm
