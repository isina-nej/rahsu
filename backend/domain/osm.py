"""Pure conversion of a bounded Overpass JSON response to known obstacle nodes.

This does NOT infer stop duration or confirm a lane/direction match.
Only source-tagged nodes are accepted, never fabricated from missing data.
"""
from dataclasses import dataclass
from math import isfinite

BOUNDING_BOX = (51.05, 35.45, 51.75, 35.95)
TRAFFIC_CALMING = {'bump':'bump', 'hump':'hump', 'table':'hump'}
HIGHWAY = {'traffic_signals':'traffic_signals', 'stop':'stop', 'crossing':'crossing'}

@dataclass(frozen=True)
class OSMObstacle:
    osm_id: int
    kind: str
    lat: float
    lon: float

def parse_osm_obstacles(data: dict) -> list[OSMObstacle]:
    """Parse Overpass node elements, preserving OSM IDs and provenance."""
    if not isinstance(data, dict) or not isinstance(data.get('elements'), list):
        raise ValueError('Invalid Overpass JSON response')
    results: dict[int, OSMObstacle] = {}
    for el in data['elements']:
        if not isinstance(el, dict) or el.get('type') != 'node':
            continue
        tags = el.get('tags')
        if not isinstance(tags, dict):
            continue
        kind = TRAFFIC_CALMING.get(tags.get('traffic_calming')) or HIGHWAY.get(tags.get('highway'))
        if not kind:
            continue
        try:
            oid = int(el['id']);lat=float(el['lat']);lon=float(el['lon'])
        except (TypeError, KeyError, ValueError):
            continue
        if oid <= 0 or not (isfinite(lat) and isfinite(lon)):
            continue
        if not (BOUNDING_BOX[0] <= lon <= BOUNDING_BOX[2] and BOUNDING_BOX[1] <= lat <= BOUNDING_BOX[3]):
            continue
        results[oid] = OSMObstacle(oid, kind, lat, lon)
    return list(results.values())
