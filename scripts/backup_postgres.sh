#!/usr/bin/env bash
# Operator-run encrypted-at-rest postgres backup; secrets are NEVER printed.
set -euo pipefail
cd "$(dirname "$0")/.."
OUTDIR="${1:-./backups}"
mkdir -p "$OUTDIR"
chmod 700 "$OUTDIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TEMP="$(mktemp "$OUTDIR/.rahsu-$STAMP-XXXXXXXX")"
trap 'rm -f "$TEMP"' EXIT
docker compose exec -T db sh -c 'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --no-owner' > "$TEMP"
test -s "$TEMP"
chmod 600 "$TEMP"
TARGET="$OUTDIR/rahsu-$STAMP.dump"
mv "$TEMP" "$TARGET"
sha256sum "$TARGET" > "$TARGET.sha256"
chmod 600 "$TARGET.sha256"
echo "Backup saved. Encrypt it before offsite upload: $TARGET"
