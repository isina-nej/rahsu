# On-demand Persian geocoding

The app supports clicking the map without geocoder dependencies. Optionally configure `GEOCODER_BASE_URL` to a **self-hosted or commercially licensed** Nominatim-compatible instance. The API does one request per submitted query, NOT keystroke autocomplete.

`GET /api/v1/geocode/?q=...` returns a maximum of six results within Tehran. Cache TTL is one day. The anonymous endpoint has DRF rate limits; the additional geocoder lock requires a shared distributed cache if deployed with multiple API workers.

Do not set `GEOCODER_BASE_URL` to a public server in production without verifying usage policy, traffic caps, required attribution, contact details and shared throttling. No key or external URL is passed from frontend users.
