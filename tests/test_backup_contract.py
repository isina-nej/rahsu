"""Backup/restore protections must remain visible in review."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def test_postgis_backups_are_encrypted_without_plaintext_intermediate():
    script=(ROOT/'scripts/backup_postgis.sh').read_text(encoding='utf-8')
    assert 'set -euo pipefail' in script
    assert 'umask 077' in script
    assert 'pg_dump' in script
    assert '| age -r "$BACKUP_AGE_RECIPIENT" -o' in script
    assert 'sha256sum' in script
    assert 'pg_dump -f' not in script


def test_verify_is_non_destructive_and_checks_checksum_and_archive():
    script=(ROOT/'scripts/verify_postgis_backup.sh').read_text(encoding='utf-8')
    assert 'sha256sum --check --status' in script
    assert 'age -d -i "$BACKUP_AGE_IDENTITY_FILE"' in script
    assert 'pg_restore --list' in script
    assert 'pg_restore --clean' not in script
    assert 'dropdb' not in script


def test_generated_data_and_backups_cannot_be_committed_by_default():
    ignore=(ROOT/'.gitignore').read_text(encoding='utf-8')
    assert '\ndata/\n' in ignore
    assert '*.age' in ignore
