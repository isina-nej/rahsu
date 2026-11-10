# Auditable OSM obstacle import provenance

`python manage.py import_osm_geojson /data/osm/tehran-obstacles.geojson`
now performs an atomic, checksum-recorded import into PostGIS.

The `geo.ObstacleImportBatch` table stores:
- SHA-256 hash of the exact GeoJSON bytes
- source basename (not the operator's private directory path)
- insertion timestamp, recognized OSM node count
- created, updated and manually reviewed-preserved counts

An empty or unsupported GeoJSON export fails explicitly rather than giving
a misleading successful "0 obstacles" import. Moderated corrections and
deletion tombstones retain priority over imported OSM data.

The staff/token-scoped `/api/v1/admin/observability/readiness` endpoint
exposes the last import hash and time to facilitate scientific reproducibility.
This fingerprint is **not** a cryptographically signed publisher attestation
and does not guarantee OSM completeness or OSRM graph synchronization.
The operator should record the matching Tehran extract and route graph hashes
and rebuild both from the same official PBF.
