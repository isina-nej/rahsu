#!/usr/bin/env bash
# Encrypted PostGIS snapshot, streamed without a plaintext dump on host disk.
set -euo pipefail
umask 077
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

: "${BACKUP_AGE_RECIPIENT:?Set an age public recipient in the environment; do not upload private identity keys}"
command -v age >/dev/null || { echo "Install age for authenticated backup encryption." >&2; exit 2; }
command -v docker >/dev/null || { echo "Install Docker Compose." >&2; exit 2; }
command -v sha256sum >/dev/null || { echo "Missing sha256sum." >&2; exit 2; }

OUTDIR="${1:-$ROOT/data/backups}"
mkdir -p "$OUTDIR"
chmod 700 "$OUTDIR"
WORKDIR="$(mktemp -d "$OUTDIR/.rahsu-backup.XXXXXX")"
trap 'rm -rf -- "$WORKDIR"' EXIT
NAME="rahsu-postgis-$(date -u +%Y%m%dT%H%M%SZ)-$$.dump.age"

# Docker provides PG env inside its own dedicated Rahsu container.
# pipefail propagates a failed pg_dump or a failed age encryption.
docker compose exec -T db sh -eu -c \
  'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --no-owner --no-privileges' \
  | age -r "$BACKUP_AGE_RECIPIENT" -o "$WORKDIR/archive.age"

[[ -s "$WORKDIR/archive.age" ]] || { echo "Backup produced no ciphertext." >&2; exit 3; }
mv -- "$WORKDIR/archive.age" "$OUTDIR/$NAME"
(cd "$OUTDIR" && sha256sum "$NAME" > "$NAME.sha256")
echo "Encrypted Rahsu PostGIS backup created: $OUTDIR/$NAME"
echo "Ciphertext checksum stored alongside backup. Verify with scripts/verify_postgis_backup.sh."
