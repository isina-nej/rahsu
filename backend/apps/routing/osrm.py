"""OSRM adapter: true routes and turn-by-turn named-road evidence."""
from dataclasses import dataclass
from math import isfinite
import httpx
from domain.route_factors import RoadStep

class RoutingError(Exception):
    pass

@dataclass(frozen=True)
class RouteCandidate:
    distance_m: float
    duration_s: float
    coordinates: tuple[tuple[float, float], ...]
    road_steps: tuple[RoadStep, ...] = ()

class OsrmClient:
    def __init__(self, base_url: str, timeout_s: float = 8.0):
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s

    def candidates(self, origin: tuple[float, float], dest: tuple[float, float]) -> list[RouteCandidate]:
        coords = f"{origin[1]},{origin[0]};{dest[1]},{dest[0]}"
        try:
            with httpx.Client(timeout=self.timeout_s) as client:
                response = client.get(self.base_url+"/route/v1/driving/"+coords,
                    params={"alternatives":"true","overview":"full","geometries":"geojson","steps":"true"})
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise RoutingError("routing_provider_unavailable") from exc
        if not isinstance(data,dict) or data.get("code") != "Ok":
            raise RoutingError("no_route")
        candidates = []
        for item in data.get("routes",[])[:4]:
            try:
                coords_geo = tuple(tuple(map(float, xy)) for xy in item["geometry"]["coordinates"])
                distance, duration = float(item["distance"]), float(item["duration"])
                if len(coords_geo) < 2 or not all(isfinite(x) for x in (distance,duration)) or distance <= 0 or duration <= 0:
                    continue
                steps=[]
                for leg in item.get("legs",[]):
                    for step in leg.get("steps",[]):
                        name = step.get("name", "")
                        coordinates = step.get("geometry",{}).get("coordinates",[])
                        if name and len(coordinates) >= 2:
                            steps.append(RoadStep(str(name),tuple(tuple(map(float,xy)) for xy in coordinates)))
                candidates.append(RouteCandidate(distance,duration,coords_geo,tuple(steps)))
            except (TypeError,ValueError,KeyError):
                continue
        return candidates
