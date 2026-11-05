"""OSRM adapter. Route geometry is [longitude,latitude] per GeoJSON."""
from dataclasses import dataclass
import httpx

class RoutingError(Exception):
    pass

@dataclass(frozen=True)
class RouteCandidate:
    distance_m: float
    duration_s: float
    coordinates: tuple[tuple[float,float], ...]

class OsrmClient:
    def __init__(self,base_url:str,timeout_s:float=8.0):
        self.base_url=base_url.rstrip('/')
        self.timeout_s=timeout_s
    def candidates(self,origin:tuple[float,float],dest:tuple[float,float])->list[RouteCandidate]:
        coords=f'{origin[1]},{origin[0]};{dest[1]},{dest[0]}'
        try:
            r=httpx.get(self.base_url+'/route/v1/driving/'+coords,params={'alternatives':'true','overview':'full','geometries':'geojson'},timeout=self.timeout_s)
            r.raise_for_status()
            data=r.json()
        except (httpx.HTTPError,ValueError) as exc:
            raise RoutingError('routing_provider_unavailable') from exc
        if data.get('code')!='Ok':raise RoutingError('no_route')
        return [RouteCandidate(float(item['distance']),float(item['duration']),tuple(tuple(c) for c in item['geometry']['coordinates'])) for item in data.get('routes',[]) if item.get('distance',0)>0 and item.get('geometry',{}).get('coordinates')]
