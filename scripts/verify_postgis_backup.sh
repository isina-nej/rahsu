#!/usr/bin/env bash
# Non-destructively check encrypted snapshot and PostgreSQL custom archive.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FILE="${1:?Usage: scripts/verify_postgis_backup.sh /path/to/backup.dump.age}"
: "${BACKUP_AGE_IDENTITY_FILE:?Set an age identity *file path* (never publish the key)}"
[[ -f "$FILE" && -s "$FILE" ]] || { echo "Missing encrypted archive." >&2; exit 2; }
[[ -f "$FILE.sha256" ]] || { echo "Missing SHA256 manifest." >&2; exit 2; }
[[ -r "$BACKUP_AGE_IDENTITY_FILE" ]] || { echo "Age identity file cannot be read." >&2; exit 2; }

command -v age >/dev/null || { echo "Install age." >&2; exit 2; }
command -v sha256sum >/dev/null || { echo "Install sha256sum." >&2; exit 2; }
# Manifest is generated with relative filename; verification works after moving
# both files together into an offline location.
DIR="$(cd "$(dirname "$FILE")" && pwd)"
NAME="$(basename "$FILE")"
(cd "$DIR" && sha256sum --check --status "$NAME.sha256") || {
  echo "Ciphertext checksum mismatch." >&2; exit 3;
}
# age verifies authenticated ciphertext; pg_restore --list verifies the
# decrypted PostgreSQL custom archive's structure WITHOUT restoring tables.
age -d -i "$BACKUP_AGE_IDENTITY_FILE" "$FILE" \
  | docker compose exec -T db pg_restore --list >/dev/null
echo "Encrypted archive integrity and PostgreSQL dump structure verified."
echo "No database was restored or modified. A separate restore drill is still required."
