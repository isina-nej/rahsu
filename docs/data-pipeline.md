# End-to-end Tehran data preparation

The entire routing/fuel website is **not operational until Tehran OSM data is present**. Unlike generated examples, this pipeline produces real OSM-sourced network and obstacle inputs.

1. Download the current Iran OSM PBF manually from [Geofabrik](https://download.geofabrik.de/asia/iran.html) and validate their published checksums.
2. Install `osmium-tool` on the preparation host (Ubuntu package `osmium-tool`).
3. Run `bash scripts/prepare_tehran_data.sh /path/to/iran-latest.osm.pbf`.
4. Build OSRM MLD graph with `bash scripts/prepare_osrm.sh data/osrm/tehran.osm.pbf`. Needs Docker and sufficient RAM/storage.
5. Start PostGIS and API; run `python manage.py migrate`, then `python manage.py seed_pride`, then `python manage.py import_osm_geojson ../data/osm/tehran-obstacles.geojson` (adjust path for container).
6. Start OSRM using the Compose `routing` profile. Test with a Tehran origin/destination.
7. Record data timestamp, source URI, checksum, coverage and license in deployment notes. Never commit PBF/DEM datasets to GitHub.

OSM roads and obstacle labels are incomplete. This importer preserves reviewed manual corrections, and OSM nodes remain non-fuel-affecting until manually reviewed with road direction and names. The model does NOT infer signals' live phase or congestion. OSM/ODbL attribution applies.

**Important:** These scripts are supplied and syntax-checked, but no Tehran dataset has been downloaded or imported in this environment; those operations require a real network/host.
