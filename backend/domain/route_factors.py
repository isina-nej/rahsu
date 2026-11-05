"""Conservative geographic obstacle projection onto a real OSRM route.

Coordinates follow GeoJSON lon/lat order. Approximate proximity is evidence
ONLY: without reviewer confirmation of road/direction it is not a fuel input.
"""
from dataclasses import dataclass
from math import cos, hypot, radians
from unicodedata import normalize

METERS_PER_DEGREE = 111_195.0


@dataclass(frozen=True)
class RoadStep:
    name: str
    coordinates: tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class ObstaclePoint:
    id: int
    kind: str
    lon: float
    lat: float
    verified: bool = False
    road_name: str = ""
    direction: str = "unknown"
    source: str = "osm"
    osm_type: str = ""
    osm_id: int | None = None


@dataclass(frozen=True)
class ProjectedObstacle:
    id: int
    kind: str
    at_m: float
    offset_m: float
    usable_for_fuel: bool
    reason: str


def _normalized(name: str) -> str:
    return " ".join(normalize("NFKC", name).replace("ي", "ی").replace("ك", "ک").lower().split())


def project_point(
    point: tuple[float, float], line: tuple[tuple[float, float], ...]
) -> tuple[float, float, float]:
    """Return (offset metres, along-line metres, total polyline metres)."""
    if len(line) < 2:
        raise ValueError("Polyline requires at least two positions")
    ref_lat = radians(point[1])
    scale_x = METERS_PER_DEGREE * cos(ref_lat)
    scale_y = METERS_PER_DEGREE
    px, py = point[0] * scale_x, point[1] * scale_y
    length = 0.0
    best = (float("inf"), 0.0)
    for a, b in zip(line, line[1:]):
        ax, ay = a[0] * scale_x, a[1] * scale_y
        bx, by = b[0] * scale_x, b[1] * scale_y
        dx, dy = bx - ax, by - ay
        square = dx * dx + dy * dy
        segment = square ** 0.5
        t = min(1.0, max(0.0, ((px - ax) * dx + (py - ay) * dy) / square)) if square else 0.0
        distance = hypot(px - (ax + t * dx), py - (ay + t * dy))
        if distance < best[0]:
            best = (distance, length + t * segment)
        length += segment
    return best[0], best[1], length


def match_obstacles(
    route: tuple[tuple[float, float], ...],
    route_distance_m: float,
    road_steps: tuple[RoadStep, ...],
    obstacles: list[ObstaclePoint],
    max_offset_m: float = 12.0,
    route_osm_nodes: tuple[int, ...] = (),
) -> list[ProjectedObstacle]:
    """Topology-match OSM calming nodes; review directional traffic controls.

    Automatic OSM bump/hump slowdown is eligible ONLY when the route really
    traverses the same OSM node ID and the geographic offset is plausible.
    Signals, stop signs and crossings remain evidence-only until reviewed;
    passing a shared intersection node alone does not prove the approach.
    """
    projected: list[ProjectedObstacle] = []
    traversed = set(route_osm_nodes)
    for ob in obstacles:
        offset, along, length = project_point((ob.lon, ob.lat), route)
        if offset > max_offset_m or not length:
            continue
        on_named_step = False
        if ob.road_name:
            for step in road_steps:
                if _normalized(step.name) != _normalized(ob.road_name) or len(step.coordinates) < 2:
                    continue
                step_offset, _, _ = project_point((ob.lon, ob.lat), step.coordinates)
                if step_offset <= max_offset_m:
                    on_named_step = True
                    break
        auto_calming = bool(
            ob.source == "osm" and ob.kind in ("bump", "hump")
            and ob.osm_type == "node" and ob.osm_id is not None
            and ob.osm_id in traversed
        )
        reviewed = bool(ob.verified and ob.source == "manual"
                        and ob.direction == "both" and on_named_step)
        usable = auto_calming or reviewed
        if auto_calming:
            reason = "osm_node_on_traversed_route"
        elif reviewed:
            reason = "reviewed_named_road_bidirectional"
        elif not ob.verified:
            reason = "not_reviewed_or_not_on_traversed_osm_nodes"
        else:
            reason = "road_or_direction_not_confirmed"
        projected.append(ProjectedObstacle(
            ob.id, ob.kind, min(route_distance_m, route_distance_m * along / length),
            round(offset, 2), usable, reason
        ))
    return sorted(projected, key=lambda item: (item.at_m, item.id))
