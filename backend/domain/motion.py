"""Deterministic approximate driving profile with controlled stops.

A placeholder for a road-class/grade-aware speed-profile engine. No fabricated
live traffic or actual traffic light cycles are assumed.
"""

from dataclasses import dataclass
from math import isfinite, sqrt

from domain.fuel import MotionSample


@dataclass(frozen=True)
class RequiredStop:
    at_m: float
    duration_s: float


def simulate_motion(
    distance_m: float, nominal_duration_s: float, stops: tuple[RequiredStop, ...] = (), *,
    dt_s: float = 1.0, max_accel_mps2: float = 1.25, max_brake_mps2: float = 2.0,
) -> list[MotionSample]:
    if not (isfinite(distance_m) and 0 < distance_m <= 500_000 and isfinite(nominal_duration_s)
            and nominal_duration_s > 0 and 0 < dt_s <= 2):
        raise ValueError("Invalid route or timestep")
    if max_accel_mps2 <= 0 or max_brake_mps2 <= 0:
        raise ValueError("Invalid acceleration bounds")
    ordered = sorted(stops, key=lambda x: x.at_m)
    if any(not 0 < stop.at_m < distance_m or stop.duration_s < 0 for stop in ordered):
        raise ValueError("Stops must be within the route")
    target_v = min(22.0, max(2.0, distance_m / nominal_duration_s))
    points = [MotionSample(t_s=0.0, s_m=0.0, v_mps=0.0, a_mps2=0.0)]
    s = t = v = 0.0
    index = 0
    hold = 0.0
    max_steps = int((distance_m / 2.0 + sum(x.duration_s for x in ordered) + 3600) / dt_s) + 1000
    for _ in range(max_steps):
        if s >= distance_m - 1e-6:
            break
        if hold > 0:
            new_v = 0.0
            hold = max(0.0, hold - dt_s)
        else:
            next_stop = ordered[index] if index < len(ordered) else None
            remaining = max(0.0, next_stop.at_m - s) if next_stop else None
            safe_v = sqrt(2 * max_brake_mps2 * remaining) if remaining is not None else target_v
            wanted = min(target_v, safe_v)
            new_v = min(wanted, v + max_accel_mps2 * dt_s) if wanted >= v else max(wanted, v - max_brake_mps2 * dt_s)
        s_next = s + (v + new_v) * dt_s / 2.0
        if index < len(ordered) and s_next >= ordered[index].at_m - 1e-6:
            s_next = ordered[index].at_m
            new_v = 0.0
            hold = ordered[index].duration_s
            index += 1
        if s_next >= distance_m:
            s_next = distance_m
            new_v = 0.0
        t += dt_s
        a = (new_v - v) / dt_s
        s, v = s_next, new_v
        points.append(MotionSample(t_s=t, s_m=s, v_mps=v, a_mps2=a))
    else:
        raise RuntimeError("Driving profile did not converge")
    if s < distance_m - 1e-6:
        raise RuntimeError("Driving profile stopped early")
    return points
