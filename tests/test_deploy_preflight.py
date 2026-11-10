"""Offline deployment guard tests; no secrets or Docker required."""
import stat
from pathlib import Path

import pytest

from scripts.preflight import parse_env, validate


@pytest.fixture
def valid() -> dict[str, str]:
    return {
        "DJANGO_SECRET_KEY": "s" * 48,
        "POSTGRES_PASSWORD": "p" * 40,
        "GRAFANA_ADMIN_PASSWORD": "g" * 32,
        "DJANGO_DEBUG": "0",
        "DJANGO_ALLOWED_HOSTS": "localhost,127.0.0.1",
        "ALLOW_PUBLIC_SIGNUP": "0",
        "TRUST_REVERSE_PROXY": "0",
        "DJANGO_CSRF_TRUSTED_ORIGINS": "http://localhost:8080",
    }


def test_private_staging_configuration_accepted(valid):
    assert validate(valid, "staging", 0o600) == []


def test_examples_and_overly_permissive_files_fail(valid):
    valid["DJANGO_SECRET_KEY"] = "REPLACE_WITH_SECURE_RANDOM_VALUE"
    errors = validate(valid, "staging", 0o644)
    assert "unsafe_django_secret_key" in errors
    assert "env_file_permissions_require_chmod_600" in errors


def test_production_requires_trusted_https_proxy(valid):
    errors = validate(valid, "production", 0o600)
    assert "trusted_https_proxy_required" in errors
    assert "production_https_csrf_origin_required" in errors
    assert "production_public_host_required" in errors
    valid.update({
        "OSRM_IMAGE": "ghcr.io/project-osrm/osrm-backend:v26.10.0-debian@sha256:55dbfd47d984c2cacd64e32901b4321c86b5ec761438e69aa053dc78698a786f",
        "TRUST_REVERSE_PROXY": "1",
        "DJANGO_ALLOWED_HOSTS": "fuel.example.org",
        "DJANGO_CSRF_TRUSTED_ORIGINS": "https://fuel.example.org",
    })
    assert validate(valid, "production", 0o600) == []


def test_rejects_debug_wildcard_and_token_shortcut(valid):
    valid.update({
        "DJANGO_DEBUG": "1",
        "DJANGO_ALLOWED_HOSTS": "*",
        "OPS_READ_TOKEN": "123456789",
    })
    errors = validate(valid, "staging", 0o600)
    assert "debug_must_be_disabled" in errors
    assert "allowed_hosts_required_no_wildcard" in errors
    assert "unsafe_ops_read_token" in errors


def test_parser_rejects_duplicate_keys(tmp_path: Path):
    file = tmp_path / ".env"
    file.write_text("DJANGO_DEBUG=0\nDJANGO_DEBUG=1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        parse_env(file)


def test_parser_supports_quoted_values(tmp_path: Path):
    file = tmp_path / ".env"
    file.write_text("FOO='has spaces'\nBAR=two\n", encoding="utf-8")
    assert parse_env(file) == {"FOO": "has spaces", "BAR": "two"}
