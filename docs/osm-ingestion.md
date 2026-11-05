# Tehran obstacle dataset import

Download Tehran OSM data from a licensed source and generate a **bounded** Overpass JSON node export with source attribution. For a lightweight experimental run, a bounded Overpass API request can be prepared offline (obey rate limits and usage policy). The importer itself NEVER calls an external server.

```bash
cd backend
python manage.py import_osm_obstacles ../data/osm/tehran-obstacles.json
```

Accepted tags: `highway=traffic_signals`, `highway=stop`, `highway=crossing`, and `traffic_calming=bump|hump|table` on OSM *nodes* with coordinate bounds 51.05–51.75° E / 35.45–35.95° N. Other element types are deliberately ignored until a correct network topology importer is available.

Imported records are unverified. Reviewed records have precedence and are never overwritten by bulk import. Node-to-road topology, direction of travel, and coverage quality are NOT proven by proximity; the fuel engine currently does not apply obstacle costs. OSM copyright attribution and ODbL obligations apply.
