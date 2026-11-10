# Deployment preflight and bounded startup

The operator should create **unique** credentials, restrict the file to
`chmod 600 .env` and validate before enabling the stack:

```bash
cp .env.example .env
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
# Insert separately generated values for Django, Postgres and Grafana.
chmod 600 .env
python3 scripts/preflight.py --env .env --mode staging
bash scripts/activate_tehran.sh
```

Do not paste real credentials into this chat, GitHub Issues, logs or commits.
The preflight checks passwords and production-related HTTPS/CSRF configuration
without printing secret values; it is **not** a security audit. A production
deployment should use `--mode production` and enforce HTTPS/MFA at an
operator-owned identity proxy.

Startup waits up to fifteen short retry intervals for the actual
`/health/live`, `/health/ready` and fuel routing response. A failure
terminates nonzero. The services may remain running after an unsuccessful
smoke check to support on-host diagnosis.

The scripts do not provision a server, purchase infrastructure, provide
reverse-proxy TLS certificates or collect real Pride calibration datasets.
