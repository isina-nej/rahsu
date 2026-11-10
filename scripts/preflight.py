#!/usr/bin/env python3
"""Fail-closed preflight for a dedicated Rahsu deployment.

This CLI checks the .env file without importing Django and without printing
secret values. It never modifies the host, environment, or database.
"""
import argparse
import os
import stat
import sys
from pathlib import Path

PLACEHOLDERS = ("replace_", "dev-only", "change_me", "changeme", "your-secret")


def parse_env(path: Path) -> dict[str, str]:
    """Parse single-line KEY=value assignments; reject unsupported duplicates."""
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            raise ValueError("invalid_env_line")
        key, value = line.split("=", 1)
        key = key.strip()
        if not key.isidentifier() or key in values:
            raise ValueError("invalid_or_duplicate_env_key")
        value = value.strip()
        if len(value) > 1 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        values[key] = value
    return values


def validate(values: dict[str, str], mode: str, permissions: int) -> list[str]:
    """Return only *names* of failures, never secret values."""
    if mode not in ("staging", "production"):
        raise ValueError("invalid_mode")
    errors = []
    if permissions & 0o077:
        errors.append("env_file_permissions_require_chmod_600")
    required = {
        "DJANGO_SECRET_KEY": 40,
        "POSTGRES_PASSWORD": 24,
        "GRAFANA_ADMIN_PASSWORD": 20,
    }
    for key, minimum in required.items():
        value = values.get(key, "")
        if len(value) < minimum or any(x in value.lower() for x in PLACEHOLDERS):
            errors.append(f"unsafe_{key.lower()}")
    ops = values.get("OPS_READ_TOKEN", "")
    if ops and (len(ops) < 32 or any(x in ops.lower() for x in PLACEHOLDERS)):
        errors.append("unsafe_ops_read_token")
    if values.get("DJANGO_DEBUG") != "0":
        errors.append("debug_must_be_disabled")
    hosts = [v.strip() for v in values.get("DJANGO_ALLOWED_HOSTS", "").split(",")]
    if not hosts or any(not host or host == "*" for host in hosts):
        errors.append("allowed_hosts_required_no_wildcard")
    if values.get("ALLOW_PUBLIC_SIGNUP", "0") != "0":
        errors.append("public_registration_must_remain_closed")
    if mode == "production":
        if values.get("TRUST_REVERSE_PROXY") != "1":
            errors.append("trusted_https_proxy_required")
        csrf = [v.strip() for v in values.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")]
        if not csrf or any(not origin.startswith("https://") for origin in csrf):
            errors.append("production_https_csrf_origin_required")
        if all(host in ("localhost", "127.0.0.1") for host in hosts):
            errors.append("production_public_host_required")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Rahsu deployment .env safety")
    parser.add_argument("--env", type=Path, default=Path(".env"))
    parser.add_argument("--mode", choices=("staging", "production"), default="staging")
    args = parser.parse_args()
    try:
        permissions = stat.S_IMODE(args.env.stat().st_mode)
        values = parse_env(args.env)
        errors = validate(values, args.mode, permissions)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"RAHSU preflight FAILED: {type(exc).__name__}", file=sys.stderr)
        return 2
    if errors:
        print("RAHSU preflight FAILED: " + ", ".join(errors), file=sys.stderr)
        return 1
    print(f"RAHSU preflight PASSED ({args.mode}); no credentials displayed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
