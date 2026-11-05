# Infrastructure hardening guide

Backend static files are collected during Docker image build with WhiteNoise; Django admin is reverse-proxied at `/admin/` from the web container. The built-in `/api/v1/auth/*` forms use session cookies and explicit CSRF tokens.

When `REDIS_URL` is available, Django's native RedisCache is shared by all API workers. This supports geocoder caching and distributed rate limiting; Redis loss should surface as a service fault, not be masked as a false cache hit. Development without Redis uses the default local memory cache.

Set `DJANGO_ALLOWED_HOSTS`, `DJANGO_CORS_ORIGINS`, `DJANGO_CSRF_TRUSTED_ORIGINS` and secure secrets for your actual domain. Terminate HTTPS at a trusted reverse proxy, and set `TRUST_REVERSE_PROXY=1` only if proxy forwarding is controlled by the operator. Never publish raw PostGIS, Redis, Loki, Prometheus or OSRM ports.

The project has *not* been production-deployed. CI validates Django + PostGIS migrations, source tests and Compose config; the actual container startup, static file delivery and remote HTTPS setup require a staging smoke test on a real host.
