#!/usr/bin/env bash
# Download the official Iran OSM extract, verify publisher MD5, produce SHA256.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-$ROOT/data/downloads/iran-latest.osm.pbf}"
URL="https://download.geofabrik.de/asia/iran-latest.osm.pbf"
for executable in curl md5sum sha256sum awk; do
  command -v "$executable" >/dev/null || { echo "Missing $executable" >&2; exit 2; }
done
mkdir -p "$(dirname "$OUT")"
TMP="$(mktemp -d "$(dirname "$OUT")/.rahsu.XXXXXX")"
trap 'rm -rf -- "$TMP"' EXIT
curl -fL --retry 4 --connect-timeout 15 --max-time 120 -sS "$URL.md5" -o "$TMP/checksum"
EXPECTED="$(grep -Eo '^[0-9a-fA-F]{32}' "$TMP/checksum" | head -n 1)"
if [[ ! "$EXPECTED" =~ ^[0-9a-fA-F]{32}$ ]]; then echo "Invalid publisher checksum" >&2; exit 2; fi
if [[ ! -f "$OUT" ]] || ! printf '%s  %s\n' "$EXPECTED" "$OUT" | md5sum -c --status; then
  curl -fL --retry 4 --connect-timeout 15 --max-time 3600 -sS "$URL" -o "$TMP/iran.osm.pbf"
  printf '%s  %s\n' "$EXPECTED" "$TMP/iran.osm.pbf" | md5sum -c --status || {
    echo "Checksum mismatch; refusing unverified data" >&2; exit 3;
  }
  mv -f "$TMP/iran.osm.pbf" "$OUT"
fi
sha256sum "$OUT" > "$OUT.sha256"
echo "Verified: $OUT"
