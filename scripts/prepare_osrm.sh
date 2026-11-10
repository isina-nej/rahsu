#!/usr/bin/env bash
set -euo pipefail
# Offline preparation: obtain a licensed OSM PBF extract of Tehran yourself.
# Usage: scripts/prepare_osrm.sh /path/to/tehran.osm.pbf
PBF=${1:?Provide Tehran .osm.pbf}; test -f "$PBF"
mkdir -p data/osrm
if [[ "$(realpath "$PBF")" != "$(realpath -m data/osrm/tehran.osm.pbf)" ]]; then
  cp "$PBF" data/osrm/tehran.osm.pbf
fi
# Load only the OSRM image setting from the project .env, never source secrets
# as executable shell code. Environment override is supported for operators.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if [[ -z "${OSRM_IMAGE:-}" && -f .env ]]; then
  IMAGE="$(python3 - <<'PY'
from pathlib import Path
from scripts.preflight import parse_env
print(parse_env(Path(".env")).get("OSRM_IMAGE", ""))
PY
)"
else
  IMAGE="${OSRM_IMAGE:-}"
fi
IMAGE="${IMAGE:-ghcr.io/project-osrm/osrm-backend:v26.10.0-debian@sha256:55dbfd47d984c2cacd64e32901b4321c86b5ec761438e69aa053dc78698a786f}"
if [[ ! "$IMAGE" =~ @sha256:[a-f0-9]{64}$ ]]; then
  echo "OSRM image must be pinned to a SHA256 digest for graph preparation." >&2
  exit 2
fi
docker run --rm -v "$PWD/data/osrm:/data" "$IMAGE" osrm-extract -p /opt/car.lua /data/tehran.osm.pbf
docker run --rm -v "$PWD/data/osrm:/data" "$IMAGE" osrm-partition /data/tehran.osrm
docker run --rm -v "$PWD/data/osrm:/data" "$IMAGE" osrm-customize /data/tehran.osrm
