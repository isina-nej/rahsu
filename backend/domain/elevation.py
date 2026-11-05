"""Optional elevation data adapter (self-hosted OpenTopoData compatible service).

A missing/failed provider is *explicitly unknown*, never silently flat terrain.
"""
from bisect import bisect_right
from dataclasses import dataclass, replace
from math import asin, atan, cos, hypot, isfinite, radians, sin, sqrt
from statistics import median

import httpx
from domain.fuel import MotionSample


def haversine_m(a: tuple[float,float], b: tuple[float,float]) -> float:
    lat1,lon1 = radians(a[1]),radians(a[0])
    lat2,lon2 = radians(b[1]),radians(b[0])
    d_lat,d_lon=lat2-lat1,lon2-lon1
    x=sin(d_lat/2)**2+cos(lat1)*cos(lat2)*sin(d_lon/2)**2
    return 2*6_371_000*asin(min(1.0,sqrt(x)))


def uniform_positions(route: tuple[tuple[float,float],...], count: int) -> list[tuple[float,float]]:
    if len(route)<2 or not 2<=count<=100:
        raise ValueError("Invalid route/sample count")
    cumulative=[0.0]
    for a,b in zip(route,route[1:]):
        cumulative.append(cumulative[-1]+haversine_m(a,b))
    total=cumulative[-1]
    if total<=0:
        raise ValueError("Zero-length route geometry")
    result=[]
    for i in range(count):
        distance=total*i/(count-1)
        j=min(max(1,bisect_right(cumulative,distance)),len(route)-1)
        d=cumulative[j]-cumulative[j-1]
        t=(distance-cumulative[j-1])/d if d else 0.0
        result.append((route[j-1][0]+t*(route[j][0]-route[j-1][0]),
                       route[j-1][1]+t*(route[j][1]-route[j-1][1])))
    return result


@dataclass(frozen=True)
class Terrain:
    grades_rad: tuple[float,...]
    ascent_m: float
    descent_m: float
    method: str = "sampled_srtm"


def terrain_from_elevations(values_m: list[float], distance_m: float) -> Terrain:
    if len(values_m)<3 or distance_m<=0 or any(not isfinite(x) for x in values_m):
        raise ValueError("Missing or invalid elevation readings")
    # 3-sample median removes isolated DEM artifacts, not long-range bias.
    smooth=[median(values_m[max(0,i-1):min(len(values_m),i+2)])
            for i in range(len(values_m))]
    ds=distance_m/(len(smooth)-1)
    differences=[b-a for a,b in zip(smooth,smooth[1:])]
    # Low-resolution DEM slopes are noisy; cap to plausible driving bounds.
    grades=tuple(atan(max(-.15,min(.15,d/ds))) for d in differences)
    return Terrain(grades, sum(max(0,x) for x in differences),
                   sum(max(0,-x) for x in differences))


def apply_terrain(
    motion: list[MotionSample], terrain: Terrain, distance_m: float
) -> list[MotionSample]:
    n=len(terrain.grades_rad)
    if distance_m<=0 or n==0:
        raise ValueError("Invalid terrain input")
    return [replace(sample,grade_rad=terrain.grades_rad[
        min(n-1,max(0,int(sample.s_m/distance_m*n)))]) for sample in motion]


class ElevationError(Exception):
    pass


class ElevationClient:
    def __init__(self,base_url: str, dataset: str = "srtm90m", timeout_s: float = 5.0):
        self.base_url=base_url.rstrip("/")
        self.dataset=dataset
        self.timeout_s=timeout_s

    def elevations(self, positions: list[tuple[float,float]]) -> list[float]:
        if not positions or len(positions)>100:
            raise ElevationError("invalid_elevation_sample_count")
        collected=[]
        try:
            with httpx.Client(timeout=self.timeout_s) as client:
                for i in range(0,len(positions),35):
                    points=positions[i:i+35]
                    encoded="|".join(f"{lat:.6f},{lon:.6f}" for lon,lat in points)
                    response=client.get(f"{self.base_url}/v1/{self.dataset}",params={"locations":encoded})
                    response.raise_for_status()
                    data=response.json()
                    rows=data.get("results")
                    if not isinstance(rows,list) or len(rows)!=len(points):
                        raise ElevationError("incomplete_elevation_response")
                    for row in rows:
                        value=row.get("elevation") if isinstance(row,dict) else None
                        if value is None or not isfinite(float(value)):
                            raise ElevationError("missing_elevation_value")
                        collected.append(float(value))
        except (httpx.HTTPError,ValueError,TypeError,AttributeError) as exc:
            raise ElevationError("elevation_provider_unavailable") from exc
        return collected
