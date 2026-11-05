# Session authentication for optional route history

The project can estimate anonymous routes without persisting locations. To save a route and submit measured fuel, a user must sign in and explicitly set `save_history=true` for that route.

Use `GET /api/v1/auth/csrf/` to obtain a CSRF token and send it in `X-CSRFToken` on all state-changing session requests. A cookie session is issued by `POST /api/v1/auth/login/`. `GET /api/v1/auth/me/` returns status; `POST /api/v1/auth/logout/` clears the session.

Registration is **disabled by default** (`ALLOW_PUBLIC_SIGNUP=0`). The operator can create participants through Django admin or enable signup with `ALLOW_PUBLIC_SIGNUP=1` after reviewing abuse controls, terms, privacy and user deletion workflows.

Never store user passwords, sessions, exact origin/destination coordinates or submitted personal notes in application logs. Route history is saved only with opt-in, and observation records require explicit consent. Production must use HTTPS with secure cookies and appropriate CSRF trusted origins.
