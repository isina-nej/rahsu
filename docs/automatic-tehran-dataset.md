# Automated real Tehran OSM preparation

The script downloads the official Geofabrik Iran extract using HTTPS,
checks the **publisher MD5 transfer checksum** and creates a local SHA256
manifest. MD5 is only a transfer-integrity check, not a signed artifact.
See https://download.geofabrik.de/asia/iran.html

Prerequisites: Docker, `osmium-tool`, curl, enough free disk and RAM for
an OSRM MLD graph build. Network and hardware requirements must be met
on the operator host; CI does not download a 200+ MB dataset.

```bash
bash scripts/build_tehran_dataset.sh
# Or with already checked source:
SKIP_IRAN_DOWNLOAD=1 IRAN_PBF=/path/iran-latest.osm.pbf bash scripts/build_tehran_dataset.sh
```

This generates a Tehran OSRM dataset and OSM obstacle GeoJSON.
Then follow `docs/data-pipeline.md` for Django/PostGIS import, seed and
live-route smoke testing. No result is considered accurate until real
Tehran road data and separate Pride fuel calibration have been validated.

Do not commit geospatial datasets or collected driver observations.
Always preserve OSM attribution and licensing.
